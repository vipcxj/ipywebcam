#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Xiaojing Chen.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from abc import ABCMeta, abstractmethod
from os import path
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from threading import RLock
from urllib.parse import parse_qs, quote, urlencode, urlparse, urlunparse
import re
import inspect
from string import Template
import logging
import uuid
from typing import Awaitable, Callable, Generic, Optional, TypeVar, Union, IO, Any as AnyType
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay, MediaStreamTrack, MediaRecorder
from av import VideoFrame, AudioFrame, open as av_open
from ipywidgets import DOMWidget, Dropdown
from traitlets import Any, Bool, Float, List, Unicode, Dict, Enum, link
from ._frontend import module_name, module_version

logger = logging.getLogger("ipywebcam")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(path.join(path.dirname(__file__), "ipywebcam.log"))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
my_loop = False
try:
    loop = asyncio.get_running_loop()
    logger.debug("using exist loop.")
except RuntimeError:
    loop = asyncio.get_event_loop()
    my_loop = True
    logger.debug("create new loop.")


logger.info("I am loaded")

relay = MediaRelay()

MT = TypeVar('MT', VideoFrame, AudioFrame)
class MediaTransformer(Generic[MT]):
    def __init__(self, callback: Callable[[MT, dict, MediaStreamTrack], Union[MT, Awaitable[MT]]], context: dict = {}) -> None:
        self.callback = callback
        self.context = context
        self.iscoroutinefunction = inspect.iscoroutinefunction(self.callback)
        sig = inspect.signature(self.callback)
        self.require_ctx =  len(sig.parameters) > 1
        self.require_track = len(sig.parameters) > 2
        
    async def transform(self, frame: MT, track: MediaStreamTrack=None) -> MT | None:
        if self.iscoroutinefunction:
            if self.require_ctx and self.require_track:
                frame = await self.callback(frame, self.context, track)
            elif self.require_ctx:
                frame = await self.callback(frame, self.context)
            else:
                frame = await self.callback(frame)
        else:
            if self.require_ctx and self.require_track:
                frame = self.callback(frame, self.context, track)
            elif self.require_ctx:
                frame = self.callback(frame, self.context)
            else:
                frame = self.callback(frame)
        return frame


class WithMediaTransformers:
    video_transformers: list[MediaTransformer[VideoFrame]]
    video_posters: list[MediaTransformer[VideoFrame]]
    audio_transformers: list[MediaTransformer[AudioFrame]]
    audio_posters: list[MediaTransformer[AudioFrame]]
    
    def __init__(self) -> None:
        self.video_transformers = []
        self.video_posters = []
        self.audio_transformers = []
        self.audio_posters = []

class MediaTransformTrack(MediaStreamTrack, Generic[MT], metaclass=ABCMeta):
    
    def __init__(self, track: MediaStreamTrack, withTransformers: WithMediaTransformers):
        super().__init__()
        self.track = track
        self.withTransformers = withTransformers
        
    async def recv(self) -> MT:
        frame: MT = await self.track.recv()
        org_frame = frame
        try:
            for transformer in self.__class__.get_transformers(self.withTransformers):
                transformer.context["_org_frame_"] = org_frame
                out_frame = await transformer.transform(frame=frame, track=self.track)
                frame = out_frame if out_frame is not None else frame
                
            if org_frame is not None and frame is not None:
                if hasattr(org_frame, "pts") and hasattr(frame, "pts") and frame.pts is None:
                    frame.pts = org_frame.pts
                if hasattr(org_frame, "time_base") and hasattr(frame, "time_base") and frame.time_base is None:
                    frame.time_base = org_frame.time_base
                    
            for poster in self.__class__.get_posters(self.withTransformers):
                poster.context["_org_frame_"] = org_frame
                await poster.transform(frame=frame, track=self.track)
            return frame
        except Exception as e:
            logger.exception(e)
    
    @staticmethod        
    @abstractmethod
    def get_transformers(withTransformers: WithMediaTransformers) -> list[MediaTransformer[MT]]:
        pass
    
    @staticmethod
    @abstractmethod
    def get_posters(withTransformers: WithMediaTransformers) -> list[MediaTransformer[MT]]:
        pass            
            
class VideoTransformTrack(MediaTransformTrack[VideoFrame]):
    kind = 'video'
    
    @staticmethod
    def get_transformers(withTransformers: WithMediaTransformers) -> list[MediaTransformer[VideoFrame]]:
        return withTransformers.video_transformers
    
    @staticmethod
    def get_posters(withTransformers: WithMediaTransformers) -> list[MediaTransformer[MT]]:
        return withTransformers.video_posters
    
class AudioTransformTrack(MediaTransformTrack[AudioFrame]):
    kind = 'audio'
    
    @staticmethod
    def get_transformers(withTransformers: WithMediaTransformers) -> list[MediaTransformer[AudioFrame]]:
        return withTransformers.audio_transformers
    
    @staticmethod
    def get_posters(withTransformers: WithMediaTransformers) -> list[MediaTransformer[MT]]:
        return withTransformers.audio_posters


def transform_devices_to_options(devices): 
    return [(device.get('label') or device.get('deviceId'), device) for device in devices]


def transform_options_to_devices(options):
    return [device for (_, device) in options if device]


def find_device_from_options(options: list[tuple[str, dict]], device_id: str) -> dict | None:
    for _, device in options:
        if device.get("deviceId") == device_id:
            return device
    return None


def deviceEquals(dev1: dict | None, dev2: dict | None) -> bool:
    if dev1 is None:
        return dev2 is None
    if dev2 is None:
        return dev1 is None
    return dev1.get("deviceId") == dev2.get("deviceId")

@dataclass
class TrackMap:
    video: list[MediaStreamTrack] = field(default_factory=list)
    audio: list[MediaStreamTrack] = field(default_factory=list)
    
    def clear(self) -> None:
        self.video = []
        self.audio = []

@dataclass
class State:
    id: str
    widget: "WebCamWidget"
    pc: RTCPeerConnection = None
    client_desc: RTCSessionDescription = None
    server_desc: RTCSessionDescription = None
    lock: RLock = field(default_factory=RLock)
    a_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    video_input_devices: list[dict] = field(default_factory=list)
    video_input_devices_busy: bool = False
    video_input_device_id: str | None = None
    video_input_selector: Dropdown = field(default_factory=lambda: Dropdown(options=[], value=None, description='Video Input', _view_count=0))
    audio_input_devices: list[dict] = field(default_factory=list)
    audio_input_devices_busy: bool = False
    audio_input_device_id: str | None = None
    audio_input_selector: Dropdown = field(default_factory=lambda: Dropdown(options=[], value=None, description='Audio Input', _view_count=0))
    audio_output_devices: list[dict] = field(default_factory=list)
    audio_output_devices_busy: bool = False
    audio_output_device_id: str | None = None
    audio_output_selector: Dropdown = field(default_factory=lambda: Dropdown(options=[], value=None, description='Audio Output', _view_count=0))
    track_map: TrackMap = field(default_factory=TrackMap)
    
    def __post_init__(self):
        def on_view_count_change(type: str, old_count, new_count):
            self.log_info(f"view count change from {old_count} to {new_count}")
            if old_count == 0 and new_count > 0:
                self.widget.request_devices(self.id, type=type)
        def transform_change(change: dict) -> dict:
            return {
                "old": None if change.old is None else change.old["deviceId"],
                "new": None if change.new is None else change.new["deviceId"],
            }
        def create_handler(type: str) -> Callable[[AnyType], None]:
            def handler(change: AnyType) -> None:
                if not self.is_devices_busy(type=type):
                    t_change = transform_change(change)
                    self._set_device_id(type, t_change["new"])
                    self.widget.notify_device_change(self.id, type=type, change=t_change)
            return handler
        
        self.video_input_selector.observe(lambda change: on_view_count_change("video_input", change.old, change.new), "_view_count")
        self.observe(id, "video_input", create_handler("video_input"))
        self.audio_input_selector.observe(lambda change: on_view_count_change("audio_input", change.old, change.new), "_view_count")
        self.observe(id, "audio_input", create_handler("audio_input"))
        self.audio_output_selector.observe(lambda change: on_view_count_change("audio_output", change.old, change.new), "_view_count")
        self.observe(id, "audio_output", create_handler("audio_output"))
        
    
    def get_device_id(self, type: str) -> str:
        if type == 'video_input':
            return self.video_input_device_id
        elif type == 'audio_input':
            return self.audio_input_device_id
        elif type == 'audio_output':
            return self.audio_output_device_id
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def _set_device_id(self, type: str, id: str):
        if type == 'video_input':
            self.video_input_device_id = id
        elif type == 'audio_input':
            self.audio_input_device_id = id
        elif type == 'audio_output':
            self.audio_output_device_id = id
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def set_device_id(self, type: str, id: str):
        with self.lock:
            self._set_device_id(type=type, id=id)
            selector = self.get_device_selector(type=type)
            device = find_device_from_options(selector.options, id)
            self.log_info(f'found device: {device} from options by id: {id} and type: {type}')
            if selector.value != device:
                selector.value = device
        
    def get_device_selector(self, type: str) -> Dropdown:
        if type == 'video_input':
            return self.video_input_selector
        elif type == 'audio_input':
            return self.audio_input_selector
        elif type == 'audio_output':
            return self.audio_output_selector
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def is_devices_busy(self, type: str) -> bool:
        if type == 'video_input':
            return self.video_input_devices_busy
        elif type == 'audio_input':
            return self.audio_input_devices_busy
        elif type == 'audio_output':
            return self.audio_output_devices_busy
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def set_devices_busy(self, type: str, busy: bool) -> None:
        if type == 'video_input':
            if busy:
                self.video_input_selector.disabled = True
            self.video_input_devices_busy = busy
            if not busy:
                self.video_input_selector.disabled = False
        elif type == 'audio_input':
            if busy:
                self.audio_input_selector.disabled = True
            self.audio_input_devices_busy = busy
            if not busy:
                self.audio_input_selector.disabled = False
        elif type == 'audio_output':
            if busy:
                self.audio_output_selector.disabled = True
            self.audio_output_devices_busy = busy
            if not busy:
                self.audio_output_selector.disabled = False
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    @contextmanager
    def hold_devices(self, type: str):
        if self.is_devices_busy(type=type):
            yield
        else:
            try:
                self.set_devices_busy(type=type, busy=True)
                yield
            finally:
                self.set_devices_busy(type=type, busy=False)
        
        
    def set_devices(self, type: str, devices: list[dict]):
        with self.lock:
            try:
                selector = self.get_device_selector(type=type)
                options = transform_devices_to_options(devices=devices)
                device_id = self.get_device_id(type)
                old_value = selector.value
                new_value = None if device_id is None else find_device_from_options(options, device_id)
                with self.hold_devices(type):
                    selector.options = options
                    selector.value = new_value
                if not deviceEquals(old_value, new_value):
                    self.widget.notify_device_change(
                        self.id,
                        type=type,
                        change={
                            "old": None if old_value is None else old_value["deviceId"],
                            "new": None if new_value is None else new_value["deviceId"],
                        },
                    )
            except Exception as e:
                logger.exception(e)
            
            
    def get_devices(self, type: str):
        with self.lock:
            selector = self.get_device_selector(type=type)
            return transform_options_to_devices(selector.options)
        
    def observe(self, id: str, type: str, handler: Callable[[dict], None]):
        with self.lock:
            selector = self.get_device_selector(type=type)
            selector.observe(handler=handler, names="value")
            
    def log_info(self, msg: str, *args):
        logger.info(f"[{self.id}] {msg}", *args)
            
    async def exchange_peer(self, client_desc: dict[str, str]):
        try:
            async with self.a_lock:
                if self.pc:
                    await self.pc.close()
                    self.pc = None
                    self.track_map.clear()
                self.client_desc = offer = RTCSessionDescription(**client_desc)
                self.pc = RTCPeerConnection(RTCConfiguration(self.widget.get_ice_servers()))
                id = uuid.uuid4().hex
                pc = self.pc
                @pc.on("icegatheringstatechange")
                async def on_iceconnectionstatechange():
                    self.log_info(f"[{id}] Ice connection state is {pc.iceGatheringState}")
                
                @pc.on("iceconnectionstatechange")
                async def on_iceconnectionstatechange():
                    self.log_info(f"[{id}] Ice connection state is {pc.iceConnectionState}")
                    
                @pc.on("signalingstatechange")
                async def on_signalingstatechange():
                    self.log_info(f"[{id}] Signaling state is {pc.signalingState}")
                
                @pc.on("connectionstatechange")    
                async def on_connectionstatechange():
                    self.log_info(f"[{id}] Connection state is {pc.connectionState}")
                    if pc.connectionState == "failed":
                        async with self.a_lock:
                            await pc.close()
                            self.pc = None
                            self.track_map.clear()
                    
                @pc.on("error")
                async def on_error(error):
                    logger.exception(error)
                
                @pc.on("track")
                def on_track(track):
                    self.log_info(f"[{id}] Track {track.kind} received")
                    if track.kind == "video":
                        pc.addTrack(relay.subscribe(VideoTransformTrack(track, self.widget)))
                    elif track.kind == "audio":
                        pc.addTrack(relay.subscribe(AudioTransformTrack(track, self.widget)))
                    with self.widget.lock:
                        asyncio.gather(*[callback(track, pc) for callback in self.widget.track_callbacks])
                        self.track_map.video.append(track)
                    
                # handle offer
                await pc.setRemoteDescription(offer)
                # send answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                self.server_desc = pc.localDescription
                self.widget.answer("exchange_peer", self.id, { "sdp": self.server_desc.sdp, "type": self.server_desc.type })
        except Exception as e:
            logger.exception(e)
            
    async def close(self):
        async with self.a_lock:
            if self.pc:
                await self.pc.close()
                self.pc = None
                self.track_map.clear()

OnTrackCallback = Callable[[MediaStreamTrack, RTCPeerConnection], Awaitable[None]] 

class WebCamWidget(DOMWidget, WithMediaTransformers):
    """
    A widget for using web camera. Support processing frame in the backend using python at runtime.
    
    If there are multiple cameras on your computer, the widget provide a child widget 'devicesWidget' which can be used to select the active device.
    
    The widget also support many attribute of html5 tag 'video'.
    * autoplay - Bool (default True)
    * controls - Bool (default True)
    * crossOrigin - Enum('not-support', 'anonymous', 'use-credentials') (default 'not-support')
    * width - Float (default None)
    * height - Float (default None)
    * playsInline - Bool (default True)
    * muted - Bool (default False)
    """
    _model_name = Unicode('WebCamModel').tag(sync=True)
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_name = Unicode('WebCamView').tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)
     
    iceServers = List(Any(), default_value=[]).tag(sync=True)
    
    autoplay = Bool(True, allow_none=True).tag(sync=True)
    
    controls = Bool(True, allow_none=True).tag(sync=True)
    
    crossOrigin = Enum(set(['not-support', 'anonymous', 'use-credentials']), default_value='not-support').tag(sync=True)
    
    width = Float(default_value=None, allow_none=True).tag(sync=True)
    
    height = Float(default_value=None, allow_none=True).tag(sync=True)
    
    playsInline = Bool(True, allow_none=True).tag(sync=True)
    
    muted = Bool(False, allow_none=True).tag(sync=True)
    
    constraints = Dict(default_value=None, allow_none=True).tag(sync=True)
    
    video_codecs = List(Unicode(), default_value=[]).tag(sync=True)
    video_codec = Unicode(default_value=None, allow_none=True).tag(sync=True)
    video_codec_selector = Dropdown(options=[], value=None, description='Video codec')
    
    state_map: dict[str, State]
    lock: RLock
    track_callbacks: list[OnTrackCallback]
    
    def __init__(
        self,
        constraints: Optional[dict] = None,
        iceServers: Optional[list[RTCIceServer]] = None,
        autoplay: Optional[bool] = None,
        controls: Optional[bool] = None,
        crossOrigin: Optional[bool] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        playsInline: Optional[bool] = None,
        muted: Optional[bool] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.state_map = {}
        self.lock = RLock()
        self.track_callbacks = []
        link((self.video_codec_selector, 'options'), (self, 'video_codecs'))
        link((self.video_codec_selector, 'value'), (self, 'video_codec'))
        if iceServers is not None:
            self.iceServers = iceServers
        if constraints is not None:
            self.constraints = constraints
        if autoplay is not None:
            self.autoplay = autoplay
        if controls is not None:
            self.controls = controls
        if crossOrigin is not None:
            self.crossOrigin = crossOrigin
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        if playsInline is not None:
            self.playsInline = playsInline
        if muted is not None:
            self.muted = muted
            
            
    def send_command(self, cmd: str, target_id: str, args: dict, on_result: Callable[[str, AnyType], None] | None) -> None:
        self.send({ "cmd": cmd, "id": target_id, "args": args })
        if on_result is not None:
            def callback(widget, content, buffers) -> None:
                if isinstance(content, dict) and content.get("ans") == cmd:
                    source_id: str = content.get("id")
                    if not target_id or source_id == target_id:
                        on_result(source_id, content.get("res"))
                        self.on_msg(callback, True)
            self.on_msg(callback)
        
    def answer(self, cmd: str, target_id: str, content: AnyType) -> None:
        self.send({ "ans": cmd, "id": target_id, "res": content })
        
    def notify_device_change(self, id: str, type: str, change: dict):
        state = self.get_or_create_state(id)
        self.send_command("notify_device_change", id, { "type": type, "change": change }, on_result=None)
        
        
    def get_or_create_state(self, id: str) -> State:
        with self.lock:
            state = self.state_map.get(id)
            if state is None:
                state = State(id=id, widget=self)
                self.state_map[id] = state
            return state
        
    def get_current_state(self, create=True) -> State:
        if create:
            return self.get_or_create_state(self.model_id)
        else:
            return self.state_map.get(self.model_id)
    
    @property
    def video_input_selector(self) -> Dropdown:
        return self.get_current_state().video_input_selector
    
    @property
    def video_input_device_id(self) -> str | None:
        return self.get_current_state().video_input_device_id
    
    @property
    def audio_input_selector(self) -> Dropdown:
        return self.get_current_state().audio_input_selector
    
    @property
    def audio_input_device_id(self) -> str | None:
        return self.get_current_state().audio_input_device_id
    
    @property
    def audio_output_selector(self) -> Dropdown:
        return self.get_current_state().audio_output_selector
    
    @property
    def audio_output_device_id(self) -> str | None:
        return self.get_current_state().audio_output_device_id
        
    def request_devices(self, id: str, type: str):
        state = self.get_or_create_state(id)
        def on_result(id: str, res: AnyType):
            if not isinstance(res, list):
                raise RuntimeError(f"The result of request_devices command from {id} should be a list. but got {type(res)}")
            state.set_devices(type=type, devices=res)
            
        self.send_command("request_devices", id, { "type": type }, on_result=on_result)
        
        
    def answer_exchange_peer(self, id: str, client_desc: dict[str, str]):
        state = self.get_or_create_state(id)
        loop.create_task(state.exchange_peer(client_desc=client_desc))
                
    def answer_sync_device(self, id: str, type: str, device_id: str):
        state = self.get_or_create_state(id)
        state.set_device_id(type=type, id=device_id)
    
    def _handle_custom_msg(self, content, buffers):
        super()._handle_custom_msg(content, buffers)
        if isinstance(content, dict) and "cmd" in content and "id" in content and "args" in content:
            cmd = content.get("cmd")
            id = content.get("id")
            args = content.get("args")
            if cmd == "exchange_peer" and isinstance(args, dict) and "desc" in args:
                self.answer_exchange_peer(id, args.get("desc"))
            elif cmd == "sync_device" and isinstance(args, dict) and "type" in args and "id" in args:
                self.answer_sync_device(id, type=args["type"], device_id=args["id"])
            else:
                logger.info(f'Unhandled custom message: {content}')
        
        
    def add_video_transformer(self, callback: Callable[[VideoFrame, dict, MediaStreamTrack], Union[VideoFrame | None, Awaitable[VideoFrame | None]]]) -> MediaTransformer[VideoFrame]:
        """Add a video frame processor

        Args:
            callback (Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]] | None]): 
            a callback accept the frame and a context dict, and then return a processed frame. Support sync and async function.
            The context dict contains key "_org_frame_" at least. It represent the original frame. The users can add their own data to the context dict.

        Returns:
            MediaTransformer[VideoFrame]: A transformer instance which can be used to remove the callback by calling remove_video_transformer
        """        
        new_transformers = self.video_transformers.copy()
        transformer = MediaTransformer(callback)
        new_transformers.append(transformer)
        self.video_transformers = new_transformers
        return transformer
    
    
    def remove_video_transformer(self, transformer: MediaTransformer[VideoFrame]) -> None:
        """Remove the video frame processor

        Args:
            transformer (MediaTransformer[VideoFrame]): The transformer instance return by add_video_transformer
        """        
        new_transformers = self.video_transformers.copy()
        new_transformers.remove(transformer)
        self.video_transformers = new_transformers
        
    def add_video_poster(self, callback: Callable[[VideoFrame, dict, MediaStreamTrack], None]) -> MediaTransformer[VideoFrame]:
        """Add a video frame post processor

        Args:
            callback (Callable[[VideoFrame, dict], None]): 
            a callback accept the frame and a context dict, Should not return anything. Support sync and async function.
            The context dict contains key "_org_frame_" at least. It represent the original frame. The users can add their own data to the context dict.

        Returns:
            MediaTransformer[VideoFrame]: A poster instance which can be used to remove the callback by calling remove_video_poster
        """        
        new_posters = self.video_posters.copy()
        poster = MediaTransformer(callback)
        new_posters.append(poster)
        self.video_posters = new_posters
        return poster
    
    
    def remove_video_poster(self, poster: MediaTransformer[VideoFrame]) -> None:
        """Remove the video frame post processor

        Args:
            poster (MediaTransformer[VideoFrame]): The poster instance return by add_video_poster
        """        
        new_posters = self.video_posters.copy()
        new_posters.remove(poster)
        self.video_posters = new_posters
        
    def add_audio_transformer(self, callback: Callable[[AudioFrame, dict, MediaStreamTrack], Union[AudioFrame, Awaitable[AudioFrame]]]) -> MediaTransformer[AudioFrame]:
        """Add a audio frame processor

        Args:
            callback (Callable[[AudioFrame, dict], Union[AudioFrame, Awaitable[AudioFrame]]]): 
            a callback accept the frame and a context dict, and then return a processed frame. Support sync and async function

        Returns:
            MediaTransformer[AudioFrame]: A transformer instance which can be used to remove the callback by calling remove_audio_transformer
        """        
        new_transformers = self.audio_transformers.copy()
        transformer = MediaTransformer(callback)
        new_transformers.append(transformer)
        self.audio_transformers = new_transformers
        return transformer
    
    
    def remove_audio_transformer(self, transformer: MediaTransformer[AudioFrame]) -> None:
        """Remove the audio frame processor

        Args:
            transformer (MediaTransformer[VideoFrame]): The transformer instance return by add_video_transformer
        """        
        new_transformers = self.audio_transformers.copy()
        new_transformers.remove(transformer)
        self.audio_transformers = new_transformers
        
    def add_audio_poster(self, callback: Callable[[AudioFrame, dict, MediaStreamTrack], None]) -> MediaTransformer[AudioFrame]:
        """Add a audio frame post processor

        Args:
            callback (Callable[[AudioFrame, dict], None]): 
            a callback accept the frame and a context dict, Should not return anything. Support sync and async function.
            The context dict contains key "_org_frame_" at least. It represent the original frame. The users can add their own data to the context dict.

        Returns:
            MediaTransformer[AudioFrame]: A poster instance which can be used to remove the callback by calling remove_video_poster
        """        
        new_posters = self.audio_posters.copy()
        poster = MediaTransformer(callback)
        new_posters.append(poster)
        self.audio_posters = new_posters
        return poster
    
    
    def remove_audio_poster(self, poster: MediaTransformer[AudioFrame]) -> None:
        """Remove the audio frame post processor

        Args:
            poster (MediaTransformer[AudioFrame]): The poster instance return by add_audio_poster
        """        
        new_posters = self.audio_posters.copy()
        new_posters.remove(poster)
        self.audio_posters = new_posters
        
        
    def add_track_callback(self, callback: OnTrackCallback) -> None:
        with self.lock:
            for state in self.state_map.values():
                pc = state.pc
                tracks: list[MediaStreamTrack] = []
                for track in state.track_map.video:
                    tracks.append(track)
                for track in state.track_map.audio:
                    tracks.append(track)
                asyncio.gather(*[callback(track, pc) for track in tracks])
            self.track_callbacks.append(callback)
        
        
    def remove_track_callback(self, callback: OnTrackCallback) -> None:
        with self.lock:
            self.track_callbacks.remove(callback)
        
    
    def get_ice_servers(self) -> list[RTCIceServer]:
        servers: list[RTCIceServer] = []
        if self.iceServers and len(self.iceServers) > 0:
            for config in self.iceServers:
                if isinstance(config, str):
                    servers.append(RTCIceServer(urls=config))
                else:
                    urls = config.get('urls')
                    if not urls:
                        raise RuntimeError('urls attribute of ice server is required.')
                    username = config.get('username')
                    credential = config.get('credential')
                    credentialType = config.get('credentialType') or 'password'
                    servers.append(RTCIceServer(urls=urls, username=username, credential=credential, credentialType=credentialType))
        else:
            servers.append(RTCIceServer(urls='stun:stun.l.google.com:19302'))
        return servers
    
    def close_peers(self):
        asyncio.gather(*[state.close() for state in self.state_map.values()])
            
    def __del__(self):
        self.close_peers()
        return super().__del__()
    
class RecorderContext:
    def __init__(self, stream):
        self.started = False
        self.stream = stream
        
        
class Record:
    file: str
    format: str | None
    options: dict | None
    __container: AnyType | None
    __mode: str
    __tracks: dict[MediaStreamTrack, RecorderContext] | None
    __factory: "RecordFactory"
    
    def __init__(self, factory: "RecordFactory", file: str, format: str | None=None, options: dict | None=None) -> None:
        self.file = file
        self.format = format
        self.options = options
        self.__factory = factory
        
    @property
    def factory(self) -> "RecordFactory":
        return self.__factory
        
    @staticmethod
    def of(factory: "RecordFactory", url: str):
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
            
        return Record(factory=factory, file=res.path, format=format, options=options)
    
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
    def full_path(self):
        return self.__factory._full_path(self.file)
    
    def open(self, mode: str):
        self.close()
        self.__mode = mode
        self.__container = av_open(file=self.full_path, mode=mode, format=self.format, options=self.options)
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
            raise RuntimeError(f"The record is not open: {self.full_path}")
        if self.full_path == record.full_path:
            raise RuntimeError(f"Unable to relay tracks between records with same path: {self.full_path}")
        for track in self.__tracks.keys():
            record.add_track(track=track, open=True)
        
        
        
class RecordFactory:
    delimiter = '$'
    idpattern = r'(?a:[_a-z][_a-z0-9]*)'
    braceidpattern = None
    name: str
    template: str
    base_path: str
    base_index: int
    format: str | None
    options: dict | None
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
    
    def __init__(self, name: str, template: str, base: str=None, base_index=1, format: str | None = None, options: dict | None = None) -> None:
        self.name = name
        self.template = template
        self.base_path = base.replace('\\', '/') if base else None
        self.base_index = base_index
        self.format = format
        self.options = options
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
        
    def load(self) -> "RecordFactory":
        record_list_path = self._full_path(f'{self.name}.record_list')
        if path.exists(record_list_path):
            with open(record_list_path) as f:
                self.__record_list = [Record.of(self, line) for line in f.readlines()]
        else:
            self.__record_list = []
        return self
    
    def _ensure_loaded(self):
        if self.__record_list is None:
            raise RuntimeError(f"The record factory {self.name} has not been loaded. You must load it at first.")
            
    def append(self, record: Record):
        pass
    
    def flush(self):
        self._ensure_loaded()
        pass
                
    def new_record(self) -> Record:
        self._ensure_loaded()
        if self.__pending_record is not None:
            raise RuntimeError(f"The record factory {self.name} has a pending record. Please flush first.")
        file = self.generate(self.base_index + len(self.__record_list))
        self.__pending_record = Record(factory=self, file=file, format=self.format, options=self.options)
        return self.__pending_record
    
    def get_or_create_pending_record(self) -> Record:
        self._ensure_loaded()
        return self.__pending_record if self.__pending_record is not None else self.new_record()
        
                    
        
RecordFactory.__init_subclass__()
        
class WebCamRecorder:
    post: bool
    def __init__(self, widget: WebCamWidget, file: str | IO, post: bool=True, format: str=None, options:dict={}, **kargs) -> None:
        self.widget = widget
        self.post = post
        self.__container = av_open(file=file, format=format, mode="w", options=options)
        self.__tracks = {}
        self.recording = False
        self.video_poster = MediaTransformer[VideoFrame]
        self.audio_poster = MediaTransformer[AudioFrame]
        self.lock = asyncio.Lock()
        self.widget.add_track_callback(self.on_add_track)
        
    def _add_Track(self, track: MediaStreamTrack):
        """
        Add a track to be recorded.

        :param track: A :class:`aiortc.MediaStreamTrack`.
        """
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
        
    async def on_add_track(self, track: MediaStreamTrack, pc: RTCPeerConnection) -> None:
        async with self.lock:
            self._add_Track(track=track)
            if self.recording:
                self.video_poster = self.widget.add_video_poster(self.on_frame)
                self.audio_poster = self.widget.add_audio_poster(self.on_frame)
                
    async def on_frame(self, frame: VideoFrame | AudioFrame, ctx: dict, track: MediaStreamTrack):
        async with self.lock:
            context: RecorderContext = self.__tracks.get(track)
            if not context:
                return
            if not self.post:
                frame = ctx["_org_frame_"]
            if not context.started:
                # adjust the output size to match the first frame
                if isinstance(frame, VideoFrame):
                    context.stream.width = frame.width
                    context.stream.height = frame.height
                context.started = True
            for packet in context.stream.encode(frame):
                self.__container.mux(packet)

            
    async def a_start(self) -> None:
        async with self.lock:
            if not self.recording:
                self.recording = True
                self.video_poster = self.widget.add_video_poster(self.on_frame)
                self.audio_poster = self.widget.add_audio_poster(self.on_frame)
        
    async def a_stop(self) -> None:
        async with self.lock:
            if self.recording:
                self.recording = False
                self.widget.remove_video_poster(self.video_poster)
                self.widget.remove_audio_poster(self.audio_poster)
                if self.__container:
                    for track, context in self.__tracks.items():
                        for packet in context.stream.encode(None):
                            self.__container.mux(packet)
                    self.__tracks = {}
                    self.__container.close()
                    self.__container = None
                    
    def start(self) -> None:
        asyncio.create_task(self.a_start())
        
    def stop(self) -> None:
        asyncio.create_task(self.a_stop())