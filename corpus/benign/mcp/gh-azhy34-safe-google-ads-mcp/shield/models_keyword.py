from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator

# Country code -> (geo target constant, language constant the country is searched in).
# IDs: developers.google.com/google-ads/api/reference/data/geotargets and .../codes-formats#languages
COUNTRIES: Dict[str, Tuple[str, str]] = {
    "DE": ("2276", "1001"), "AT": ("2040", "1001"), "CH": ("2756", "1001"),
    "FR": ("2250", "1002"), "BE": ("2056", "1002"),
    "ES": ("2724", "1003"), "IT": ("2380", "1004"), "NL": ("2528", "1010"), "PL": ("2616", "1030"),
    "GB": ("2826", "1000"), "IE": ("2372", "1000"), "US": ("2840", "1000"), "CA": ("2124", "1000"),
}

MAX_KEYWORD_CHARS = 80

class KeywordVolumesRequest(BaseModel):
    keywords: List[str] = Field(..., min_length=1, max_length=20, description="Words or phrases to check, 1-20")
    countries: List[str] = Field(default_factory=lambda: ["DE"], min_length=1, max_length=5,
                                 description=f"1-5 country codes, each answered separately: {', '.join(COUNTRIES)}")

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, v: List[str]) -> List[str]:
        cleaned, seen = [], set()
        for word in v:
            word = " ".join((word or "").split())
            if not word:
                raise ValueError("Пустое слово в списке keywords")
            if len(word) > MAX_KEYWORD_CHARS:
                raise ValueError(f"Слово длиннее {MAX_KEYWORD_CHARS} символов: «{word[:40]}…»")
            if word.lower() not in seen:
                seen.add(word.lower())
                cleaned.append(word)
        return cleaned

    @field_validator("countries")
    @classmethod
    def known_countries(cls, v: List[str]) -> List[str]:
        codes = list(dict.fromkeys((c or "").strip().upper() for c in v))
        unknown = [c for c in codes if c not in COUNTRIES]
        if unknown:
            raise ValueError(f"Неизвестные страны {unknown}; доступны: {', '.join(COUNTRIES)}")
        return codes

class MonthVolume(BaseModel):
    month: str = Field(..., description="YYYY-MM")
    searches: int

class KeywordVolume(BaseModel):
    keyword: str
    avg_monthly: Optional[int] = Field(None, description="Average monthly searches over the last 12 months; None = no data")
    competition: Optional[str] = Field(None, description="LOW / MEDIUM / HIGH (ad competition, not SEO)")
    competition_index: Optional[int] = Field(None, description="0-100")
    cpc_low_eur: Optional[float] = Field(None, description="Top-of-page bid, 20th percentile, account currency (EUR)")
    cpc_high_eur: Optional[float] = Field(None, description="Top-of-page bid, 80th percentile, account currency (EUR)")
    close_variants: List[str] = Field(default_factory=list, description="Spellings Google counted together with this keyword")
    peak_month: Optional[str] = Field(None, description="YYYY-MM with the most searches")
    months: List[MonthVolume] = Field(default_factory=list, description="Searches per month, oldest first")

class CountryVolumes(BaseModel):
    country: str
    geo_target: str
    language: str
    test_account_fallback: bool = Field(False, description="True: the answer came from the test account and carries no volumes")
    keywords: List[KeywordVolume] = Field(default_factory=list)

class KeywordVolumesReport(BaseModel):
    countries: List[CountryVolumes] = Field(default_factory=list)
    verdicts: List[str] = Field(default_factory=list)
