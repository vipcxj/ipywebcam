import asyncio
import base64
import json
import logging
import time
from typing import Any

import socketio

from .common import EventDispatcher, MessageEvent, OwtEvent

logger = logging.getLogger("ipywebcam [SioSignaling]")

class SioSignaling(EventDispatcher):
    
    io: socketio.AsyncClient | None
    _loggedIn: bool = False
    _reconnectTimes: int = 0
    _reconnectionTicket: str | None = None
    _refreshReconnectionTicket: asyncio.Future | None = None
    reconnectionAttempts: int
    
    def __init__(self) -> None:
        self.io = None
        
    async def connect(self, host: str, login_info):
        if self.io is not None:
            raise RuntimeError('Portal has been connected.')
        io = self.io = socketio.AsyncClient()
        await io.connect(host)
        def message_handler(data: Any):
            co = self.dispatchEvent(MessageEvent(
                'data',
                message={
                    'notification': notification,
                    'data': data,
                }
            ))
            asyncio.ensure_future(co)
        for notification in ['participant', 'text', 'stream', 'progress']:
            io.on(notification, message_handler)
            
        def on_drop(data: Any):
            asyncio.create_task(self.disconnect(False))
        io.on('drop', on_drop)
        
        def on_disconnect():
            self._loggedIn = False
            self._clearReconnectionTask()
            co = self.dispatchEvent(OwtEvent('disconnect'))
            asyncio.ensure_future(co)
        io.on('disconnect', on_disconnect)
            
        ticket = await self.send('login', login_info)
        self._loggedIn = True
        self._onReconnectionTicket(ticket)
        
        async def on_connect():
            try:
                ticket = await self.send('relogin', self._reconnectionTicket)
                self._loggedIn = True
                self._onReconnectionTicket(ticket)
            except Exception:
                await self.disconnect(False)

        io.on('connect', lambda: asyncio.ensure_future(on_connect()))
    
    async def send(self, requestName: str, requestData: Any):
        if self.io is None:
            raise RuntimeError('Portal is not connected.')
        future = asyncio.Future()
        def resp(status: str, data: Any):
            if status == 'ok' or status == 'success':
                future.set_result(data)
            else:
                future.set_exception(RuntimeError(data))
        await self.io.emit(requestName, requestData, resp)
        return await future
        
    
    async def disconnect(self, logout: bool = True):
        if self.io is None:
            raise RuntimeError('Portal is not connected.')
        if logout:
            await self.io.emit('logout')
        await self.io.disconnect()
        self.io = None
        
        
    def _onReconnectionTicket(self, ticketString: str):
        self._reconnectionTicket = ticketString
        ticket = json.loads(base64.b64decode(ticketString))
        
        # Refresh ticket 1 min or 10 seconds before it expires.
        now = time.time() * 1000
        millisecondsInOneMinute = 60 * 1000
        millisecondsInTenSeconds = 10 * 1000
        if ticket.notAfter <= now - millisecondsInTenSeconds:
            logger.warning('Reconnection ticket expires too soon.')
            return
        
        refreshAfter = ticket.notAfter - now - millisecondsInOneMinute
        if refreshAfter < 0:
            refreshAfter = ticket.notAfter - now - millisecondsInTenSeconds
        
        self._clearReconnectionTask()
        
        def refreshReconnectionTicket_resp(status: str, data: str):
            if status != 'ok':
                logger.warning('Failed to refresh reconnection ticket.')
            self._onReconnectionTicket(data)
        
        async def refreshReconnectionTicket():
            io = self.io
            if io is not None:
                await io.emit('refreshReconnectionTicket', refreshReconnectionTicket_resp)
                await asyncio.sleep(refreshAfter / 1000)
        self._refreshReconnectionTicket = asyncio.ensure_future(refreshReconnectionTicket())
    
    def _clearReconnectionTask(self):
        if self._refreshReconnectionTicket is not None:
            self._refreshReconnectionTicket.cancel()
        self._refreshReconnectionTicket = None
