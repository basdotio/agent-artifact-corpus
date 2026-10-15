"""Wire shapes. Every tool returns one of these, and its output schema is built from it
(`server.schema()`, which also admits the error envelope)."""

from pydantic import BaseModel, ConfigDict, Field


class Bookmark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bookmark_id: str = Field(
        description=(
            "Handle for this bookmark. Pass it to get_bookmark, update_bookmark, "
            "archive_bookmark, or delete_bookmark."
        )
    )
    url: str = Field(description="The saved URL as given, with surrounding whitespace removed.")
    title: str | None = Field(description="Display title, or null when there is none.")
    tags: list[str] = Field(description="Lower-case tags, deduplicated, in the order given.")
    archived: bool = Field(description="True once archive_bookmark has been called on it.")
    created_at: str = Field(description="When it was saved, ISO 8601 in UTC.")
    updated_at: str = Field(description="When it last changed, ISO 8601 in UTC.")


class BookmarkPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[Bookmark] = Field(description="Bookmarks, newest first.")
    next_cursor: str | None = Field(
        description=(
            "Position of the next page, to pass back as cursor with the same filters. "
            "Null on the last page."
        )
    )
    next_step: str = Field(description="What to do to see more, in words.")


class Deleted(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bookmark_id: str = Field(description="The handle that was deleted. It no longer resolves.")
    deleted: bool = Field(description="Always true.")
