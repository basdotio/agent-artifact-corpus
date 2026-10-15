from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Optional, List, Dict


class SearchBase(BaseModel):
    term: Optional[str] = None
    first: int = 0
    size: int = 50
    sort_attribute_name: Optional[str] = None
    sort_order: Optional[str] = None  # "asc" / "dsc"
    phrase_match: bool = True
    minimal: bool = False

    @field_validator("size")
    @classmethod
    def _cap_size(cls, v: int):
        return 1 if v < 1 else (500 if v > 500 else v)


class Rectangle(BaseModel):
    top_left_lat: float
    top_left_lon: float
    bottom_right_lat: float
    bottom_right_lon: float


class PointDistance(BaseModel):
    lat: float
    lon: float
    distance: float  # meters


class SearchByRect(BaseModel):
    term: Optional[str] = None
    first: int = 0
    size: int = 50
    phrase_match: bool = True
    prefecture_code: Optional[str] = None
    rectangle: Rectangle


class SearchByPoint(BaseModel):
    term: Optional[str] = None
    first: int = 0
    size: int = 50
    phrase_match: bool = True
    prefecture_code: Optional[str] = None
    point: PointDistance


# ==== GRAPHQL MODE ONLY ====
class SearchByAttr(SearchBase):
    # attributeFilter: { attributeName: "...", is: <value> }
    attribute_name: str            # example: "DPF:dataset_id" / "DPF:prefecture_code" / etc.
    attribute_value: Any           # value for 'is' (can be string / number). Operator is ALWAYS 'is'.


class GetDataParams(BaseModel):
    dataset_id: str = Field(..., alias="dataset_id")
    data_id: str = Field(..., alias="data_id")


# ===== Municipalities =====
class GetMunicipalitiesParams(BaseModel):
    pref_codes: Optional[List[str]] = None
    muni_codes: Optional[List[str]] = None
    fields: Optional[List[str]] = None
    # backward compat (single)
    pref_code: Optional[str] = None

    @model_validator(mode="after")
    def _normalize_codes(self):
        if self.pref_code and not self.pref_codes:
            self.pref_codes = [self.pref_code]
        if not self.pref_codes and not self.muni_codes:
            raise ValueError("Either pref_codes or muni_codes (or pref_code) must be provided.")
        return self


# --- getAllData ---
class GetAllDataInput(BaseModel):
    size: int = Field(1000, ge=1, le=1000, description="Max 1000 per request (MLIT limit)")
    term: Optional[str] = None
    phrase_match: Optional[bool] = None

    prefecture_code: Optional[str] = None
    municipality_code: Optional[str] = None
    address: Optional[str] = None
    catalog_id: Optional[str] = None
    dataset_id: Optional[str] = None

    location_rectangle_top_left_lat: Optional[float] = None
    location_rectangle_top_left_lon: Optional[float] = None
    location_rectangle_bottom_right_lat: Optional[float] = None
    location_rectangle_bottom_right_lon: Optional[float] = None

    max_batches: int = Field(20, ge=1, le=10000)
    include_metadata: bool = True


class GetAllDataItem(BaseModel):
    id: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =========================
# SUGGEST API
# =========================
class SuggestInput(BaseModel):
    term: str
    phrase_match: Optional[bool] = None

    prefecture_code: Optional[str] = None
    municipality_code: Optional[str] = None
    address: Optional[str] = None
    catalog_id: Optional[str] = None
    dataset_id: Optional[str] = None

    location_rectangle_top_left_lat: Optional[float] = None
    location_rectangle_top_left_lon: Optional[float] = None
    location_rectangle_bottom_right_lat: Optional[float] = None
    location_rectangle_bottom_right_lon: Optional[float] = None


class SuggestItem(BaseModel):
    name: str
    cnt: int


class SuggestResponse(BaseModel):
    total_number: Optional[int] = None
    suggestions: List[SuggestItem] = Field(default_factory=list)
    raw: Optional[Any] = None


# =========================
# COUNT DATA API
# =========================
class CountAttributeSliceSettingInput(BaseModel):
    attribute_name: str = Field(..., alias="attributeName")
    size: Optional[int] = Field(default=None, ge=1, le=50)
    sub_slice_setting: Optional["CountAttributeSliceSettingInput"] = Field(
        default=None,
        alias="subSliceSetting" 
    )


class CountSliceSettingInput(BaseModel):
    type_: Optional[str] = Field(default=None, alias="type")
    attribute_slice_setting: Optional[CountAttributeSliceSettingInput] = Field(
        default=None, 
        alias="attributeSliceSetting"
    )


class CountDataInput(BaseModel):
    term: Optional[str] = None
    phrase_match: Optional[bool] = None

    prefecture_code: Optional[str] = None
    municipality_code: Optional[str] = None
    address: Optional[str] = None
    catalog_id: Optional[str] = None
    dataset_id: Optional[str] = None

    location_rectangle_top_left_lat: Optional[float] = None
    location_rectangle_top_left_lon: Optional[float] = None
    location_rectangle_bottom_right_lat: Optional[float] = None
    location_rectangle_bottom_right_lon: Optional[float] = None

    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    location_distance: Optional[float] = None

    slice_setting: Optional[CountSliceSettingInput] = None


class CountSlice(BaseModel):
    attribute_name: Optional[str] = None
    attribute_value: Optional[Any] = None
    data_count: int
    slices: Optional[List["CountSlice"]] = None


class CountDataResponse(BaseModel):
    data_count: int
    slices: Optional[List[CountSlice]] = None
    raw: Optional[Any] = None


# =========================
# MESH API
# =========================
class MeshParams(BaseModel):
    dataset_id: str
    data_id: str
    mesh_id: str
    mesh_code: str


# =========================
# FILE DOWNLOAD URLs
# =========================
class FileRef(BaseModel):
    id: str
    original_path: str


class FileDownloadURLsInput(BaseModel):
    files: Optional[List[FileRef]] = None
    dataset_id: Optional[str] = None
    data_id: Optional[str] = None

    @model_validator(mode="after")
    def _check_inputs(self):
        have_files = bool(self.files)
        have_data_keys = bool(self.dataset_id and self.data_id)
        if not (have_files or have_data_keys):
            raise ValueError("Provide either files[] or dataset_id+data_id.")
        return self


class FileDownloadURLItem(BaseModel):
    ID: str
    URL: str


class FileDownloadURLsResponse(BaseModel):
    urls: List[FileDownloadURLItem]
    raw: Optional[Any] = None


# =========================
# ZIPFILE DOWNLOAD URL
# =========================
class ZipfileDownloadURLInput(BaseModel):
    files: Optional[List[FileRef]] = None
    dataset_id: Optional[str] = None
    data_id: Optional[str] = None

    @model_validator(mode="after")
    def _check_inputs(self):
        have_files = bool(self.files)
        have_data_keys = bool(self.dataset_id and self.data_id)
        if not (have_files or have_data_keys):
            raise ValueError("Provide either files[] or dataset_id+data_id.")
        return self


class ZipfileDownloadURLResponse(BaseModel):
    url: str
    raw: Optional[Any] = None


# =========================
# THUMBNAIL URLs
# =========================
class ThumbnailRef(BaseModel):
    id: str
    original_path: str


class ThumbnailURLsInput(BaseModel):
    thumbnails: Optional[List[ThumbnailRef]] = None
    dataset_id: Optional[str] = None
    data_id: Optional[str] = None

    @model_validator(mode="after")
    def _check_inputs(self):
        have_thumbs = bool(self.thumbnails)
        have_data_keys = bool(self.dataset_id and self.data_id)
        if not (have_thumbs or have_data_keys):
            raise ValueError("Provide either thumbnails[] or dataset_id+data_id.")
        return self


class ThumbnailURLItem(BaseModel):
    ID: str
    URL: str


class ThumbnailURLsResponse(BaseModel):
    urls: List[ThumbnailURLItem]
    raw: Optional[Any] = None


# =========================
# NORMALIZE CODES
# =========================
class NormalizeCodesInput(BaseModel):
    prefecture: Optional[str] = None
    municipality: Optional[str] = None


class MunicipalityCandidate(BaseModel):
    municipality_code: str
    municipality_name: str


class NormalizeCodesOutput(BaseModel):
    prefecture_code: Optional[str] = None
    prefecture_name: Optional[str] = None
    municipality_code: Optional[str] = None
    municipality_name: Optional[str] = None
    candidates: List[MunicipalityCandidate] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    normalization_meta: Dict[str, Any] = Field(default_factory=dict)


# forward refs
CountAttributeSliceSettingInput.model_rebuild()
CountSlice.model_rebuild()
