"""Immutable data models shared by parsers, perception and tools."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.right) // 2, (self.top + self.bottom) // 2

    def contains_point(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom

    def contains(self, other: Bounds) -> bool:
        return (
            self.left <= other.left
            and self.top <= other.top
            and self.right >= other.right
            and self.bottom >= other.bottom
        )

    def intersects(self, other: Bounds) -> bool:
        return not (
            self.right <= other.left
            or other.right <= self.left
            or self.bottom <= other.top
            or other.bottom <= self.top
        )

    def as_list(self) -> list[int]:
        return [self.left, self.top, self.right, self.bottom]


@dataclass(frozen=True)
class Element:
    """One accessibility node, flattened in depth-first order."""

    index: int
    depth: int
    parent: int
    class_name: str
    resource_id: str
    package: str
    text: str
    description: str
    hint: str
    state_description: str
    bounds: Bounds
    clickable: bool = False
    long_clickable: bool = False
    focusable: bool = False
    focused: bool = False
    editable: bool = False
    password: bool = False
    scrollable: bool = False
    checkable: bool = False
    checked: bool = False
    selected: bool = False
    enabled: bool = True
    visible: bool = True
    input_type: int = 0

    @property
    def short_id(self) -> str:
        return self.resource_id.rsplit("/", 1)[-1] if self.resource_id else ""

    @property
    def label(self) -> str:
        """The node's own human-readable label."""
        return self.text or self.description or self.hint or self.state_description

    @property
    def interactive(self) -> bool:
        return self.clickable or self.long_clickable or self.editable or self.checkable


@dataclass(frozen=True)
class PhoneState:
    package: str
    app: str
    activity: str
    keyboard_visible: bool
    focused_editable: bool


@dataclass(frozen=True)
class Screen:
    phone: PhoneState
    width: int
    height: int
    elements: tuple[Element, ...] = field(default_factory=tuple)

    @property
    def bounds(self) -> Bounds:
        return Bounds(0, 0, self.width, self.height)


@dataclass(frozen=True)
class Mark:
    """A numbered, targetable item on screen (set-of-marks)."""

    id: int
    kind: str  # button | input | toggle | text | image | scroll | icon
    label: str
    bounds: Bounds
    element_index: int
    source: str = "a11y"  # a11y | ocr | vision
    checked: bool | None = None
    password: bool = False
    scrollable: bool = False
    confidence: float = 1.0  # detector score for source="vision"

    @property
    def center(self) -> tuple[int, int]:
        return self.bounds.center

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "bounds": self.bounds.as_list(),
            "center": list(self.center),
        }
        if self.source != "a11y":
            out["source"] = self.source
        if self.checked is not None:
            out["checked"] = self.checked
        if self.password:
            out["password"] = True
        return out
