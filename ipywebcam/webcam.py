#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Xiaojing Chen.
# Distributed under the terms of the Modified BSD License.

"""
TODO: Add module docstring
"""

import atexit
import asyncio
import logging
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaBlackhole, MediaRelay
from ipywidgets import DOMWidget
from traitlets import Unicode, Dict, Enum, observe
from typing_extensions import TypeAlias
from ._frontend import module_name, module_version

logger = logging.getLogger("ipywebcam")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("C:\\Users\\vipcx\\Projects\\ipywebcam\\ipywebcam.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
loop = asyncio.get_event_loop()

@atexit.register
def on_exit():
    logger.info("I am unloaded")
    asyncio.wait(on_shutdown)
    loop.close()

logger.info("I am loaded")

PcSet: TypeAlias = "set[RTCPeerConnection]"

pcs: PcSet = set()
relay = MediaRelay()


async def on_shutdown():
    # close peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


class WebCamWidget(DOMWidget):
    """TODO: Add docstring here
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
    
    pc: RTCPeerConnection = None
    state: int = 0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    
    async def new_pc_connection(self, client_desc: dict[str, str]):
        if self.state >= 0:
            try:
                self.state = -1
                await self.close_pc_connection()
                offer = RTCSessionDescription(**client_desc)
                self.pc = RTCPeerConnection()
                pcs.add(self.pc)
                
                @self.pc.on("connectionstatechange")    
                async def on_connectionstatechange():
                    logger.info("Connection state is %s", self.pc.connectionState)
                    if self.pc.connectionState == "failed":
                        await self.close_pc_connection()
                        self.state = 2
                                
                @self.pc.on("track")
                def on_track(track):
                    logger.info("Track %s received", track.kind)
                    if track.kind == "video":
                        self.pc.addTrack(relay.subscribe(track))
                        
                # handle offer
                await self.pc.setRemoteDescription(offer)
                # send answer
                answer = await self.pc.createAnswer()
                await self.pc.setLocalDescription(answer)
                logger.debug(f"send answer: {answer} to client.")
                self.server_desc = answer
                self.state = 1
            except Exception as e:
                logger.error(e)
                self.state = 2
    
    
    async def close_pc_connection(self):
        if self.pc:
            await self.pc.close()
            pcs.remove(self.pc)
            self.pc = None
        
    
    @observe("client_desc")
    def on_client_desc_change(self, change):
        logger.debug(f'receive client_desc change from {change.old} to {change.new}')
        loop.call_soon(self.new_pc_connection, change.new)