#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Xiaojing Chen.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

import asyncio
import inspect
import logging
import sys
import uuid
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, field
from os import path
from threading import RLock
from typing import Any as AnyType
from typing import Awaitable, Callable, Generic, Optional, TypeVar, Union

from aiortc import (RTCConfiguration, RTCIceServer, RTCPeerConnection,
                    RTCSessionDescription)
from aiortc.contrib.media import MediaRelay, MediaStreamTrack
from av import AudioFrame, VideoFrame
from IPython import display
from ipywidgets import DOMWidget, Dropdown, Output
from traitlets import Any, Bool, Dict, Enum, Float, List, Unicode, link

from ._frontend import module_name, module_version
from .common import OutputContextManager, BaseWidget, ContextHelper

logger = logging.getLogger("ipywebcam")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(path.join(path.dirname(__file__), "ipywebcam.log"))
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

logger.info("I am loaded")

relay = MediaRelay()

MT = TypeVar('MT', VideoFrame, AudioFrame)
class MediaTransformer(Generic[MT]):
    enabled: bool = True
    def __init__(self, callback: Callable[[MT, dict, MediaStreamTrack], Union[MT, Awaitable[MT]]], context: dict | None = None) -> None:
        self.callback = callback
        self.context = context if context is not None else {}
        self.iscoroutinefunction = inspect.iscoroutinefunction(self.callback)
        sig = inspect.signature(self.callback)
        self.require_ctx =  len(sig.parameters) > 1
        self.require_track = len(sig.parameters) > 2
        
    async def transform(self, frame: MT, track: MediaStreamTrack=None) -> MT | None:
        if not self.enabled:
            return frame
        if self.iscoroutinefunction:
            if self.require_ctx and self.require_track:
                out_frame = await self.callback(frame, self.context, track)
            elif self.require_ctx:
                out_frame = await self.callback(frame, self.context)
            else:
                out_frame = await self.callback(frame)
        else:
            if self.require_ctx and self.require_track:
                out_frame = self.callback(frame, self.context, track)
            elif self.require_ctx:
                out_frame = self.callback(frame, self.context)
            else:
                out_frame = self.callback(frame)
        return out_frame


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
    output: Output | None
    
    def __init__(self, track: MediaStreamTrack, withTransformers: WithMediaTransformers, output: Output | None = None):
        super().__init__()
        self.track = track
        self.withTransformers = withTransformers
        self.output = output
        
    async def recv(self) -> MT:
        frame: MT = await self.track.recv()
        org_frame = frame
        output_context_manager = OutputContextManager(self.output) if self.output is not None else nullcontext
        for transformer in self.__class__.get_transformers(self.withTransformers):
            out_frame = None
            transformer.context[ContextHelper.KEY_ORG_FRAME] = org_frame
            try:
                async with output_context_manager:
                    out_frame = await transformer.transform(frame=frame, track=self.track)
            except Exception:
                transformer.enabled = False
            frame = out_frame if out_frame is not None else frame
            
        if org_frame is not None and frame is not None:
            if hasattr(org_frame, "pts") and hasattr(frame, "pts") and frame.pts is None:
                frame.pts = org_frame.pts
            if hasattr(org_frame, "time_base") and hasattr(frame, "time_base") and frame.time_base is None:
                frame.time_base = org_frame.time_base
                
        for poster in self.__class__.get_posters(self.withTransformers):
            poster.context[ContextHelper.KEY_ORG_FRAME] = org_frame
            try:
                async with output_context_manager:
                    await poster.transform(frame=frame, track=self.track)
            except Exception:
                poster.enabled = False
        return frame
    
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
                        pc.addTrack(relay.subscribe(VideoTransformTrack(track, self.widget, self.widget.output)))
                    elif track.kind == "audio":
                        pc.addTrack(relay.subscribe(AudioTransformTrack(track, self.widget, self.widget.output)))
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

class WebCamWidget(DOMWidget, BaseWidget, WithMediaTransformers):
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
    output = Output()
    
    _model_name = Unicode('WebCamModel').tag(sync=True)
    _view_name = Unicode('WebCamView').tag(sync=True)
     
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
        super().__init__(logger=logger, **kwargs)
        self.state_map = {}
        self.lock = RLock()
        self.track_callbacks = []
        link((self.video_codec_selector, 'options'), (self, 'video_codecs'))
        link((self.video_codec_selector, 'value'), (self, 'video_codec'))
        self.add_answer("exchange_peer", self.answer_exchange_peer)
        self.add_answer("sync_device", self. answer_sync_device)
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
        
        
    def answer_exchange_peer(self, id: str, cmd: str, args: dict):
        if "desc" in args:
            client_desc: dict[str, str] = args["desc"]
            state = self.get_or_create_state(id)
            asyncio.create_task(state.exchange_peer(client_desc=client_desc))
                
    def answer_sync_device(self, id: str, cmd: str, args: dict):
        if "type" in args and "id" in args:
            type: str = args["type"]
            device_id: str = args["id"]
            state = self.get_or_create_state(id)
            state.set_device_id(type=type, id=device_id)
        
        
    def add_video_transformer(self, callback: Callable[[VideoFrame, dict, MediaStreamTrack], Union[VideoFrame | None, Awaitable[VideoFrame | None]]]) -> MediaTransformer[VideoFrame]:
        """Add a video frame processor

        Args:
            callback (Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]] | None]): 
            a callback accept the frame and a context dict, and then return a processed frame. Support sync and async function.
            The context dict contains key "__org_frame" at least. It represent the original frame. The users can add their own data to the context dict.

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
        self.video_transformers = [t for t in self.video_transformers if t != transformer]
        
    def add_video_poster(self, callback: Callable[[VideoFrame, dict, MediaStreamTrack], None]) -> MediaTransformer[VideoFrame]:
        """Add a video frame post processor

        Args:
            callback (Callable[[VideoFrame, dict], None]): 
            a callback accept the frame and a context dict, Should not return anything. Support sync and async function.
            The context dict contains key "__org_frame" at least. It represent the original frame. The users can add their own data to the context dict.

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
        self.video_posters = [p for p in self.video_posters if p != poster]
        
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
        self.audio_transformers = [t for t in self.audio_transformers if t != transformer]
        
    def add_audio_poster(self, callback: Callable[[AudioFrame, dict, MediaStreamTrack], None]) -> MediaTransformer[AudioFrame]:
        """Add a audio frame post processor

        Args:
            callback (Callable[[AudioFrame, dict], None]): 
            a callback accept the frame and a context dict, Should not return anything. Support sync and async function.
            The context dict contains key "__org_frame" at least. It represent the original frame. The users can add their own data to the context dict.

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
        self.audio_posters = [p for p in self.audio_posters if p != poster]
        
        
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
            if callback in self.track_callbacks:
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
        
    def _ipython_display_(self):
        display.display(super(), self.output)
            
    def __del__(self):
        self.close_peers()
        return super().__del__()
