from ipywidgets import Widget
from typing import Callable, Any
from traitlets import Unicode
from logging import Logger

from ._frontend import module_name, module_version

Answer = Callable[[str, str, dict], None];

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