"""Turn a UI-state payload into a flat :class:`Screen`.

Two sources share one model:

- the Android Portal ``state_full`` payload (``a11y_tree`` / ``phone_state`` / ``device_context``),
  also what mobilerun-core returns for Android over adb, Portal HTTP and cloud;
- other trees (iOS via mobilerun-ios / ios-portal) whose nodes use different field names and
  ``{x, y, width, height}`` frames. Field aliases follow mobilerun-core's.
"""

from __future__ import annotations

from typing import Any

from ..models import Bounds, Element, PhoneState, Screen

DEFAULT_SIZE = (720, 1280)

TEXT_FIELDS = ("text", "value", "label", "title")
DESC_FIELDS = ("contentDescription", "content_description", "accessibilityLabel", "label")
RID_FIELDS = ("resourceId", "resource_id", "accessibilityIdentifier", "identifier")
CLASS_FIELDS = ("className", "class_name", "elementType", "type", "role")
BOUNDS_FIELDS = ("boundsInScreen", "bounds", "bounds_in_screen", "rect", "frame")
CHILD_FIELDS = ("children", "nodes", "subviews")
# XCUIElement types that are interactive on iOS (names as ios-portal / mobilerun-ios print them)
IOS_TAPPABLE = {
    "button",
    "cell",
    "link",
    "tab",
    "menuitem",
    "switch",
    "toggle",
    "segmentedcontrol",
    "slider",
    "stepper",
    "picker",
    "pickerwheel",
    "key",
    "icon",
    "image",
    "checkbox",
    "radiobutton",
    "textfield",
    "securetextfield",
    "searchfield",
    "textview",
}
IOS_EDITABLE = {"textfield", "securetextfield", "searchfield", "textview"}
IOS_TOGGLE = {"switch", "toggle", "checkbox", "radiobutton"}
IOS_SCROLL = {"scrollview", "table", "collectionview", "webview"}


def _bounds(raw: dict[str, Any] | None) -> Bounds:
    raw = raw or {}
    return Bounds(
        int(raw.get("left", 0)),
        int(raw.get("top", 0)),
        int(raw.get("right", 0)),
        int(raw.get("bottom", 0)),
    )


def _flatten(node: dict[str, Any], depth: int, parent: int, out: list[Element]) -> None:
    index = len(out)
    out.append(
        Element(
            index=index,
            depth=depth,
            parent=parent,
            class_name=str(node.get("className", "")).rsplit(".", 1)[-1],
            resource_id=str(node.get("resourceId", "")),
            package=str(node.get("packageName", "")),
            text=str(node.get("text") or ""),
            description=str(node.get("contentDescription") or ""),
            hint=str(node.get("hint") or ""),
            state_description=str(node.get("stateDescription") or ""),
            bounds=_bounds(node.get("boundsInScreen")),
            clickable=bool(node.get("isClickable")),
            long_clickable=bool(node.get("isLongClickable")),
            focusable=bool(node.get("isFocusable")),
            focused=bool(node.get("isFocused")),
            editable=bool(node.get("isEditable")),
            password=bool(node.get("isPassword")),
            scrollable=bool(node.get("isScrollable")),
            checkable=bool(node.get("isCheckable")),
            checked=bool(node.get("isChecked")),
            selected=bool(node.get("isSelected")),
            enabled=bool(node.get("isEnabled", True)),
            visible=bool(node.get("isVisibleToUser", True)),
            input_type=int(node.get("inputType") or 0),
        )
    )
    for child in node.get("children") or []:
        _flatten(child, depth + 1, index, out)


def parse_screen(state: dict[str, Any]) -> Screen:
    """Build a :class:`Screen` from the ``state_full`` dict (``a11y_tree`` + ``phone_state``)."""
    phone = state.get("phone_state") or {}
    focused = phone.get("focusedElement") or {}
    ctx = (state.get("device_context") or {}).get("screen_bounds") or {}
    width = int(ctx.get("width") or DEFAULT_SIZE[0])
    height = int(ctx.get("height") or DEFAULT_SIZE[1])
    elements: list[Element] = []
    tree = state.get("a11y_tree")
    if isinstance(tree, dict):
        _flatten(tree, 0, -1, elements)
    return Screen(
        phone=PhoneState(
            package=str(phone.get("packageName", "")),
            app=str(phone.get("currentApp", "")),
            activity=str(phone.get("activityName", "")),
            keyboard_visible=bool(phone.get("keyboardVisible")),
            focused_editable=bool(phone.get("isEditable")) or bool(focused.get("text")),
        ),
        width=width,
        height=height,
        elements=tuple(elements),
    )


# ---- generic trees ------------------------------------------------------------------------


def _field(node: dict[str, Any], names: tuple[str, ...]) -> str:
    for name in names:
        value = node.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _flag(node: dict[str, Any], *names: str, default: bool = False) -> bool:
    for name in names:
        if name in node:
            return bool(node[name])
    return default


def generic_bounds(raw: Any) -> Bounds:
    """``{left,top,right,bottom}``, ``{x,y,width,height}``, ``[l,t,r,b]`` or ``"l,t,r,b"``."""
    if isinstance(raw, str):
        parts = [p for p in raw.replace("[", ",").replace("]", ",").split(",") if p.strip()]
        raw = [float(p) for p in parts[:4]] if len(parts) >= 4 else None
    if isinstance(raw, (list, tuple)) and len(raw) >= 4:
        left, top, right, bottom = (int(float(v)) for v in raw[:4])
        return Bounds(left, top, right, bottom)
    if isinstance(raw, dict):
        if "width" in raw and "x" in raw:
            x, y = int(float(raw["x"])), int(float(raw["y"]))
            return Bounds(x, y, x + int(float(raw["width"])), y + int(float(raw["height"])))
        if "left" in raw:
            return _bounds(raw)
    return Bounds(0, 0, 0, 0)


def _generic_flatten(node: dict[str, Any], depth: int, parent: int, out: list[Element]) -> None:
    kind = _field(node, CLASS_FIELDS).rsplit(".", 1)[-1]
    key = kind.lower().replace("xcuielementtype", "")
    bounds = generic_bounds(next((node[f] for f in BOUNDS_FIELDS if node.get(f)), None))
    index = len(out)
    out.append(
        Element(
            index=index,
            depth=depth,
            parent=parent,
            class_name=kind,
            resource_id=_field(node, RID_FIELDS),
            package=_field(node, ("packageName", "bundleId", "bundle_id")),
            text=_field(node, TEXT_FIELDS),
            description=_field(node, DESC_FIELDS),
            hint=_field(node, ("hint", "placeholderValue", "placeholder")),
            state_description="",
            bounds=bounds,
            clickable=_flag(
                node, "isClickable", "clickable", "hittable", default=key in IOS_TAPPABLE
            ),
            long_clickable=_flag(node, "isLongClickable", "longClickable"),
            focusable=_flag(node, "isFocusable", "focusable"),
            focused=_flag(node, "isFocused", "focused", "hasFocus"),
            editable=_flag(node, "isEditable", "editable", default=key in IOS_EDITABLE),
            password=_flag(node, "isPassword", "password", default=key == "securetextfield"),
            scrollable=_flag(node, "isScrollable", "scrollable", default=key in IOS_SCROLL),
            checkable=_flag(node, "isCheckable", "checkable", default=key in IOS_TOGGLE),
            checked=_flag(node, "isChecked", "checked", "selected")
            or str(node.get("value", "")).lower() in ("1", "on", "true"),
            selected=_flag(node, "isSelected", "selected"),
            enabled=_flag(node, "isEnabled", "enabled", default=True),
            visible=_flag(node, "isVisibleToUser", "visible", "hittable", default=True),
        )
    )
    for field in CHILD_FIELDS:
        for child in node.get(field) or []:
            if isinstance(child, dict):
                _generic_flatten(child, depth + 1, index, out)


def parse_any_state(state: dict[str, Any], size: tuple[int, int] | None = None) -> Screen:
    """Portal payloads take the fast path; anything else is parsed through field aliases."""
    tree = state.get("a11y_tree")
    if isinstance(tree, dict) and "boundsInScreen" in tree:
        return parse_screen(state)
    root: Any = tree if tree is not None else state
    if isinstance(root, dict):
        for container in ("tree", "root", "nodes"):
            if isinstance(root.get(container), (list, dict)):
                root = root[container]
                break
    elements: list[Element] = []
    for node in root if isinstance(root, list) else [root]:
        if isinstance(node, dict):
            _generic_flatten(node, 0, -1, elements)
    phone = state.get("phone_state") or {}
    width, height = size or (0, 0)
    if not width and elements:
        width = max(e.bounds.right for e in elements)
        height = max(e.bounds.bottom for e in elements)
    package = str(phone.get("packageName") or phone.get("bundleId") or state.get("bundle_id") or "")
    return Screen(
        phone=PhoneState(
            package=package,
            app=str(phone.get("currentApp") or package),
            activity=str(phone.get("activityName") or ""),
            keyboard_visible=bool(phone.get("keyboardVisible")),
            focused_editable=bool(phone.get("isEditable")),
        ),
        width=width or DEFAULT_SIZE[0],
        height=height or DEFAULT_SIZE[1],
        elements=tuple(elements),
    )
