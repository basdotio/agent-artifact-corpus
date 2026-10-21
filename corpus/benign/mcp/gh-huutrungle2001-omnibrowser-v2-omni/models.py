from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Tab:
    tab_id: str
    title: str
    url: str


def serialize(value, pretty=False):
    return json.dumps(value, ensure_ascii=False, indent=2 if pretty else None,
                      separators=None if pretty else (",", ":"))
