import asyncio
import atexit
import httpx
from concurrent.futures import ThreadPoolExecutor

LOOP = asyncio.new_event_loop()
background = ThreadPoolExecutor().submit(LOOP.run_forever)

@atexit.register
def goodbye():
    LOOP.call_soon_threadsafe(LOOP.stop)
    

class OWTClient:
    host: str
    
    def __init__(self, host: str) -> None:
        self.host = host
    
    def url(self, path: str) -> str:
        return f'{self.host}/{path}'
    
    async def _create_token(self, username: str, role: str, room: str | None = None):
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(self.url('tokens'), json={ 'room': room or '', 'user': username, 'role': role})
        return r
    
    def create_token(self, username: str, role: str, room: str | None = None):
        res = asyncio.run_coroutine_threadsafe(self._create_token(username, role, room), LOOP)
        return res.result(30)