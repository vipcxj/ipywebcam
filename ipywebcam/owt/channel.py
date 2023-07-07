from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCIceCandidate, RTCRtpTransceiver, MediaStreamTrack
from aiortc.events import RTCTrackEvent
import asyncio
from dataclasses import dataclass
import logging
from typing import Any
from .common import EventDispatcher, OwtEvent, ConferenceError, ErrorEvent
from .signaling import SioSignaling
from .subscription import Subscription
from .publication import Publication

logger = logging.getLogger("ipywebcam [OwtChannel]")

@dataclass
class Transceiver:
    type: str
    transceiver: RTCRtpTransceiver
    from_: str
    parameters: Any
    option: Any

@dataclass
class TransceiversWithId:
    id: str | None = None
    transceivers: list[Transceiver] = []

class OwtChannel(EventDispatcher):
    pc: RTCPeerConnection
    _signaling: SioSignaling
    _id: str | None
    _internalCount: int
    _ended: bool
    _subscriptions: dict[str, Subscription]
    _subscribeTransceivers: dict[str, TransceiversWithId]
    _subscribePromises: dict[str, asyncio.Future[Subscription]]
    _remoteMediaTracks: dict[str, MediaStreamTrack]
    _publications: dict[str, Publication]
    
    def __init__(self, signaling: SioSignaling) -> None:
        super().__init__()
        self._ended = False
        self._internalCount = 0
        self._signaling = signaling
        self._subscriptions = {}
        self._subscribeTransceivers = {}
        self._remoteMediaTracks = {}
        
        self._publications = {}
        self._createPeerConnection()
        
        
    def _onRemoteTrackAdded(self, event: RTCTrackEvent):
        logger.debug('Remote stream added.')
        for internalId, sub in self._subscribeTransceivers.items():
            if next((t for t in sub.transceivers if t.transceiver == event.transceiver), None):
                assert sub.id is not None
                if sub.id in self._subscriptions:
                    subscription = self._subscriptions[sub.id]
                    subscription.track = event.track
                    if internalId in self._subscribePromises:
                        self._subscribePromises[internalId].set_result(subscription)
                        del self._subscribePromises[internalId]

                else:
                    self._remoteMediaTracks[sub.id] = event.track
            return
        # This is not expected path. However, this is going to happen on Safari
        # because it does not support setting direction of transceiver.
        logger.warning('Received remote stream without subscription.')
        
    def _onIceConnectionStateChange(self):
        logger.debug(f'ICE connection state changed to {self.pc.iceConnectionState}')

        if self.pc.iceConnectionState == 'closed' or self.pc.iceConnectionState == 'failed':
            if self.pc.iceConnectionState == 'failed':
                asyncio.ensure_future(self._handleError('connection failed.'))
            else:
                # Fire ended event if publication or subscription exists.
                asyncio.ensure_future(self._fireEndedEventOnPublicationOrSubscription())
                
    def _onConnectionStateChange(self):
        if self.pc.connectionState == 'closed' or self.pc.connectionState == 'failed':
            if self.pc.connectionState == 'failed':
                asyncio.ensure_future(self._handleError('connection failed.'))
            else:
                # Fire ended event if publication or subscription exists.
                asyncio.ensure_future(self._fireEndedEventOnPublicationOrSubscription())
        
    def _createPeerConnection(self):
        if self.pc:
            logger.warning('A PeerConnection was created. Cannot create again for ' +
                'the same PeerConnectionChannel.')
            return

        self.pc = RTCPeerConnection()
        self.pc.on('track', self._onRemoteTrackAdded)
        self.pc.on('iceconnectionstatechange', self._onIceConnectionStateChange)
        self.pc.on('connectionstatechange', self._onConnectionStateChange)
        
    async def close(self):
        if self.pc and self.pc.signalingState != 'closed':
            await self.pc.close()
            
    async def _handleError(self, errorMessage: str):
        if self._ended:
            return
        error = ConferenceError(errorMessage)
        event = ErrorEvent('error', error=error)
        for publication in self._publications.values():
            await publication.dispatchEvent(event)
        for subscription in self._subscriptions.values():
            await subscription.dispatchEvent(event)
        await self._fireEndedEventOnPublicationOrSubscription()
        
            
    async def _fireEndedEventOnPublicationOrSubscription(self):
        if self._ended:
            return
        self._ended = True
        event = OwtEvent('ended')
        for publication in self._publications.values():
            await publication.dispatchEvent(event)
            publication.stop()
        for subscription in self._subscriptions.values():
            await subscription.dispatchEvent(event)
            subscription.stop()
        await self.dispatchEvent(event)
        await self.close()
            
    def _createInternalId(self):
        id = self._internalCount
        self._internalCount += 1
        return id
