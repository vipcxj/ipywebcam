#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Xiaojing Chen.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

from os import path
import asyncio
import inspect
import logging
from typing import Awaitable, Callable, Union
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay, MediaStreamTrack
from av import VideoFrame
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


DEFAULT_ICE_SERVERS: list[RTCIceServer] = [
    RTCIceServer(urls='stun:stun.l.google.com:19302'),
    RTCIceServer(urls='stun:23.21.150.121'),
    RTCIceServer(urls='stun:stun01.sipphone.com'),
    RTCIceServer(urls='stun:stun.ekiga.net'),
    RTCIceServer(urls='stun:stun.fwdnet.net'),
    RTCIceServer(urls='stun:stun.ideasip.com'),
    RTCIceServer(urls='stun:stun.iptel.org'),
    RTCIceServer(urls='stun:stun.rixtelecom.se'),
    RTCIceServer(urls='stun:stun.schlund.de'),
    RTCIceServer(urls='stun:stunserver.org'),
    RTCIceServer(urls='stun:stun.softjoys.com'),
    RTCIceServer(urls='stun:stun.voiparound.com'),
    RTCIceServer(urls='stun:stun.voipstunt.com'),
    RTCIceServer(urls='stun:stun.voxgratia.org'),
    RTCIceServer(urls='stun:stun.xten.com'),
];


relay = MediaRelay()

class VideoTransformer:
    def __init__(self, callback: Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]]], context: dict = {}) -> None:
        self.callback = callback
        self.context = context
        
    async def transform(self, frame: VideoFrame) -> VideoFrame:
        if inspect.iscoroutinefunction(self.callback):
            frame = await self.callback(frame, self.context)
        else:
            frame = self.callback(frame, self.context)
        return frame


class WithTransformers:
    transformers: list[VideoTransformer] = []

class VideoTransformTrack(MediaStreamTrack):
    kind = "video"
    
    def __init__(self, track: MediaStreamTrack, withTransformers: WithTransformers):
        super().__init__()
        self.track = track
        self.withTransformers = withTransformers
        
    async def recv(self) -> VideoFrame:
        frame: VideoFrame = await self.track.recv()
        try:
            for transformer in self.withTransformers.transformers:
                frame = await transformer.transform(frame)
            return frame
        except Exception as e:
            logger.exception(e)

class WebCamWidget(DOMWidget, WithTransformers):
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
    
    devices = List(Dict(), default_value=[]).tag(sync=True)
    
    device = Dict(default_value=None, allow_none=True).tag(sync=True)
    
    state = Unicode('closed', read_only=True).tag(sync=True)
    
    autoplay = Bool(True, allow_none=True).tag(sync=True)
    
    controls = Bool(True, allow_none=True).tag(sync=True)
    
    crossOrigin = Enum(set(['not-support', 'anonymous', 'use-credentials']), default_value='not-support').tag(sync=True)
    
    width = Float(default_value=None, allow_none=True).tag(sync=True)
    
    height = Float(default_value=None, allow_none=True).tag(sync=True)
    
    playsInline = Bool(True, allow_none=True).tag(sync=True)
    
    muted = Bool(False, allow_none=True).tag(sync=True)
    
    devicesWidget = Dropdown(options=[], value=None, description='cameras')
    
    pc: RTCPeerConnection = None
    state: int = 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        def transform_devices_to_options(devices): 
            options = [(device['label'] or device['deviceId'], device) for device in devices]
            options.insert(0, ('', None))
            return options
        def transform_options_to_devices(options):
            return [device for (_, device) in options if device]

        link((self.devicesWidget, "options"), (self, "devices"), transform=(transform_options_to_devices, transform_devices_to_options))
        link((self.devicesWidget, "value"), (self, "device"))
        
        
    def add_transformer(self, callback: Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]]]) -> VideoTransformer:
        """Add a frame processor

        Args:
            callback (Callable[[VideoFrame, dict], Union[VideoFrame, Awaitable[VideoFrame]]]): 
            a callback accept the frame and a context dict, and then return a processed frame. Support sync and async function

        Returns:
            VideoTransformer: A transformer instance which can be used to remove the callback by calling remove_transformer
        """        
        new_transformers = self.transformers.copy()
        transformer = VideoTransformer(callback)
        new_transformers.append(transformer)
        self.transformers = new_transformers
        return transformer
    
    
    def remove_transformer(self, transformer: VideoTransformer) -> None:
        """Remove the frame processor

        Args:
            transformer (VideoTransformer): The transformer instance return by add_transformer
        """        
        new_transformers = self.transformers.copy()
        new_transformers.remove(transformer)
        self.transformers = new_transformers
        
    
    async def new_pc_connection(self, client_desc: dict[str, str]):
        logger.debug("new_pc_connection")
        if self.state >= 0:
            try:
                self.state = -1
                await self.close_pc_connection(self.pc)
                offer = RTCSessionDescription(**client_desc)
                self.pc = pc = RTCPeerConnection(RTCConfiguration(DEFAULT_ICE_SERVERS))
                
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
                        
                # handle offer
                await pc.setRemoteDescription(offer)
                # send answer
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                logger.debug(f"send answer: {answer} to client.")
                self.server_desc = { "sdp": answer.sdp, "type": answer.type }
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
            
    @observe("device")    
    def on_device_change(self, change):
        logger.debug(f"device change from {change.old} to {change.new}")
            
    def __del__(self):
        loop.create_task(self.close_pc_connection(self.pc))
        return super().__del__()
