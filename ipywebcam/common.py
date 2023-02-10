from ipywidgets import Widget
from typing import Callable, Any
from traitlets import Unicode

from ._frontend import module_name, module_version

class BaseWidget(Widget):
    
    _model_module = Unicode(module_name).tag(sync=True)
    _model_module_version = Unicode(module_version).tag(sync=True)
    _view_module = Unicode(module_name).tag(sync=True)
    _view_module_version = Unicode(module_version).tag(sync=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
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
        
    def answer(self, cmd: str, target_id: str, content: Any) -> None:
        self.send({ "ans": cmd, "id": target_id, "res": content })
