from typing import Protocol


class ToolClass(Protocol):
    def __call__(self):
        pass
