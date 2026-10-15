from pydantic import BaseModel, Field


class CkanResource(BaseModel):
    id: str
    name: str | None = None
    format: str | None = None
    url: str | None = None
    size: int | None = None
    datastore_active: bool = False
    last_modified: str | None = None

    model_config = {"extra": "ignore"}


class CkanOrganization(BaseModel):
    name: str
    title: str | None = None
    package_count: int | None = None

    model_config = {"extra": "ignore"}


class CkanDataset(BaseModel):
    id: str
    name: str
    title: str | None = None
    notes: str | None = None
    license_title: str | None = None
    license_id: str | None = None
    metadata_modified: str | None = None
    organization: CkanOrganization | None = None
    resources: list[CkanResource] = Field(default_factory=list)

    model_config = {"extra": "ignore"}
