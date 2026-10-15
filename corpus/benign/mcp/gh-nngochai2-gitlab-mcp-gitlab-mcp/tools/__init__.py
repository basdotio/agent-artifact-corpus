from .issues import ISSUE_TOOLS, handle_issue_tool
from .merge_requests import MR_TOOLS, handle_mr_tool

ALL_TOOLS = ISSUE_TOOLS + MR_TOOLS

TOOL_HANDLERS: dict = {
    **{t.name: handle_issue_tool for t in ISSUE_TOOLS},
    **{t.name: handle_mr_tool for t in MR_TOOLS},
}

__all__ = ["ALL_TOOLS", "TOOL_HANDLERS"]
