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
from threading import RLock
import inspect
import logging
from typing import Awaitable, Callable, Generic, Optional, TypeVar, Union, Any as AnyType
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay, MediaStreamTrack
from av import VideoFrame, AudioFrame
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
    def __init__(self, callback: Callable[[MT, dict], Union[MT, Awaitable[MT]]], context: dict = {}) -> None:
        self.callback = callback
        self.context = context
        
    async def transform(self, frame: MT) -> MT:
        if inspect.iscoroutinefunction(self.callback):
            frame = await self.callback(frame, self.context)
        else:
            frame = self.callback(frame, self.context)
        return frame


class WithMediaTransformers:
    video_transformers: list[MediaTransformer[VideoFrame]]
    audio_transformers: list[MediaTransformer[AudioFrame]]
    
    def __init__(self) -> None:
        self.video_transformers = []
        self.audio_transformers = []

class MediaTransformTrack(MediaStreamTrack, Generic[MT], metaclass=ABCMeta):
    
    def __init__(self, track: MediaStreamTrack, withTransformers: WithMediaTransformers):
        super().__init__()
        self.track = track
        self.withTransformers = withTransformers
        
    async def recv(self) -> MT:
        frame: MT = await self.track.recv()
        try:
            for transformer in self.__class__.get_transformers(self.withTransformers):
                frame = await transformer.transform(frame)
            return frame
        except Exception as e:
            logger.exception(e)
            
    
    @staticmethod        
    @abstractmethod
    def get_transformers(withTransformers: WithMediaTransformers) -> list[MediaTransformer[MT]]:
        pass
            
            
class VideoTransformTrack(MediaTransformTrack[VideoFrame]):
    kind = 'video'
    
    @staticmethod
    def get_transformers(withTransformers: WithMediaTransformers) -> list[MediaTransformer[VideoFrame]]:
        return withTransformers.video_transformers
    
class AudioTransformTrack(MediaTransformTrack[AudioFrame]):
    kind = 'audio'
    
    @staticmethod
    def get_transformers(withTransformers: WithMediaTransformers) -> list[MediaTransformer[AudioFrame]]:
        return withTransformers.audio_transformers


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
    video_input_selector: Dropdown = field(default_factory=lambda: Dropdown(options=[], value=None, description='Video Input'))
    audio_input_devices: list[dict] = field(default_factory=list)
    audio_input_devices_busy: bool = False
    audio_input_device_id: str | None = None
    audio_input_selector: Dropdown = field(default_factory=lambda: Dropdown(options=[], value=None, description='Audio Input'))
    audio_output_devices: list[dict] = field(default_factory=list)
    audio_output_devices_busy: bool = False
    audio_output_device_id: str | None = None
    audio_output_selector: Dropdown = field(default_factory=lambda: Dropdown(options=[], value=None, description='Audio Output'))
    
    def __post_init__(self):
        def on_display(type: str, *args):
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
                
        self.video_input_selector.on_displayed(lambda *args: on_display("video_input", *args))
        self.observe(id, "video_input", create_handler("video_input"))
        self.audio_input_selector.on_displayed(lambda *args: on_display("audio_input", *args))
        self.observe(id, "audio_input", create_handler("audio_input"))
        self.audio_output_selector.on_displayed(lambda *args: on_display("audio_output", *args))
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
        
    @contextmanager
    def hold_devices(self, type: str):
        try:
            if type == 'video_input':
                self.video_input_selector.disabled = True
                self.video_input_devices_busy = True
            elif type == 'audio_input':
                self.audio_input_selector.disabled = True
                self.audio_input_devices_busy = True
            elif type == 'audio_output':
                self.audio_output_selector.disabled = True
                self.audio_output_devices_busy = True
            else:
                raise RuntimeError(f'Invalid device type {type}')
            yield
        finally:
            if type == 'video_input':
                self.video_input_devices_busy = False
                self.video_input_selector.disabled = False
            elif type == 'audio_input':
                self.audio_input_devices_busy = False
                self.audio_input_selector.disabled = False
            elif type == 'audio_output':
                self.audio_output_devices_busy = False
                self.audio_output_selector.disabled = False
            else:
                raise RuntimeError(f'Invalid device type {type}')
            
            
    def is_devices_busy(self, type: str):
        if type == 'video_input':
            return self.video_input_devices_busy
        elif type == 'audio_input':
            return self.audio_input_devices_busy
        elif type == 'audio_output':
            return self.audio_output_devices_busy
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
        
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
                    self.pc.close()
                self.client_desc = offer = RTCSessionDescription(**client_desc)
                self.pc = RTCPeerConnection(RTCConfiguration(self.widget.get_ice_servers()))
                pc = self.pc
                @pc.on("icegatheringstatechange")
                async def on_iceconnectionstatechange():
                    self.log_info(f"Ice connection state is {pc.iceGatheringState}")
                
                @pc.on("iceconnectionstatechange")
                async def on_iceconnectionstatechange():
                    self.log_info(f"Ice connection state is {pc.iceConnectionState}")
                    
                @pc.on("signalingstatechange")
                async def on_signalingstatechange():
                    self.log_info(f"Signaling state is {pc.signalingState}")
                
                @pc.on("connectionstatechange")    
                async def on_connectionstatechange():
                    self.log_info(f"Connection state is {pc.connectionState}")
                    if pc.connectionState == "failed":
                        async with self.a_lock:
                            await pc.close()
                            self.pc = None
                    
                @pc.on("error")
                async def on_error(error):
                    logger.exception(error)
                
                @pc.on("track")
                def on_track(track):
                    self.log_info(f"Track {track.kind} received")
                    if track.kind == "video":
                        pc.addTrack(relay.subscribe(VideoTransformTrack(track, self.widget)))
                    elif track.kind == "audio":
                        pc.addTrack(relay.subscribe(AudioTransformTrack(track, self.widget)))
                    
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
        
        
    def add_video_transformer(self, callback: Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]]]) -> MediaTransformer[VideoFrame]:
        """Add a video frame processor

        Args:
            callback (Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]]]): 
            a callback accept the frame and a context dict, and then return a processed frame. Support sync and async function

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
        
    def add_audio_transformer(self, callback: Callable[[AudioFrame, dict], Union[AudioFrame, Awaitable[AudioFrame]]]) -> MediaTransformer[AudioFrame]:
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
        
            
    def __del__(self):
        loop.create_task(asyncio.gather([state.close() for state in self.state_map.values()]))
        return super().__del__()
