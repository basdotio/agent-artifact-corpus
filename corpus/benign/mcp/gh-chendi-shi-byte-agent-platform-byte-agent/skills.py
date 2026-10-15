"""Load an explicitly selected, operator-owned Markdown workflow as instructions."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    sha256: str

    def prompt(self, system):
        return system + f"\n\nOperator-selected skill {self.name}:\n" + self.instructions


def load_skill(path):
    body = Path(path).read_bytes()
    if len(body) > 16000:
        raise ValueError("skill exceeds 16KB limit")
    text = body.decode("utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("skill requires name/description frontmatter")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError("unterminated skill frontmatter")
    fields = dict(line.split(":", 1) for line in parts[1].strip().splitlines() if ":" in line)
    name, description = fields.get("name", "").strip(), fields.get("description", "").strip()
    instructions = parts[2].strip()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name) or not description or not instructions:
        raise ValueError("invalid skill metadata or empty instructions")
    return Skill(name, description, instructions, hashlib.sha256(body).hexdigest())
