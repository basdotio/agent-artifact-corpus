"""Pydantic input schemas for every qloo-mcp tool."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

EntityType = Literal[
    "urn:entity:artist",
    "urn:entity:book",
    "urn:entity:brand",
    "urn:entity:destination",
    "urn:entity:movie",
    "urn:entity:person",
    "urn:entity:place",
    "urn:entity:podcast",
    "urn:entity:tv_show",
    "urn:entity:video_game",
]
AgeBucket = Literal[
    "35_and_younger",
    "36_to_55",
    "55_and_older",
    "24_and_younger",
    "25_to_29",
    "30_to_34",
    "35_to_44",
    "45_to_54",
]
Gender = Literal["male", "female"]


class SearchEntitiesInput(BaseModel):
    query: Annotated[str, Field(min_length=1, max_length=200, description="Name to search for")]
    types: list[EntityType] = Field(default_factory=list, description="Entity type URNs to search within")
    take: Annotated[int, Field(ge=1, le=50)] = 10
    page: Annotated[int, Field(ge=1, le=100)] = 1
    location: str | None = Field(default=None, description="lat,lon pair or WKT geometry (filter.location)")
    radius_miles: Annotated[float, Field(ge=0, le=100)] | None = Field(
        default=None, description="Max distance in miles from location (filter.radius)"
    )


class SearchTagsInput(BaseModel):
    query: Annotated[str, Field(min_length=1, max_length=200, description="Partial tag name")]
    tag_types: list[str] = Field(default_factory=list, description="Tag type URNs (filter.tag.types)")
    parent_types: list[EntityType] = Field(default_factory=list, description="Parent entity types (filter.parents.types)")
    take: Annotated[int, Field(ge=1, le=50)] = 10
    page: Annotated[int, Field(ge=1, le=100)] = 1


class ListAudiencesInput(BaseModel):
    audience_types: list[str] = Field(
        default_factory=list, description="Audience type URNs, e.g. urn:audience:hobbies_and_interests"
    )
    take: Annotated[int, Field(ge=1, le=50)] = 20
    page: Annotated[int, Field(ge=1, le=100)] = 1


class GetInsightsInput(BaseModel):
    entity_type: EntityType = Field(description="What to recommend (filter.type)")
    entity_ids: list[str] = Field(default_factory=list, description="Seed entity IDs (signal.interests.entities)")
    tag_ids: list[str] = Field(default_factory=list, description="Seed tag IDs (signal.interests.tags)")
    audience_ids: list[str] = Field(default_factory=list, description="Audience IDs (signal.demographics.audiences)")
    age: AgeBucket | None = Field(default=None, description="signal.demographics.age")
    gender: Gender | None = Field(default=None, description="signal.demographics.gender")
    signal_location: str | None = Field(default=None, description="Locality name that biases results (signal.location.query)")
    filter_location: str | None = Field(default=None, description="Locality name that restricts results (filter.location.query)")
    filter_tag_ids: list[str] = Field(default_factory=list, description="Only return entities with these tags (filter.tags)")
    popularity_min: Annotated[float, Field(ge=0, le=1)] | None = Field(default=None, description="filter.popularity.min")
    explain: bool = Field(default=False, description="Include explainability (feature.explainability)")
    take: Annotated[int, Field(ge=1, le=50)] = 10
    page: Annotated[int, Field(ge=1, le=100)] = 1


class GetDemographicsInput(BaseModel):
    entity_ids: list[str] = Field(default_factory=list)
    tag_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _needs_signal(self) -> "GetDemographicsInput":
        if not self.entity_ids and not self.tag_ids:
            raise ValueError("provide at least one of entity_ids or tag_ids")
        return self


class GetTasteAnalysisInput(BaseModel):
    entity_ids: list[str] = Field(default_factory=list)
    tag_ids: list[str] = Field(default_factory=list)
    audience_ids: list[str] = Field(default_factory=list)
    location: str | None = Field(default=None, description="signal.location.query")
    tag_types: list[str] = Field(default_factory=list, description="filter.tag.types")
    parent_types: list[EntityType] = Field(default_factory=list, description="filter.parents.types")
    take: Annotated[int, Field(ge=1, le=50)] = 15

    @model_validator(mode="after")
    def _needs_signal(self) -> "GetTasteAnalysisInput":
        if not (
            self.entity_ids
            or self.tag_ids
            or self.audience_ids
            or self.location
            or self.tag_types
            or self.parent_types
        ):
            raise ValueError(
                "provide at least one of entity_ids, tag_ids, audience_ids, location, tag_types, parent_types"
            )
        return self


class TasteMatchInput(BaseModel):
    work_title: Annotated[str, Field(min_length=1, max_length=200)]
    work_kind: Literal["artwork", "song"] = "artwork"
    description: Annotated[str, Field(min_length=1, max_length=4000)]
    influences: list[Annotated[str, Field(min_length=1, max_length=200)]] = Field(
        default_factory=list, max_length=10, description="Artists, films, books, brands the work sits next to"
    )
    keywords: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=10, description="Genre or style words"
    )
    location: str | None = Field(default=None, description="City to find places and local taste in")
    take: Annotated[int, Field(ge=1, le=20)] = 8
