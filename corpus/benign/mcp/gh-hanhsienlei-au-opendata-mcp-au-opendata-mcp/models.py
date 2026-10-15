from pydantic import BaseModel


class Sourced(BaseModel):
    """Attribution is structural: there is no result model without these fields."""

    dataset_url: str
    organisation: str
    licence: str
