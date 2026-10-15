from collections.abc import Callable
from typing import Any

from mcp.types import TextContent, Tool


class BaseTool(Tool):

    def _entrypoint(self, input:Any) -> TextContent | list[TextContent]:
        raise NotImplementedError("Entrypoint not implemented")
    
    def callback(self) -> Callable[..., Any]:
        return self._entrypoint


    
