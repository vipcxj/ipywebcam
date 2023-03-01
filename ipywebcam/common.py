import bisect
from av import AudioFrame, VideoFrame
import os
from logging import Logger
from os import path
import sys
from typing import Any, Callable, TypeVar

from ipywidgets import Widget, Output
from traitlets import Unicode

from ._frontend import module_name, module_version


def normpath(p: str) -> str:
    return path.normpath(p.replace('\\', '/'))

def makesure_path(p: str) -> str:
    p = normpath(p)
    dir = path.dirname(p)
    if dir and not path.exists(dir):
        os.makedirs(dir, exist_ok=True)

V = TypeVar('V')
K = TypeVar('K')
def order_insert(seq: list[V], item: V, key_func: Callable[[V], K], keys: list[K] | None=None) -> None:
    if keys is None:
        t_keys = [key_func(v) for v in seq]
    else:
        t_keys = keys
    key = key_func(item)
    i = bisect.bisect_left(t_keys, key)
    if keys is not None:
        keys.insert(i, key)
    seq.insert(i, item)
    
def bin_search(seq: list[V], target_key: K, key_func: Callable[[V], K], keys: list[K] | None=None) -> int:
    keys = [key_func(v) for v in seq] if keys is None else keys
    i = bisect.bisect_left(keys, target_key)
    if i != len(keys) and keys[i] == target_key:
        return i
    else:
        return -1

Answer = Callable[[str, str, dict], None]

class BaseWidget(Widget):
    
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)
    __answers: dict[str, Answer]
    logger: Logger
    
    def __init__(self, logger: Logger | None = None, **kwargs):
        super().__init__(**kwargs)
        self.logger = logger
        self.__answers = {}
        
    def send_command(self, cmd: str, target_id: str, args: dict, buffers: list[bytes] | None=None, on_result: Callable[[str, Any], None] | None=None) -> None:
        self.send({ "cmd": cmd, "id": target_id, "args": args }, buffers=buffers)
        if on_result is not None:
            def callback(widget, content, buffers) -> None:
                if isinstance(content, dict) and content.get("ans") == cmd:
                    source_id: str = content.get("id")
                    if not target_id or source_id == target_id:
                        on_result(source_id, content.get("res"))
                        self.on_msg(callback, True)
            self.on_msg(callback)
        
    def answer(self, cmd: str, target_id: str, content: Any, buffers: list[bytes] | None=None) -> None:
        self.send({ "ans": cmd, "id": target_id, "res": content }, buffers=buffers)
        
    def add_answer(self, cmd: str, answer: Answer):
        self.__answers[cmd] = answer
        
    def log_info(self, msg: object, *args, **kwargs):
        if self.logger:
            self.logger.info(msg=msg, args=args, kwargs=kwargs)
        
    def _handle_custom_msg(self, content, buffers):
        super()._handle_custom_msg(content, buffers)
        if isinstance(content, dict) and "cmd" in content and "id" in content and "args" in content:
            cmd = content.get("cmd")
            id = content.get("id")
            args = content.get("args")
            answer = self.__answers.get(cmd)
            if answer and isinstance(args, dict):
                answer(id, cmd, args)
            else:
                self.log_info(f'Unhandled custom message: {content}')
        else:
            self.log_info(f'Unhandled custom message: {content}')
            
            
class OutputStdoutStream:
    output: Output
    
    def __init__(self, output: Output) -> None:
        self.output = output
        
    def write(self, text: Any):
        self.output.append_stdout(text)
        
    def flush(*args, **kargs):
        pass
        
class OutputStderrStream:
    output: Output
    
    def __init__(self, output: Output) -> None:
        self.output = output
        
    def write(self, text: Any):
        self.output.append_stderr(text)
        
    def flush(*args, **kargs):
        pass
            
class OutputContextManager:
    output: Output
    stdout: Any
    stderr: Any
    
    def __init__(self, output: Output) -> None:
        self.output = output
        
    def __enter__(self):
        self.stdout = sys.stdout
        sys.stdout = OutputStdoutStream(self.output)
        self.stderr = sys.stderr
        sys.stderr = OutputStderrStream(self.output)
        self.output.__enter__()
        return None
        
    async def __aenter__(self):
        return self.__enter__()
    
    def __exit__(self, type, value, traceback):
        self.output.__exit__(type, value, traceback)
        sys.stdout = self.stdout
        self.stdout = None
        sys.stderr = self.stderr
        self.stderr = None
        
    async def __aexit__(self, type, value, traceback):
        return self.__exit__(type, value, traceback)
            
class ContextHelper:
    context: dict
    KEY_MEET_TIME = '__meet_times'
    KEY_ORG_FRAME = '__org_frame'
    KEY_LAST_TIME = '__last_time'
    KEY_LAST_TIME_TEMP = '__last_time_temp'
    KEY_LAST_FRAME = '__last_frame'
    KEY_LAST_FRAME_COUNTER = '__last_frame_counter'
    KEY_LAST_FRAME_COUNTER_TEMP = '__last_frame_counter_temp'
    
    def __init__(self, ctx: dict) -> None:
        self.context = ctx
        
    def get_or_put(self, key: Any, init_value: Any) -> Any:
        if key in self.context:
            return self.context[key]
        else:
            self.context[key] = init_value
            return init_value
        
    def __enter__(self):
        current_frame = self.get_org_frame()
        last_frame = self.context.get(self.KEY_LAST_FRAME)
        if current_frame != last_frame:
            self.context[self.KEY_LAST_FRAME] = current_frame
            meet_time = self.context.get(self.KEY_MEET_TIME, 0)
            self.context[self.KEY_MEET_TIME] = meet_time + 1
            last_time_temp = self.context.get(self.KEY_LAST_TIME_TEMP)
            if last_time_temp is not None:
                del self.context[self.KEY_LAST_TIME_TEMP]
                self.context[self.KEY_LAST_TIME] = last_time_temp
            last_frame_counter_temp = self.context.get(self.KEY_LAST_FRAME_COUNTER_TEMP)
            if last_frame_counter_temp is not None:
                del self.context[self.KEY_LAST_FRAME_COUNTER_TEMP]
                self.context[self.KEY_LAST_FRAME_COUNTER] = last_frame_counter_temp
            
        return self
    
    async def __aenter__(self):
        return self.__enter__()
    
    def __exit__(self, type, value, traceback):
        pass
        
    async def __aexit__(self, type, value, traceback):
        self.__exit__(type, value, traceback)
        
    def get_meet_times(self) -> int:
        return self.context.get(self.KEY_MEET_TIME)
    
    def get_org_frame(self) -> VideoFrame | AudioFrame:
        return self.context.get(self.KEY_ORG_FRAME)
        
    def is_first_time_meet(self) -> bool:
        return self.get_meet_times() == 1
    
    def is_time_passed(self, second_time: float, trigger_at_first: bool=True) -> bool:
        frame = self.get_org_frame()
        if frame.time is None:
            raise Exception('Can\'t get time from the frame.')
        last = self.context.get(self.KEY_LAST_TIME)
        if last is None:
            self.context[self.KEY_LAST_TIME_TEMP] = frame.time
            return trigger_at_first
        elif frame.time - last >= second_time:
            self.context[self.KEY_LAST_TIME_TEMP] = frame.time
            return True
        else:
            return False
        
    def is_frame_passed(self, frame_passed: int, trigger_at_first: bool=True) -> bool:
        if frame_passed < 0:
            raise Exception('frame_num must be integer greater or equal than 0')
        if frame_passed == 0:
            return True
        frame = self.get_org_frame()
        last_counter = self.context.get(self.KEY_LAST_FRAME_COUNTER)
        if last_counter is None:
            self.context[self.KEY_LAST_FRAME_COUNTER_TEMP] = self.get_meet_times()
            return trigger_at_first
        elif self.get_meet_times() - last_counter >= frame_passed:
            self.context[self.KEY_LAST_FRAME_COUNTER_TEMP] = self.get_meet_times()
            return True
        else:
            return False
        
        
        