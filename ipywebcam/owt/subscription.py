from typing import Callable

from aiortc import MediaStreamTrack

from .common import EventDispatcher


class Subscription(EventDispatcher):
    id: str
    track: MediaStreamTrack
    stop: Callable[[], None]

    