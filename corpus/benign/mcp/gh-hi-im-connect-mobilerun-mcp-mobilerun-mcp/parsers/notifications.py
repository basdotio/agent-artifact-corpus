"""Parse ``dumpsys notification --noredact`` into :class:`Notification` records."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

FLAG_ONGOING = 0x2
FLAG_NO_CLEAR = 0x20
FLAG_FOREGROUND_SERVICE = 0x40

_HEADER = re.compile(
    r"^ {4}NotificationRecord\(0x[0-9a-f]+: pkg=(?P<pkg>\S+) user=\S+ "
    r"id=(?P<id>-?\d+) tag=(?P<tag>\S+)"
)
_KEY = re.compile(r"^ {6}key=(.+)$")
_FLAGS = re.compile(r"^ {6}flags=0x([0-9a-f]+)")
_WHEN = re.compile(r"^\s+when=(\d+)")
_TICKER = re.compile(r"^\s+tickerText=(.*)$")
_ACTION = re.compile(r'^\s+\[(\d+)\] "(.*)" ->')
_EXTRA = re.compile(r"^\s+android\.(title|text|subText|bigText)=\w+ \((.*)\)$")
_IMPORTANCE = re.compile(r"^ {6}mImportance=(\w+)")


@dataclass(frozen=True)
class Notification:
    key: str
    package: str
    id: int
    tag: str | None
    title: str = ""
    text: str = ""
    sub_text: str = ""
    ticker: str = ""
    when_ms: int = 0
    flags: int = 0
    importance: str = ""
    actions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ongoing(self) -> bool:
        return bool(self.flags & (FLAG_ONGOING | FLAG_FOREGROUND_SERVICE))

    @property
    def clearable(self) -> bool:
        return not (self.flags & (FLAG_ONGOING | FLAG_NO_CLEAR))

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "package": self.package,
            "title": self.title,
            "text": self.text,
            "sub_text": self.sub_text,
            "when_ms": self.when_ms,
            "ongoing": self.ongoing,
            "clearable": self.clearable,
            "importance": self.importance,
            "actions": list(self.actions),
        }


def _list_section(dump: str) -> list[str]:
    lines = dump.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "Notification List:")
    except StopIteration:
        return []
    section: list[str] = []
    for ln in lines[start + 1 :]:
        if ln.strip() and len(ln) - len(ln.lstrip()) <= 2:
            break
        section.append(ln)
    return section


def parse_notifications(dump: str) -> list[Notification]:
    blocks: list[list[str]] = []
    for ln in _list_section(dump):
        if _HEADER.match(ln):
            blocks.append([ln])
        elif blocks:
            blocks[-1].append(ln)

    result: list[Notification] = []
    for block in blocks:
        head = _HEADER.match(block[0])
        assert head is not None
        fields: dict[str, str] = {}
        actions: list[str] = []
        flags = 0
        when = 0
        ticker = ""
        importance = ""
        key = ""
        for ln in block[1:]:
            if m := _KEY.match(ln):
                key = key or m.group(1)
            elif m := _FLAGS.match(ln):
                flags = int(m.group(1), 16)
            elif m := _WHEN.match(ln):
                when = int(m.group(1))
            elif m := _TICKER.match(ln):
                ticker = "" if m.group(1) == "null" else m.group(1)
            elif m := _ACTION.match(ln):
                actions.append(m.group(2))
            elif m := _EXTRA.match(ln):
                fields.setdefault(m.group(1), m.group(2))
            elif m := _IMPORTANCE.match(ln):
                importance = m.group(1)
        tag = None if head.group("tag") == "null" else head.group("tag")
        result.append(
            Notification(
                key=key,
                package=head.group("pkg"),
                id=int(head.group("id")),
                tag=tag,
                title=fields.get("title", ""),
                text=fields.get("bigText") or fields.get("text", ""),
                sub_text=fields.get("subText", ""),
                ticker=ticker,
                when_ms=when,
                flags=flags,
                importance=importance,
                actions=tuple(actions),
            )
        )
    return result
