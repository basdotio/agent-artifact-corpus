import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GuitarProfile(StrictModel):
    guitar: str = "Squier Telecaster"
    pickup: str = "bridge"
    tuning: str = "E A D G B E (standard)"
    volume: float = Field(default=10, ge=0, le=10)
    tone: float = Field(default=10, ge=0, le=10)


class ParameterSpec(StrictModel):
    name: str
    unit: Literal[
        "knob_position", "amp_scale", "effect_scale", "ms", "Hz", "dB", "cents", "semitones", "enum"
    ] = "knob_position"
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = Field(default=None, gt=0)
    choices: list[str] = Field(default_factory=list)


class ModelSpec(StrictModel):
    name: str
    kind: Literal["amp", "cabinet", "effect"]
    parameters: list[ParameterSpec] = Field(default_factory=list)
    observed: bool = False
    evidence: str = ""


class Block(StrictModel):
    model: str
    kind: Literal["amp", "cabinet", "effect"]
    enabled: bool = True
    parameters: dict[str, float | str] = Field(default_factory=dict)


class TonePlan(StrictModel):
    name: str = Field(min_length=1, max_length=28, pattern=r"^[A-Za-z0-9 _.-]+$")
    slot: int = Field(ge=1, le=200)
    section: str = "Main riff"
    chain: list[Block] = Field(min_length=1, max_length=6)
    rationale: str = ""
    setup_recommendation: str = "Start with bridge pickup, guitar volume and tone at 10."
    limitations: list[str] = Field(default_factory=list)

    def validate_catalog(self, catalog: list[ModelSpec]):
        known = {(m.kind, m.name): m for m in catalog if m.observed}
        if sum(b.kind == "amp" for b in self.chain) != 1:
            raise ValueError("A preset must contain exactly one amp")
        if sum(b.kind == "cabinet" for b in self.chain) > 1:
            raise ValueError("A preset may contain at most one cabinet")
        for block in self.chain:
            spec = known.get((block.kind, block.model))
            if not spec:
                raise ValueError(f"Unverified {block.kind}: {block.model}")
            parameters = {p.name: p for p in spec.parameters}
            for name, value in block.parameters.items():
                if name not in parameters:
                    raise ValueError(f"Unverified parameter: {block.model}.{name}")
                p = parameters[name]
                if isinstance(value, str):
                    if value not in p.choices:
                        raise ValueError(f"Invalid choice: {name}")
                elif p.minimum is None or p.maximum is None or not p.minimum <= value <= p.maximum:
                    raise ValueError(f"Parameter out of range: {name}")
                elif p.step is not None and not math.isclose(
                    (value - p.minimum) / p.step, round((value - p.minimum) / p.step), abs_tol=1e-6
                ):
                    raise ValueError(f"Parameter requires increments of {p.step}: {name}")


class SessionRequest(StrictModel):
    song: str = Field(default="Atom City Queen", min_length=1, max_length=120)
    artist: str = Field(default="Failure", min_length=1, max_length=120)
    slot: int = Field(default=172, ge=1, le=200)
    profile: GuitarProfile = Field(default_factory=GuitarProfile)
    max_trials: int = Field(default=6, ge=1, le=12)


class ReferenceRequest(StrictModel):
    url: str = Field(max_length=2048)
    source: str = Field(max_length=300)
    permitted: bool = False
    start: float = Field(default=0, ge=0, le=3600)
    duration: float = Field(default=20, ge=5, le=60)


class CaptureRequest(StrictModel):
    role: Literal["baseline", "trial", "reference"] = "baseline"
    seconds: int = Field(default=10, ge=5, le=30)
    ready: bool = False
    permitted: bool = False


class Feedback(StrictModel):
    accepted: bool = False
    description: str = Field(default="", max_length=500)
