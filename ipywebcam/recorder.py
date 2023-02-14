import asyncio
import re
import uuid
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from os import path
from typing import IO
from typing import Any as AnyType
from typing import Callable, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from traitlets import Bool, Unicode, CUnicode
import logging

from aiortc import RTCPeerConnection
from aiortc.contrib.media import MediaStreamTrack
from av import AudioFrame, VideoFrame
from av import open as av_open
from ipywidgets import DOMWidget

from ._frontend import module_name, module_version
from .common import BaseWidget
from .webcam import MediaTransformer, WebCamWidget

logger = logging.getLogger("ipywebcam")

class RecorderContext:
    def __init__(self, stream):
        self.started = False
        self.stream = stream
        
        
class Record:
    file: str | IO
    format: str | None
    options: dict | None
    __container: AnyType | None = None
    __mode: str | None = None
    __tracks: dict[MediaStreamTrack, RecorderContext] | None
    
    def __init__(self, file: str | IO, format: str | None=None, options: dict | None=None) -> None:
        self.file = file
        self.format = format
        self.options = options
    
    def __repr__(self) -> str:
        query = {}
        if self.format:
            query["format"] = self.format
        if self.options:
            for key in self.options.keys():
                query[f"options.{key}"] = self.options[key]
        return urlunparse(('', '', self.file, '', urlencode(query=query), ''))
    
    def __str__(self) -> str:
        return self.__repr__()
    
    def add_track(self, track: MediaStreamTrack, open: bool=False) -> None:
        if self.__container is None:
            if open:
                self.open('w')
            else:
                raise("The record has not been opened!")
        elif self.__mode != "w":
            raise("The record has not been opened for write!")
        
        if track.kind == "audio":
            if self.__container.format.name in ("wav", "alsa"):
                codec_name = "pcm_s16le"
            elif self.__container.format.name == "mp3":
                codec_name = "mp3"
            else:
                codec_name = "aac"
            stream = self.__container.add_stream(codec_name)
        else:
            if self.__container.format.name == "image2":
                stream = self.__container.add_stream("png", rate=30)
                stream.pix_fmt = "rgb24"
            else:
                stream = self.__container.add_stream("libx264", rate=30)
                stream.pix_fmt = "yuv420p"
        self.__tracks[track] = RecorderContext(stream)
        
    @property
    def file_path(self):
        return self.file if isinstance(self.file, str) else path.normpath(self.file.name)
    
    async def on_frame(self, frame: VideoFrame | AudioFrame, ctx: dict, track: MediaStreamTrack, post: bool):
        context: RecorderContext = self.__tracks.get(track)
        if not context:
            return
        if not post:
            frame = ctx["_org_frame_"]
            
        if not context.started:
            # adjust the output size to match the first frame
            if isinstance(frame, VideoFrame):
                context.stream.width = frame.width
                context.stream.height = frame.height
            context.started = True
        for packet in context.stream.encode(frame):
            self.__container.mux(packet)
    
    def open(self, mode: str):
        self.close()
        self.__mode = mode
        self.__container = av_open(file=self.file, mode=mode, format=self.format, options=self.options)
        self.__tracks = {}
        
    def close(self):
        if self.__container:
            for context in self.__tracks.values():
                for packet in context.stream.encode(None):
                    self.__container.mux(packet)
            self.__tracks = None
            self.__container.close()
            self.__container = None
            self.__mode = None
            
    def relay_tracks_to(self, record: "Record"):
        if not self.__container:
            raise RuntimeError(f"The record is not open: {self.file_path}")
        if self.file_path == record.file_path:
            raise RuntimeError(f"Unable to relay tracks between records with same path: {self.file_path}")
        for track in self.__tracks.keys():
            record.add_track(track=track, open=True)
        


@dataclass
class RecordConditionContext:
    track: MediaStreamTrack
    base_timestamp: float = 0.0
    recorded_frame_count: int = 0
    timestamp: float = 0.0
    on_frame: Callable[[VideoFrame | AudioFrame, dict, MediaStreamTrack], None] | None = None
    
class RecordFactory(metaclass=ABCMeta):
    @abstractmethod
    def open(self) -> "RecordFactory":
        pass
    
    @abstractmethod
    def close(self) -> None:
        pass
    
    @abstractmethod
    def next_record(self, context_map: dict[MediaStreamTrack, RecordConditionContext], track: MediaStreamTrack) -> Tuple[Record, Record]:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
RecordConditionType = Callable[[dict[MediaStreamTrack, RecordConditionContext], MediaStreamTrack], bool]

class TrackStrategy(Enum):
    ALL_TRACK = 1
    ANY_TRACK = 2
    ALL_VIDEO_TRACK = 3
    ANY_VIDEO_TRACK = 4
    ALL_AUDIO_TRACK = 5
    ANY_AUDIO_TRACK = 6
        
class FileListFactory(RecordFactory):
    delimiter = '$'
    idpattern = r'(?a:[_a-z][_a-z0-9]*)'
    braceidpattern = None
    name: str
    template: str
    flush_when_close: bool
    base_path: str
    base_index: int
    format: str | None
    options: dict | None
    __condition: RecordConditionType
    __record_list: list[Record] | None
    __pending_record: Record = None
    
    
    def __init_subclass__(cls):
        super().__init_subclass__()
        if 'pattern' in cls.__dict__:
            pattern = cls.pattern
        else:
            delim = re.escape(cls.delimiter)
            id = cls.idpattern
            bid = cls.braceidpattern or cls.idpattern
            pattern = fr"""
            {delim}(?:
              (?P<escaped>{delim})  |   # Escape sequence of two delimiters
              (?P<named>{id})       |   # delimiter and a Python identifier
              {{(?P<braced>{bid})}} |   # delimiter and a braced identifier
              (?P<invalid>)             # Other ill-formed delimiter exprs
            )
            """
        cls.pattern = re.compile(pattern, re.IGNORECASE | re.VERBOSE)
    
    def __init__(
        self, name: str,
        template: str,
        condition: RecordConditionType=lambda context_map, track: True,
        flush_when_stop: bool = True,
        base_path: str=None,
        base_index: int=1,
        format: str | None = None,
        options: dict | None = None,
    ) -> None:
        self.name = name
        self.template = template
        self.flush_when_close = flush_when_stop
        self.base_path = base_path.replace('\\', '/') if base_path else None
        self.base_index = base_index
        self.format = format
        self.options = options
        self.__condition = condition
        self.__record_list = None
        today = datetime.today()
        monday = today - timedelta(days=today.weekday())
        weeks = [monday + timedelta(days=i) for i in range(0, 7)]
        months = [datetime.strptime(s, "%y-%m-%d") for s in [f"99-{m:02}-01" for m in range(1, 13)]]
        am_and_pm = [datetime.strptime(s, "%y-%m-%d:%H:%M:%S") for s in ['99-01-01:06:00:00', '99-01-01:16:00:00']]
        a_list = "|".join([day.strftime("%a") for day in weeks])
        self._reg_a = f"({a_list})"
        A_list = "|".join([day.strftime("%A") for day in weeks])
        self._reg_A = f"({A_list})"
        b_list = "|".join([month.strftime("%b") for month in months])
        self._reg_b = f"({b_list})"
        B_list = "|".join([month.strftime("%B") for month in months])
        self._reg_B = f"({B_list})"
        p_list = "|".join([am_or_pm.strftime("%p") for am_or_pm in am_and_pm])
        self._reg_p = f"({p_list})"
        self._reg_map = {
            'u': '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'uuid': '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            'uh': '[0-9a-f]{32}',
            'uh2': '[0-9a-f]{2}',
            'uh3': '[0-9a-f]{3}',
            'uh4': '[0-9a-f]{4}',
            'uh5': '[0-9a-f]{5}',
            'uh6': '[0-9a-f]{6}',
            'uh7': '[0-9a-f]{7}',
            'uh8': '[0-9a-f]{8}',
            'uuhex': '[0-9a-f]{32}',
            'uuhex2': '[0-9a-f]{2}',
            'uuhex3': '[0-9a-f]{3}',
            'uuhex4': '[0-9a-f]{4}',
            'uuhex5': '[0-9a-f]{5}',
            'uuhex6': '[0-9a-f]{6}',
            'uuhex7': '[0-9a-f]{7}',
            'uuhex8': '[0-9a-f]{8}',
            'a': self._reg_a,
            'A': self._reg_A,
            'b': self._reg_b,
            'B': self._reg_B,
            'y': '\d{2}',
            'Y': '\d{4}',
            'm': '(0[1-9]|1[0-2])',
            'w': '[0-6]',
            'd': '(0[1-9]|[12][0-9]|3[01])',
            'H': '([01][0-9]|2[0-3])',
            'I': '(0[1-9]|1[0-2])',
            'p': self._reg_p,
            'M': '([0-5][0-9]|60)',
            'S': '([0-5][0-9]|60)',
            'f': '\d{6}',
            'z': '([+-]([01][0-9]|2[0-3])([0-5][0-9]|60))?',
            'Z': '([A-Z]+)?',
            'j': '([012]\d\d|3[0-5]\d|36[0-6])',
            'U': '([0-4]\d|5[0-3])',
            'W': '([0-4]\d|5[0-3])',
        }
        
    def _full_path(self, p: str) -> str:
        p = p.replace('\\', '/')
        return path.normpath(p) if not self.base_path else path.normpath(path.join(self.base_path, p))
    
    def _is_index_key(self, key: str) -> bool:
        return key in ['i', 'i2', 'i3', 'i4', 'i5', 'i6', 'index', 'index2', 'index3', 'index4', 'index5', 'index6']
    
    def _format_index(self, index: int, pattern: str):
        last = pattern[-1:]
        if last.isnumeric():
            len = int(last)
            return f"{{index:0{len}}}".format(index=index)
        else:
            return str(index)

    def _invalid(self, mo: re.Match[str]):
        i = mo.start('invalid')
        lines = self.template[:i].splitlines(keepends=True)
        if not lines:
            colno = 1
            lineno = 1
        else:
            colno = i - len(''.join(lines[:-1]))
            lineno = len(lines)
        raise ValueError('Invalid placeholder in string: line %d, col %d' %
                         (lineno, colno))
        
    def _ensure_open(self):
        if self.__record_list is None:
            raise RuntimeError(f"The record factory {self.name} has not been loaded. You must open it at first.")
        
    @staticmethod
    def create_time_based_condition(duration: float, track_strategy: TrackStrategy=TrackStrategy.ANY_TRACK) -> RecordConditionType:
        def condition(context_map: dict[MediaStreamTrack, RecordConditionContext], current_track: MediaStreamTrack) -> bool:
            if (track_strategy == TrackStrategy.ALL_VIDEO_TRACK or track_strategy == TrackStrategy.ANY_VIDEO_TRACK) and current_track.kind != "video":
                return True
            if (track_strategy == TrackStrategy.ALL_AUDIO_TRACK or track_strategy == TrackStrategy.ANY_AUDIO_TRACK) and current_track.kind != "audio":
                return True
            for track, context in context_map.items():
                check = context.timestamp - context.base_timestamp <= duration
                if (track_strategy == TrackStrategy.ALL_TRACK or track_strategy == TrackStrategy.ALL_VIDEO_TRACK or track_strategy == TrackStrategy.ALL_AUDIO_TRACK) and not check:
                    return False
                if (track_strategy == TrackStrategy.ANY_TRACK or track_strategy == TrackStrategy.ANY_VIDEO_TRACK or track_strategy == TrackStrategy.ANY_AUDIO_TRACK) and check:
                    return True
            return False
        return condition
    
    @staticmethod
    def create_frame_based_condition(count: int, track_strategy: TrackStrategy=TrackStrategy.ANY_TRACK) -> RecordConditionContext:
        def condition(context_map: dict[MediaStreamTrack, RecordConditionContext], current_track: MediaStreamTrack) -> bool:
            if (track_strategy == TrackStrategy.ALL_VIDEO_TRACK or track_strategy == TrackStrategy.ANY_VIDEO_TRACK) and track.kind != "video":
                return True
            if (track_strategy == TrackStrategy.ALL_AUDIO_TRACK or track_strategy == TrackStrategy.ANY_AUDIO_TRACK) and track.kind != "audio":
                return True
            for track, context in context_map.items():
                check = context.recorded_frame_count <= count
                if (track_strategy == TrackStrategy.ALL_TRACK or track_strategy == TrackStrategy.ALL_VIDEO_TRACK or track_strategy == TrackStrategy.ALL_AUDIO_TRACK) and not check:
                    return False
                if (track_strategy == TrackStrategy.ANY_TRACK or track_strategy == TrackStrategy.ANY_VIDEO_TRACK or track_strategy == TrackStrategy.ANY_AUDIO_TRACK) and check:
                    return True
            return False
        return condition
        
    def name(self) -> str:
        return self.name
        
    def generate(self, index: int, full: bool=True) -> str:
        now = datetime.now()
        i2 = f'{index:02}'
        i3 = f'{index:03}'
        i4 = f'{index:04}'
        i5 = f'{index:05}'
        i6 = f'{index:06}'
        id = uuid.uuid4()
        uh2 = id.hex[0:2]
        uh3 = id.hex[0:3]
        uh4 = id.hex[0:4]
        uh5 = id.hex[0:5]
        uh6 = id.hex[0:6]
        uh7 = id.hex[0:7]
        uh8 = id.hex[0:8]
        mapping = {
            'i': index,
            'i2': i2,
            'i3': i3,
            'i4': i4,
            'i5': i5,
            'i6': i6,
            'index': index,
            'index2': i2,
            'index3': i3,
            'index4': i4,
            'index5': i5,
            'index6': i6,
            'u': str(id),
            'uuid': str(id),
            'uh': id.hex,
            'uh2': uh2,
            'uh3': uh3,
            'uh4': uh4,
            'uh5': uh5,
            'uh6': uh6,
            'uh7': uh7,
            'uh8': uh8,
            'uuhex': id.hex,
            'uuhex2': uh2,
            'uuhex3': uh3,
            'uuhex4': uh4,
            'uuhex5': uh5,
            'uuhex6': uh6,
            'uuhex7': uh7,
            'uuhex8': uh8,
            'a': now.strftime('%a'),
            'A': now.strftime('%A'),
            'b': now.strftime('%b'),
            'B': now.strftime('%B'),
            'Y': now.strftime('%Y'),
            'y': now.strftime('%y'),
            'm': now.strftime('%m'),
            'w': now.strftime('%w'),
            'd': now.strftime('%d'),
            'H': now.strftime('%H'),
            'I': now.strftime('%I'),
            'p': now.strftime('%p'),
            'M': now.strftime('%M'),
            'S': now.strftime('%S'),
            'f': now.strftime('%f'),
            'z': now.strftime('%z'),
            'Z': now.strftime('%Z'),
            'j': now.strftime('%j'),
            'U': now.strftime('%U'),
            'W': now.strftime('%W'),
        }
        def convert(mo: re.Match[str]):
            # Check the most common path first.
            named = mo.group('named') or mo.group('braced')
            if named is not None:
                if self._is_index_key(named):
                    return self._format_index(index=index, pattern=named)
                else:
                    return str(mapping[named])
            if mo.group('escaped') is not None:
                return self.delimiter
            if mo.group('invalid') is not None:
                raise ValueError(f"Unrecognized key {mo.group('invalid')} in expression {self.template}")
            raise ValueError('Unrecognized named group in pattern',
                             self.pattern)
        t = self.pattern.sub(convert, self.template)
        return self._full_path(t) if full else path.normpath(t.replace('\\', '/'))
    
    def to_reg(self, index: int) -> str:
        parts = re.split(pattern=self.pattern, string=self.template)
        if len(parts) == 0:
            return ""
        else:
            res = ""
            for i, part in enumerate(parts):
                if i % 5 == 0:
                    res += re.escape(part)
                elif part is not None:
                    if i % 5 == 1:
                        res += re.escape(self.delimiter)
                    elif i % 5 == 2 or i % 5 == 3:
                        if self._is_index_key(part):
                            res += re.escape(self._format_index(index=index, pattern=part))
                        else:
                            reg = self._reg_map.get(part)
                            if reg is None:
                                raise ValueError(f'Unrecognized key {part} in expression {self.template}')
                            res += reg
                    elif i % 5 == 4:
                        raise ValueError(f'Unrecognized key {part} in expression {self.template}')
            return res
        
    def open(self) -> "FileListFactory":
        record_list_path = self._full_path(f'{self.name}.record_list')
        if path.exists(record_list_path):
            with open(record_list_path) as f:
                self.__record_list = [self.restore_record_from_url(line) for line in f.read().splitlines() if line]
                print(f"load {len(self.__record_list)} records")
        else:
            self.__record_list = []
        return self
    
    def close(self) -> None:
        self._ensure_open()
        if self.flush_when_close:
            self.flush()
        record_list_path = self._full_path(f'{self.name}.record_list')
        with open(record_list_path, 'w') as f:
            f.writelines([f"{record}\n" for record in self.__record_list])
        self.__record_list = None
    
    def flush(self):
        self._ensure_open()
        if self.__pending_record:
            self.__pending_record.close()
            self.__record_list.append(self.__pending_record)
            self.__pending_record = None
                
    def create_next_record(self, index: int) -> Record:
        file = self.generate(index=index, full=True)
        return Record(file=file, format=self.format, options=self.options)
    
    def restore_record_from_url(self, url: str):
        res = urlparse(url=url)
        query = res.query
        format: str | None = None
        options: dict = {}
        if res.query:
            query = parse_qs(res.query)
            if "format" in query and query['format']:
                format = query['format'][0]
            for key in query.keys():
                if key.startswith("options.") and query[key]:
                    options[key[8:]] = str(query[key][0])
            
        return Record(file=self._full_path(res.path), format=format, options=options)
    
    def get_or_create_pending_record(self) -> Record:
        self._ensure_open()
        if not self.__pending_record:
            self.__pending_record = self.create_next_record(self.base_index + len(self.__record_list))
        return self.__pending_record
    
    def next_record(self, context_map: dict[MediaStreamTrack, RecordConditionContext], track: MediaStreamTrack) -> Tuple[Record, Record]:
        self._ensure_open()
        old = self.__pending_record
        if self.__condition(context_map, track):
            return self.get_or_create_pending_record(), old
        record = self.create_next_record(self.base_index + len(self.__record_list) + 1)
        if self.__pending_record:
            self.__pending_record.relay_tracks_to(record=record)
            self.__pending_record.close()
            self.__record_list.append(self.__pending_record)
        self.__pending_record = record
        return record, old
        
                    
FileListFactory.__init_subclass__()

class SingleFileFactory(RecordFactory):
    file: str | IO
    format: str | None = None
    options: dict | None = None
    record: Record = None
    
    def __init__(
        self,
        file: str | IO,
        format: str | None = None,
        options: dict | None = None,
    ) -> None:
        super().__init__()
        self.file = file
        self.format = format
        self.options = options
        
    def open(self) -> "SingleFileFactory":
        return self
    
    def close(self) -> None:
        if self.record:
            self.record.close()
            self.record = None
    
    @property
    def name(self) -> str:
        if isinstance(self.file, str):
            base = path.basename(self.file)
        else:
            base = path.basename(self.file.name)
        return path.splitext(base)[0]
    
    def next_record(self, context_map: dict[MediaStreamTrack, RecordConditionContext], track: MediaStreamTrack) -> Tuple[Record, Record]:
        old = self.record
        if old is None:
            self.record = Record(file=self.file, format=self.format, options=self.format)
        return self.record, old
    
        
class WebCamRecorder:
    factory: RecordFactory
    post: bool
    context_map: dict[MediaStreamTrack, RecordConditionContext]
    def __init__(self, widget: WebCamWidget, file_or_factory: str | IO | RecordFactory, post: bool=True, format: str=None, options:dict={}, **kargs) -> None:
        self.widget = widget
        self.post = post
        self.factory = file_or_factory if isinstance(file_or_factory, RecordFactory) else SingleFileFactory(file=file_or_factory, format=format, options=options)
        self.recording = False
        self.video_poster = MediaTransformer[VideoFrame]
        self.audio_poster = MediaTransformer[AudioFrame]
        self.lock = asyncio.Lock()
        
    def init_record_condition_context(self, track: MediaStreamTrack) -> dict[MediaStreamTrack, RecordConditionContext]:
        if track in self.context_map:
            raise RuntimeError(f"The track {track} has been add to the condition context map.")
        self.context_map[track] = RecordConditionContext(track=track)
        return self.context_map
        
    async def on_add_track(self, track: MediaStreamTrack, pc: RTCPeerConnection) -> None:
        async with self.lock:
            context_map = self.init_record_condition_context(track=track)
            record, _ = self.factory.next_record(context_map=context_map, track=track)
            record.add_track(track=track, open=True)
                
    async def on_frame(self, frame: VideoFrame | AudioFrame, ctx: dict, track: MediaStreamTrack):
        async with self.lock:
            (record, old_record) = self.factory.next_record(context_map=self.context_map, track=track)
            context = self.context_map.get(track)
            if record != old_record:
                context.recorded_frame_count = 0
                context.timestamp = 0
                context.base_timestamp = frame.time
            else:
                context.recorded_frame_count += 1
                context.timestamp = frame.time
            await record.on_frame(frame=frame, ctx=ctx, track=track, post=self.post)

            
    async def a_start(self) -> None:
        async with self.lock:
            if not self.recording:
                self.factory.open()
                self.context_map = {}
                self.recording = True
                self.widget.add_track_callback(self.on_add_track)
                self.video_poster = self.widget.add_video_poster(self.on_frame)
                self.audio_poster = self.widget.add_audio_poster(self.on_frame)
        
    async def a_stop(self) -> None:
        async with self.lock:
            if self.recording:
                self.recording = False
                self.widget.remove_video_poster(self.video_poster)
                self.widget.remove_audio_poster(self.audio_poster)
                self.widget.remove_track_callback(self.on_add_track)
                self.factory.close()
                    
    def start(self) -> None:
        asyncio.create_task(self.a_start())
        
    def stop(self) -> None:
        asyncio.create_task(self.a_stop())
        

class RecordPlayer(DOMWidget, BaseWidget):
    
    _model_name = Unicode('RecordPlayerModel').tag(sync=True)
    _view_name = Unicode('RecordPlayerView').tag(sync=True)
    
    # Define the custom state properties to sync with the front-end
    format = Unicode('mp4', help="The format of the video.").tag(sync=True)
    width = CUnicode(help="Width of the video in pixels.").tag(sync=True)
    height = CUnicode(help="Height of the video in pixels.").tag(sync=True)
    autoplay = Bool(True, help="When true, the video starts when it's displayed").tag(sync=True)
    loop = Bool(True, help="When true, the video will start from the beginning after finishing").tag(sync=True)
    controls = Bool(True, help="Specifies that video controls should be displayed (such as a play/pause button etc)").tag(sync=True)
    
    def __init__(self, recorder: WebCamRecorder, **kwargs):
        super().__init__(logger=logger, **kwargs)
        self.recorder = recorder
        self.add_answer("fetch_record_meta", self.answer_fetch_record_meta)
        self.add_answer("fetch_media_data", self.answer_fetch_media_data)
        
    def _get_media_data(self, index: int) -> bytes | None:
        pass
    
    def answer_fetch_record_meta(self, id: str, cmd: str, args: dict) -> None:
        pass
    
    def answer_fetch_media_data(self, id: str, cmd: str, args: dict) -> None:
        if "index" in args:
            index = args["index"]
            data = self._get_media_data(index=index)
            self.answer(cmd=cmd, target_id=id, buffers=[data] if data is not None else None)
            