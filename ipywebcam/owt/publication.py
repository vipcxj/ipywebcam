from typing import Callable

from .common import EventDispatcher


class Publication(EventDispatcher):
    id: str
    stop: Callable[[], None]