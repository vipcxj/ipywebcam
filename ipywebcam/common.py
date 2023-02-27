import bisect
import os
from logging import Logger
from os import path
from typing import Any, Callable, TypeVar

from ipywidgets import Widget
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