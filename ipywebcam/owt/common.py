from typing import Callable, Any
import inspect
import asyncio

class ConferenceError(Exception):
    message: str
    
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = message

class OwtEvent:
    type: str
    
    def __init__(self, type: str) -> None:
        self.type = type
        
class ErrorEvent(OwtEvent):
    error: Exception
    
    def __init__(self, type: str, error: Exception) -> None:
        super().__init__(type)
        self.error = error
        
class MessageEvent(OwtEvent):
    
    def __init__(self, type: str, message: Any, origin: str | None = None, to: str | None = None) -> None:
        super().__init__(type)
        self.message = message
        self.origin = origin
        self.to = to

Listener = Callable[[OwtEvent], Any]

class EventDispatcher:
    
    listeners_map: dict[str, list[Listener]]
    
    def __init__(self) -> None:
        self.listeners_map = {}
    
    def addEventListener(self, eventType: str, listener: Listener) -> None:
        if eventType not in self.listeners_map:
            self.listeners_map[eventType] = []
        self.listeners_map[eventType].append(listener)
    
    def removeEventListener(self, eventType: str, listener: Listener) -> None:
        if eventType in self.listeners_map:
            listeners = self.listeners_map[eventType]
            listeners.remove(listener)
            if len(listeners) == 0:
                del self.listeners_map[eventType]
    
    def clearEventListener(self, eventType: str) -> None:
        if eventType in self.listeners_map:
            del self.listeners_map[eventType]
    
    async def dispatchEvent(self, event: OwtEvent):
        results = [listener(event) for listener in self.listeners_map.get(event.type, [])]
        coros = [result for result in results if inspect.isawaitable(result)]
        if len(coros) > 0:
            await asyncio.gather(*coros)
                
        