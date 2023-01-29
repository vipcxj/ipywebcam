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
from dataclasses import dataclass
from threading import RLock
import inspect
import logging
from typing import Awaitable, Callable, Generic, Optional, TypeVar, Union, Any as AnyType
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay, MediaStreamTrack
from av import VideoFrame, AudioFrame
from ipywidgets import DOMWidget, Dropdown
from traitlets import Any, Bool, Float, List, Unicode, Dict, Enum, observe, link
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
    video_transformers: list[MediaTransformer[VideoFrame]] = []
    audio_transformers: list[MediaTransformer[AudioFrame]] = []

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
    return [(device['label'] or device['deviceId'], device) for device in devices]


def transform_options_to_devices(options):
    return [device for (_, device) in options if device]


def find_device_from_options(options: list[tuple[str, dict]], device_id: str) -> dict | None:
    for _, device in options:
        if device.get("deviceId") == device_id:
            return device
    return None
@dataclass
class State:
    id: str
    widget: "WebCamWidget"
    pc: RTCPeerConnection = None
    client_desc: RTCSessionDescription = None
    server_desc: RTCSessionDescription = None
    lock: RLock = RLock()
    a_lock: asyncio.Lock = asyncio.Lock()
    video_input_devices: list[dict] = []
    video_input_device_id: str | None = None
    video_input_selector: Dropdown = Dropdown(options=[], value=None, description='Video Input')
    audio_input_devices: list[dict] = []
    audio_input_device_id: str | None = None
    audio_input_selector: Dropdown = Dropdown(options=[], value=None, description='Audio Input')
    audio_output_devices: list[dict] = []
    audio_output_device_id: str | None = None
    audio_output_selector: Dropdown = Dropdown(options=[], value=None, description='Audio Output')
    
    def __post_init__(self):
        def on_display(type: str, *args):
            self.request_devices(id, type=type)
        self.video_input_selector.on_displayed(lambda *args: on_display("video_input", *args))
        self.observe(id, "video_input", lambda change: self.notify_device_change(id, type="video_input", change=change))
        self.audio_input_selector.on_displayed(lambda *args: on_display("audio_input", *args))
        self.observe(id, "audio_input", lambda change: self.notify_device_change(id, type="audio_input", change=change))
        self.audio_output_selector.on_displayed(lambda *args: on_display("audio_output", *args))
        self.observe(id, "audio_output", lambda change: self.notify_device_change(id, type="audio_output", change=change))
        
    
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
            selector = self.get_device_selector(type=type)
            device = find_device_from_options(selector.options, id)
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
        
        
    def set_devices(self, type: str, devices: list[dict]):
        with self.lock:
            selector = self.get_device_selector(type=type)
            selector.options = transform_devices_to_options(devices=devices)
            device_id = self.get_device_id(type)
            selector.value = None if device_id is None else find_device_from_options(selector.options, device_id)
            
            
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
            with self.a_lock:
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
                        with self.a_lock:
                            await pc.close()
                            self.pc = None
                    
                @pc.on("error")
                async def on_error(error):
                    logger.exception(error)
                
                @pc.on("track")
                def on_track(track):
                    self.log_info(f"Track {track.kind} received")
                    if track.kind == "video":
                        pc.addTrack(relay.subscribe(VideoTransformTrack(track, self)))
                    elif track.kind == "audio":
                        pc.addTrack(relay.subscribe(AudioTransformTrack(track, self)))
                    
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
        with self.a_lock:
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
    
    client_desc = Dict(
        key_trait=Enum(set(["sdp", "type"])),
        per_key_traits={"sdp": Unicode(), "type": Enum(set(["offer", "pranswer", "answer", "rollback"]))},
        default_value=None,
        allow_none=True
    ).tag(sync=True)
    
    server_desc = Dict(
        key_trait=Enum(set(["sdp", "type"])),
        per_key_traits={"sdp": Unicode(), "type": Enum(set(["offer", "pranswer", "answer", "rollback"]))},
        default_value=None,
        allow_none=True
    ).tag(sync=True)
     
    iceServers = List(Any(), default_value=[]).tag(sync=True)
    
    autoplay = Bool(True, allow_none=True).tag(sync=True)
    
    controls = Bool(True, allow_none=True).tag(sync=True)
    
    crossOrigin = Enum(set(['not-support', 'anonymous', 'use-credentials']), default_value='not-support').tag(sync=True)
    
    width = Float(default_value=None, allow_none=True).tag(sync=True)
    
    height = Float(default_value=None, allow_none=True).tag(sync=True)
    
    playsInline = Bool(True, allow_none=True).tag(sync=True)
    
    muted = Bool(False, allow_none=True).tag(sync=True)
    
    constraints = Dict(default_value=None, allow_none=True).tag(sync=True)
    
    video_input_devices = List(Dict(), default_value=[]).tag(sync=True)
    audio_input_devices = List(Dict(), default_value=[]).tag(sync=True)
    audio_output_devices = List(Dict(), default_value=[]).tag(sync=True)
    
    video_input_devices_ready: bool = False
    audio_input_devices_ready: bool = False
    audio_output_devices_ready: bool = False
    
    video_input_device = Dict(default_value=None, allow_none=True).tag(sync=True)
    video_input_device_dirty = False
    audio_input_device = Dict(default_value=None, allow_none=True).tag(sync=True)
    audio_input_device_dirty = False
    audio_output_device = Dict(default_value=None, allow_none=True).tag(sync=True)
    audio_output_device_dirty = False
    
    video_input_selector = Dropdown(options=[], value=None, description='Video input device')
    audio_input_selector = Dropdown(options=[], value=None, description='Audio input device')
    audio_output_selector = Dropdown(options=[], value=None, description='Audio output device')
    
    video_codecs = List(Unicode(), default_value=[]).tag(sync=True)
    video_codec = Unicode(default_value=None, allow_none=True).tag(sync=True)
    video_codec_selector = Dropdown(options=[], value=None, description='Video codec')
    video_codecs_ready = False
    
    pc: RTCPeerConnection = None
    state: int = 0
    state_map: dict[str, State] = {}
    lock: RLock = RLock()
    
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
        def transform_devices_to_options(devices): 
            return [(device['label'] or device['deviceId'], device) for device in devices]
        def transform_options_to_devices(options):
            return [device for (_, device) in options if device]
        self.on_displayed(lambda w: print(type(w)))

        link((self.video_input_selector, "options"), (self, "video_input_devices"), transform=(transform_options_to_devices, transform_devices_to_options))
        link((self.video_input_selector, "value"), (self, "video_input_device"))
        link((self.audio_input_selector, "options"), (self, "audio_input_devices"), transform=(transform_options_to_devices, transform_devices_to_options))
        link((self.audio_input_selector, "value"), (self, "audio_input_device"))
        link((self.audio_output_selector, "options"), (self, "audio_output_devices"), transform=(transform_options_to_devices, transform_devices_to_options))
        link((self.audio_output_selector, "value"), (self, "audio_output_device"))
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
            def callback(_, content) -> None:
                if isinstance(content, dict) and content.get("ans") == cmd:
                    source_id: str = content.get("id")
                    if not target_id or source_id == target_id:
                        on_result(source_id, content.get("res"))
                        self.on_msg(callback, True)
            logger.log(f'add command on_result callback: {target_id(callback)}')
            self.on_msg(callback)
        
    def answer(self, cmd: str, target_id: str, content: AnyType) -> None:
        self.send({ "ans": cmd, "id": target_id, "res": content })
        
    def notify_device_change(self, id: str, type: str, change: dict):
        state = self.get_or_create_state(id)
        self.send_command("notify_device_change", id, { "type": type, "change": change })
        
        
    def get_or_create_state(self, id: str) -> State:
        with self.lock:
            state = self.state_map.get(id)
            if state is None:
                state = State(id=id, widget=self)
            return state
        
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
                
    
    def _handle_custom_msg(self, content, buffers):
        super()._handle_custom_msg(content, buffers)
        if isinstance(content, dict) and "cmd" in content and "id" in content and "args" in content:
            cmd = content.get("cmd")
            id = content.get("id")
            args = content.get("args")
            if cmd == "exchange_peer" and isinstance(args, dict) and "desc" in args:
                self.answer_exchange_peer(id, args.get("desc"))
        
        
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
