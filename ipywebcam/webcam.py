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
import inspect
import logging
from typing import Awaitable, Callable, Generic, Optional, TypeVar, Union
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
    
    state = Unicode('closed', read_only=True).tag(sync=True)
    
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
            
            
    def send_command(self, cmd: str, args: dict, on_result: Callable[[any], None]) -> None:
        self.send({ "cmd": cmd, "args": args })
        def callback(_, content) -> None:
            if isinstance(content, dict) and content.get("ans") == cmd:
                on_result(content.get("res"))
                self.on_msg(callback, True)
        logger.log(f'add command on_result callback: {id(callback)}')
        self.on_msg(callback)
        
    def answer(self, cmd: str, content: dict) -> None:
        self.send({ "ans": cmd, "res": content })
            
    def get_device_selector(self, type: str) -> Dropdown:
        if type == 'video_input':
            return self.video_input_selector
        elif type == 'audio_input':
            return self.audio_input_selector
        elif type == 'audio_output':
            return self.audio_output_selector
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def is_device_dirty(self, type: str) -> bool:
        if type == 'video_input':
            return self.video_input_device_dirty
        elif type == 'audio_input':
            return self.audio_input_device_dirty
        elif type == 'audio_output':
            return self.audio_output_device_dirty
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def set_device_dirty(self, type: str, dirty: bool) -> None:
        if type == 'video_input':
            self.video_input_device_dirty = dirty
        elif type == 'audio_input':
            self.audio_input_device_dirty = dirty
        elif type == 'audio_output':
            self.audio_output_device_dirty = dirty
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def get_device(self, type: str) -> dict:
        if type == 'video_input':
            return self.video_input_device
        elif type == 'audio_input':
            return self.audio_input_device
        elif type == 'audio_output':
            return self.audio_output_device
        else:
            raise RuntimeError(f'Invalid device type {type}')
        
    def _set_device(self, type: str, device: Optional[dict]) -> None:
        if type == 'video_input':
            self.video_input_device = device
        elif type == 'audio_input':
            self.audio_input_device = device
        elif type == 'audio_output':
            self.audio_output_device = device
        else:
            raise RuntimeError(f'Invalid device type {type}')
            
        
    def set_device(self, type: str, device: Optional[dict], dirty: bool = False) -> bool:
        """set device

        Args:
            type (str): device type
            device (Optional[dict]): device info
            dirty (bool, optional): If true, the device should be sync to selector immediately or later. 
            If false and current device is dirty, the input device param is ignored and the current device info should be sync to the selector immediately or later. 
            Defaults to False.
            
        Returns:
            Wether the device is changed.

        Raises:
            RuntimeError: invalid type value
        """        
        selector = self.get_device_selector(type)
        cur_device = self.get_device(type)
        if cur_device == device:
            return False
        
        if dirty:
            self._set_device(type, device)
            if device and self.is_in_selector(selector, device):
                selector.value = device
                self.set_device_dirty(type, False)
            else:
                self.set_device_dirty(type, True)
            return True
        else:
            if self.is_device_dirty(type):
                cur_device = self.get_device(type)
                if cur_device and cur_device != selector.value and self.is_in_selector(selector, cur_device):
                    selector.value = cur_device
                    self.set_device_dirty(type, False)
                return False
            else:
                self._set_device(type, device)
                return True
                    
        
    def get_device_id(self, device: Optional[dict]) -> Optional[str]:
        return device['deviceId'] if device is not None else None
    
    def is_in_selector(self, selector: Dropdown, device: dict):
        pass
            
    def bind_device_selector(self, type: str):
        selector = self.get_device_selector(type)
        selector.on_displayed(lambda w: self.request_devices(type))
        def handle_device_change(change):
            old_id = self.get_device_id(self.get_device(type))
            new_id = self.get_device_id(change.new)
            if old_id != new_id:
                if self.set_device(type, change.new):
                    self.send_device_id(type, new_id)
        selector.observe(handle_device_change, 'value')
    
    def request_devices(self, type: str):
        self.send({ 'msg': 'request_devices', 'type': type })
        
    def send_device_id(self, type: str, device_id: Optional[str]) -> None:
        self.send({ 'msg': 'send_device_id', 'type': type, 'data': device_id })
    
    
    def handle_answer_request_devices(self, type: str, devices: list):
        """The answer of 'request_devices'

        Args:
            type (str): device type
            devices (list): list of device info
        """
        selector = self.get_device_selector(type)
        selector.options = devices
        
    def handle_answer_sync_device(self, type: str, device: Optional[str], req_id: str) -> None:
        """The client request that the server should use its device info

        Args:
            type (str): device type
            device (Optional[str]): device info
            req_id (str): used to 
        """
        self.set_device(type, device, True)
        
    def handle_request_device(self, type: str) -> None:
        """client request the device info stored in the server

        Args:
            type (str): device type
        """
        self.send({ 'msg': 'answer_device', 'type': type, 'device': self.get_device(type) })
                
    
    def _handle_custom_msg(self, content, buffers):
        super()._handle_custom_msg(content, buffers)
        if isinstance(content, dict) and "ans" in content:
            cmd = content.get("ans")
            
        msg = content.get('msg')
        if msg == 'answer_devices':
            self.handle_answer_request_devices(content['type'], content['devices'])
        elif msg == 'sync_device':
            self.handle_answer_sync_device(content['type'], content['device'])
        elif msg == 'request_device':
            self.handle_request_device(content['type'])
            
        
        
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
    
    async def new_pc_connection(self, client_desc: dict[str, str]):
        logger.debug("new_pc_connection")
        if self.state >= 0:
            try:
                self.state = -1
                await self.close_pc_connection(self.pc)
                offer = RTCSessionDescription(**client_desc)
                self.pc = pc = RTCPeerConnection(RTCConfiguration(self.get_ice_servers()))
                
                @pc.on("icegatheringstatechange")
                async def on_iceconnectionstatechange():
                    logger.info("Ice connection state is %s", pc.iceGatheringState)
                
                @pc.on("iceconnectionstatechange")
                async def on_iceconnectionstatechange():
                    logger.info("Ice connection state is %s", pc.iceConnectionState)
                    
                @pc.on("signalingstatechange")
                async def on_signalingstatechange():
                    logger.info("Signaling state is %s", pc.signalingState)
                
                @pc.on("connectionstatechange")    
                async def on_connectionstatechange():
                    logger.info("Connection state is %s", pc.connectionState)
                    if pc.connectionState == "failed":
                        await self.close_pc_connection(pc)
                        self.state = 2
                        
                @pc.on("error")
                async def on_error(error):
                    logger.exception(error)
                                
                @pc.on("track")
                def on_track(track):
                    logger.info("Track %s received", track.kind)
                    if track.kind == "video":
                        pc.addTrack(relay.subscribe(VideoTransformTrack(track, self)))
                    elif track.kind == "audio":
                        pc.addTrack(relay.subscribe(AudioTransformTrack(track, self)))
                        
                # handle offer
                await pc.setRemoteDescription(offer)
                # send answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                # my_sdp = re.sub(r'c=IN IP4 (\d+\.\d+\.\d+\.\d+)', 'c=IN IP4 140.210.206.15', pc.localDescription.sdp)
                my_sdp = pc.localDescription.sdp
                self.server_desc = { "sdp": my_sdp, "type": pc.localDescription.type }
                self.state = 1
            except Exception as e:
                logger.exception(e)
                self.state = 2
    
    
    async def close_pc_connection(self, pc: RTCPeerConnection):
        if pc:
            logger.debug("closing pc")
            await pc.close()
            logger.debug("closed pc")
            if self.pc == pc:
                self.pc = None
        
    
    @observe("client_desc")
    def on_client_desc_change(self, change):
        try:
            logger.debug(f'receive client_desc change from {change.old} to {change.new}')
            logger.debug(f'loop is running? {loop.is_running()}')
            loop.create_task(self.new_pc_connection(change.new))
            logger.debug("on_client_desc_change end")
        except Exception as e:
            logger.error(e)
            
            
    def may_send_ready(self) -> None:
        if (self.video_codecs_ready and self.video_input_devices_ready and self.audio_input_devices_ready and self.audio_output_devices_ready):
            self.send({ 'msg': 'ready' })
            
    
    @observe("video_input_devices")
    def on_video_input_devices_change(self, change):
        self.video_input_devices_ready = True
        self.may_send_ready()
        
    @observe("audio_input_devices")
    def on_audio_input_devices_change(self, change):
        self.audio_input_devices_ready = True
        self.may_send_ready()
        
    @observe("audio_output_devices")
    def on_audio_output_devices_change(self, change):
        self.audio_output_devices_ready = True
        self.may_send_ready()
        
    @observe("video_codecs")
    def on_video_codecs_change(self, change):
        self.video_codecs_ready = True
        self.may_send_ready()
        
            
    def __del__(self):
        loop.create_task(self.close_pc_connection(self.pc))
        return super().__del__()
