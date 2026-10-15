# Mostly copied from smolagents examples

import logging

from py_conf_mcp.tools.typing import ToolClass


LOGGER = logging.getLogger(__name__)


class StaticContentTool(ToolClass):
    def __init__(
        self,
        content: str
    ):
        self.content = content

    def __call__(self):
        return self.content
