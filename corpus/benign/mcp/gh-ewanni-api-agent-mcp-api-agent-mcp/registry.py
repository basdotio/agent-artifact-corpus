import json
import uuid
from typing import Any

from aiosqlite import Connection
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentProfile(BaseModel):
    """Reusable role, prompt, and model settings (a "gem")."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="general", min_length=1, max_length=100)
    system_prompt: str = Field(min_length=1)
    model: str | None = None
    tags: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        return list(dict.fromkeys(tag.strip().casefold() for tag in tags if tag.strip()))


def _row_to_profile(row: Any) -> AgentProfile:
    return AgentProfile(
        id=row["id"],
        name=row["name"],
        role=row["role"],
        system_prompt=row["system_prompt"],
        model=row["model"],
        tags=json.loads(row["tags"]),
        config=json.loads(row["config"]),
    )


async def create_profile(db: Connection, profile: AgentProfile) -> AgentProfile:
    await db.execute(
        """INSERT INTO profiles (id, name, role, system_prompt, model, tags, config)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            profile.id,
            profile.name,
            profile.role,
            profile.system_prompt,
            profile.model,
            json.dumps(profile.tags, ensure_ascii=False),
            json.dumps(profile.config, ensure_ascii=False),
        ),
    )
    await db.commit()
    return profile


async def get_profile(db: Connection, name: str) -> AgentProfile | None:
    cur = await db.execute("SELECT * FROM profiles WHERE name = ? COLLATE NOCASE", (name,))
    row = await cur.fetchone()
    return _row_to_profile(row) if row else None


async def list_profiles(db: Connection) -> list[AgentProfile]:
    cur = await db.execute("SELECT * FROM profiles ORDER BY name COLLATE NOCASE")
    return [_row_to_profile(row) async for row in cur]


async def update_profile(db: Connection, profile: AgentProfile) -> bool:
    cur = await db.execute(
        """UPDATE profiles SET role = ?, system_prompt = ?, model = ?, tags = ?,
           config = ?, updated_at = datetime('now') WHERE id = ?""",
        (
            profile.role,
            profile.system_prompt,
            profile.model,
            json.dumps(profile.tags, ensure_ascii=False),
            json.dumps(profile.config, ensure_ascii=False),
            profile.id,
        ),
    )
    await db.commit()
    return cur.rowcount == 1
