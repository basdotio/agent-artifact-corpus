"""South African Triage Scale (SATS), adult chart, as deterministic rules.

Every number this module produces carries a rule id that points into
data/sats_reference.md, so a priority level can always be traced back to the
vital sign or symptom entry that caused it.

Source: "Adult SATS chart" (c) 2012 South African Triage Group under the
auspices of the Emergency Medicine Society of South Africa (EMSSA), licensed
CC BY-NC-SA 3.0. Thresholds were transcribed by hand and must be checked
against the official chart before any clinical use (see EVALS.md).

The scale applies to patients aged 12 and over (or taller than 150 cm).
Children need the paediatric scale, which this project does not implement.
"""

from __future__ import annotations

from dataclasses import dataclass

RULESET = "SATS adult chart (EMSSA 2012), transcribed for Spark Triage"
COLOURS = ["green", "yellow", "orange", "red"]
RANK = {c: i for i, c in enumerate(COLOURS)}
TARGET_MINUTES = {"red": 0, "orange": 10, "yellow": 60, "green": 240}
ADULT_MIN_AGE = 12

REQUIRED_VITALS = ["rr", "hr", "sbp", "temp", "avpu", "mobility", "trauma"]
AVPU_VALUES = {"A", "V", "C", "P", "U"}
MOBILITY_VALUES = {"walking", "with_help", "immobile"}


@dataclass(frozen=True)
class Component:
    param: str
    value: object
    points: int
    rule_id: str

    def as_dict(self) -> dict:
        return {"param": self.param, "value": self.value, "points": self.points, "rule_id": self.rule_id}


def missing_vitals(vitals: dict) -> list[str]:
    return [k for k in REQUIRED_VITALS if vitals.get(k) is None]


def _rr(v: float) -> tuple[int, str]:
    if v < 9:
        return 2, "SATS-TEWS-RR-LT9"
    if v <= 14:
        return 0, "SATS-TEWS-RR-9-14"
    if v <= 20:
        return 1, "SATS-TEWS-RR-15-20"
    if v <= 29:
        return 2, "SATS-TEWS-RR-21-29"
    return 3, "SATS-TEWS-RR-GT29"


def _hr(v: float) -> tuple[int, str]:
    if v < 41:
        return 2, "SATS-TEWS-HR-LT41"
    if v <= 50:
        return 1, "SATS-TEWS-HR-41-50"
    if v <= 100:
        return 0, "SATS-TEWS-HR-51-100"
    if v <= 110:
        return 1, "SATS-TEWS-HR-101-110"
    if v <= 129:
        return 2, "SATS-TEWS-HR-111-129"
    return 3, "SATS-TEWS-HR-GT129"


def _sbp(v: float) -> tuple[int, str]:
    if v < 71:
        return 3, "SATS-TEWS-SBP-LT71"
    if v <= 80:
        return 2, "SATS-TEWS-SBP-71-80"
    if v <= 100:
        return 1, "SATS-TEWS-SBP-81-100"
    if v <= 199:
        return 0, "SATS-TEWS-SBP-101-199"
    return 2, "SATS-TEWS-SBP-GT199"


def _temp(v: float) -> tuple[int, str]:
    if v < 35:
        return 2, "SATS-TEWS-TEMP-LT35"
    if v <= 38.4:
        return 0, "SATS-TEWS-TEMP-35-38.4"
    return 2, "SATS-TEWS-TEMP-GT38.4"


_AVPU = {
    "A": (0, "SATS-TEWS-AVPU-ALERT"),
    "V": (1, "SATS-TEWS-AVPU-VOICE"),
    "C": (1, "SATS-TEWS-AVPU-CONFUSED"),
    "P": (2, "SATS-TEWS-AVPU-PAIN"),
    "U": (3, "SATS-TEWS-AVPU-UNRESPONSIVE"),
}
_MOBILITY = {
    "walking": (0, "SATS-TEWS-MOB-WALKING"),
    "with_help": (1, "SATS-TEWS-MOB-WITH-HELP"),
    "immobile": (2, "SATS-TEWS-MOB-STRETCHER"),
}


def validate_vitals(vitals: dict) -> list[str]:
    """Return a list of problems; empty means the vitals can be scored."""
    problems = [f"missing: {k}" for k in missing_vitals(vitals)]
    if vitals.get("avpu") is not None and vitals["avpu"] not in AVPU_VALUES:
        problems.append(f"avpu must be one of {sorted(AVPU_VALUES)}")
    if vitals.get("mobility") is not None and vitals["mobility"] not in MOBILITY_VALUES:
        problems.append(f"mobility must be one of {sorted(MOBILITY_VALUES)}")
    ranges = {"rr": (0, 80), "hr": (0, 250), "sbp": (0, 300), "temp": (25, 45)}
    for k, (lo, hi) in ranges.items():
        val = vitals.get(k)
        if val is not None and not (lo <= float(val) <= hi):
            problems.append(f"{k}={val} outside plausible range {lo}-{hi}; re-measure")
    return problems


def tews(vitals: dict) -> dict:
    """Compute the Triage Early Warning Score with a per-parameter breakdown."""
    problems = validate_vitals(vitals)
    if problems:
        raise ValueError("; ".join(problems))
    comps = [
        Component("mobility", vitals["mobility"], *_MOBILITY[vitals["mobility"]]),
        Component("rr", vitals["rr"], *_rr(float(vitals["rr"]))),
        Component("hr", vitals["hr"], *_hr(float(vitals["hr"]))),
        Component("sbp", vitals["sbp"], *_sbp(float(vitals["sbp"]))),
        Component("temp", vitals["temp"], *_temp(float(vitals["temp"]))),
        Component("avpu", vitals["avpu"], *_AVPU[vitals["avpu"]]),
        Component(
            "trauma",
            bool(vitals["trauma"]),
            *((1, "SATS-TEWS-TRAUMA-YES") if vitals["trauma"] else (0, "SATS-TEWS-TRAUMA-NO")),
        ),
    ]
    score = sum(c.points for c in comps)
    return {"tews": score, "colour": tews_colour(score), "components": [c.as_dict() for c in comps]}


def tews_colour(score: int) -> str:
    if score >= 7:
        return "red"
    if score >= 5:
        return "orange"
    if score >= 3:
        return "yellow"
    return "green"


# Clinical discriminators. "symptom" ones must be backed by a quote from the
# intake card; "measured" ones are computed by the server from recorded values
# and are never chosen by the model.
DISCRIMINATORS: dict[str, dict] = {
    # Emergency signs (red)
    "AIRWAY_COMPROMISED": {"label": "Airway compromised or obstructed", "colour": "red", "kind": "symptom"},
    "BREATHING_NOT_EFFECTIVE": {"label": "Not breathing effectively", "colour": "red", "kind": "symptom"},
    "CARDIAC_ARREST": {"label": "Cardiac arrest / no pulse", "colour": "red", "kind": "symptom"},
    "SEIZURE_CURRENT": {"label": "Seizure, current", "colour": "red", "kind": "symptom"},
    "BURN_FACIAL_INHALATION": {"label": "Burn, facial or inhalation", "colour": "red", "kind": "symptom"},
    "HYPOGLYCAEMIA": {"label": "Hypoglycaemia, glucose below 3 mmol/L", "colour": "red", "kind": "measured"},
    # Very urgent (orange)
    "SOB_ACUTE": {"label": "Shortness of breath, acute", "colour": "orange", "kind": "symptom"},
    "COUGHING_BLOOD": {"label": "Coughing blood", "colour": "orange", "kind": "symptom"},
    "CHEST_PAIN": {"label": "Chest pain", "colour": "orange", "kind": "symptom"},
    "HAEMORRHAGE_UNCONTROLLED": {"label": "Haemorrhage, uncontrolled", "colour": "orange", "kind": "symptom"},
    "SEIZURE_POST_ICTAL": {"label": "Seizure, post-ictal", "colour": "orange", "kind": "symptom"},
    "FOCAL_NEUROLOGY_ACUTE": {"label": "Focal neurology, acute", "colour": "orange", "kind": "symptom"},
    "LOC_REDUCED": {"label": "Level of consciousness reduced", "colour": "orange", "kind": "symptom"},
    "PSYCHOSIS_AGGRESSION": {"label": "Psychosis or aggression", "colour": "orange", "kind": "symptom"},
    "THREATENED_LIMB": {"label": "Threatened limb", "colour": "orange", "kind": "symptom"},
    "DISLOCATION_LARGER_JOINT": {"label": "Dislocation of larger joint (not finger or toe)", "colour": "orange", "kind": "symptom"},
    "FRACTURE_COMPOUND": {"label": "Fracture, compound (open)", "colour": "orange", "kind": "symptom"},
    "BURN_OVER_20PCT": {"label": "Burn over 20% of body surface", "colour": "orange", "kind": "symptom"},
    "BURN_ELECTRICAL": {"label": "Burn, electrical", "colour": "orange", "kind": "symptom"},
    "BURN_CIRCUMFERENTIAL": {"label": "Burn, circumferential", "colour": "orange", "kind": "symptom"},
    "BURN_CHEMICAL": {"label": "Burn, chemical", "colour": "orange", "kind": "symptom"},
    "POISONING_OVERDOSE": {"label": "Poisoning or overdose", "colour": "orange", "kind": "symptom"},
    "DIABETIC_GLUCOSE_GT11_KETONES": {"label": "Diabetic, glucose above 11 mmol/L with ketonuria", "colour": "orange", "kind": "measured"},
    "VOMITING_FRESH_BLOOD": {"label": "Vomiting fresh blood", "colour": "orange", "kind": "symptom"},
    "PREGNANCY_ABDO_TRAUMA_OR_PAIN": {"label": "Pregnancy with abdominal trauma or abdominal pain", "colour": "orange", "kind": "symptom"},
    "PAIN_VERY_SEVERE": {"label": "Very severe pain", "colour": "orange", "kind": "symptom"},
    # Urgent (yellow)
    "HAEMORRHAGE_CONTROLLED": {"label": "Haemorrhage, controlled", "colour": "yellow", "kind": "symptom"},
    "FRACTURE_CLOSED": {"label": "Fracture, closed", "colour": "yellow", "kind": "symptom"},
    "BURN_OTHER": {"label": "Burn, other", "colour": "yellow", "kind": "symptom"},
    "ABDOMINAL_PAIN": {"label": "Abdominal pain", "colour": "yellow", "kind": "symptom"},
    "DIABETIC_GLUCOSE_GT17_NO_KETONES": {"label": "Diabetic, glucose above 17 mmol/L, no ketonuria", "colour": "yellow", "kind": "measured"},
    "VOMITING_PERSISTENT": {"label": "Vomiting, persistent", "colour": "yellow", "kind": "symptom"},
    "PREGNANCY_AND_TRAUMA": {"label": "Pregnancy and trauma", "colour": "yellow", "kind": "symptom"},
    "PAIN_MODERATE": {"label": "Moderate pain", "colour": "yellow", "kind": "symptom"},
}
for _code, _d in DISCRIMINATORS.items():
    _d["rule_id"] = f"SATS-DISC-{_code}"


def measured_discriminators(vitals: dict) -> list[dict]:
    """Discriminators the server derives from numbers on the card."""
    out = []
    g = vitals.get("glucose_mmol")
    ketones = vitals.get("ketonuria")
    if g is not None:
        g = float(g)
        if g < 3:
            out.append(("HYPOGLYCAEMIA", f"glucose_mmol={g}"))
        elif g > 11 and ketones is True:
            out.append(("DIABETIC_GLUCOSE_GT11_KETONES", f"glucose_mmol={g}, ketonuria=true"))
        elif g > 17 and ketones is False:
            out.append(("DIABETIC_GLUCOSE_GT17_NO_KETONES", f"glucose_mmol={g}, ketonuria=false"))
    return [
        {"code": c, "colour": DISCRIMINATORS[c]["colour"], "rule_id": DISCRIMINATORS[c]["rule_id"],
         "evidence": ev, "evidence_source": "vitals entry"}
        for c, ev in out
    ]


def most_urgent(colours: list[str]) -> str:
    return max(colours, key=lambda c: RANK[c]) if colours else "green"
