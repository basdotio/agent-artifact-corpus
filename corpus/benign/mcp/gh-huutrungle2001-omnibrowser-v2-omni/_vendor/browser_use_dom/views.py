"""Minimal local models for the vendored reader (not the upstream framework)."""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class NodeType(IntEnum):
    ELEMENT_NODE = 1
    TEXT_NODE = 3
    DOCUMENT_NODE = 9
    DOCUMENT_FRAGMENT_NODE = 11


@dataclass
class DOMRect:
    x: float
    y: float
    width: float
    height: float


@dataclass
class EnhancedSnapshotNode:
    is_clickable: bool = False
    cursor_style: str | None = None
    bounds: DOMRect | None = None
    computed_styles: dict[str, str] = field(default_factory=dict)
    paint_order: int | None = None


@dataclass
class EnhancedAXProperty:
    name: str
    value: Any


@dataclass
class EnhancedAXNode:
    role: str = ""
    name: str = ""
    properties: list[EnhancedAXProperty] = field(default_factory=list)


@dataclass(eq=False)
class EnhancedDOMTreeNode:
    backend_node_id: int
    node_type: int
    node_name: str
    attributes: dict[str, str] = field(default_factory=dict)
    node_value: str = ""
    children: list = field(default_factory=list)
    parent_node: Any = None
    snapshot_node: EnhancedSnapshotNode | None = None
    ax_node: EnhancedAXNode | None = None
    has_js_click_listener: bool = False
    session_id: str = "main"
    frame_id: str | None = None
    editable_ancestor: bool = False

    @property
    def tag_name(self):
        return self.node_name.lower()

    @property
    def children_and_shadow_roots(self):
        return self.children


@dataclass
class SimplifiedNode:
    original_node: EnhancedDOMTreeNode
    children: list = field(default_factory=list)
    ignored_by_paint_order: bool = False
