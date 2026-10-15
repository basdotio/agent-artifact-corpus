"""Tool server for the Marrow Creek bird count intake.

Holds the species taxonomy, the run's state (the roster and the review queue)
and the exact rules: what a valid record is, what counts as a duplicate, and
which species names are official. The agent in intake_agent.py reads the messy
notes; everything that has to be exactly right is decided here.

Run this file directly to serve the same tools over stdio:

    python intake_server.py
"""
import json
import re
from pathlib import Path

from fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

DATA_DIR = Path(__file__).resolve().parent / "data"

# The count ran over one week; a date outside it is not part of this count.
COUNT_WINDOW_START = "2026-09-14"
COUNT_WINDOW_END = "2026-09-20"

SOURCES = ("logbook", "email", "spreadsheet")

# Reasons the agent may give when it sends a note to review.
# "possible_duplicate" is not in this list: only commit_observation sets it.
FLAG_REASONS = (
    "unknown_species",       # the name did not resolve to anything in the taxonomy
    "species_group",         # it resolved to a group such as "gull sp.", not one species
    "missing_field",         # species, count, date or location is absent or blank
    "vague_count",           # "a handful", "a flock", "lots"
    "unclear_date",          # the day cannot be pinned down
    "outside_count_window",  # a clear date that is not in the count week
    "invalid_record",        # commit_observation rejected it for another reason
)


# ---------------------------------------------------------------------------
# Taxonomy lookup
# ---------------------------------------------------------------------------

def normalize(text):
    """Lower-case, turn punctuation into spaces and collapse whitespace."""
    text = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    return text.strip()


def load_taxonomy(data_dir=DATA_DIR):
    """Return (by_code, by_name): taxa keyed by code and by normalised name or alias."""
    taxa = json.loads((data_dir / "taxonomy.json").read_text(encoding="utf-8"))
    aliases = json.loads((data_dir / "aliases.json").read_text(encoding="utf-8"))

    by_code = {taxon["speciesCode"]: taxon for taxon in taxa}
    by_name = {normalize(taxon["comName"]): taxon for taxon in taxa}
    for alias, code in aliases.items():
        by_name.setdefault(normalize(alias), by_code[code])
    return by_code, by_name


BY_CODE, BY_NAME = load_taxonomy()


def resolve(text):
    """Exact lookup of a name, nickname or known typo. Returns a taxon dict or None."""
    return BY_NAME.get(normalize(text))


# ---------------------------------------------------------------------------
# The record, the checks and the run's state
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """One species seen at one place on one day."""
    species_code: str
    common_name: str
    scientific_name: str
    count: int = Field(gt=0)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    location: str = Field(min_length=1)
    source: str


def build_record(species_code, count, date, location, source):
    """Assemble a candidate record. The names always come from the taxonomy."""
    taxon = BY_CODE.get(species_code, {})
    return {
        "species_code": species_code,
        "common_name": taxon.get("comName", ""),
        "scientific_name": taxon.get("sciName", ""),
        "count": count,
        "date": date,
        "location": location.strip() if isinstance(location, str) else location,
        "source": source,
    }


def validate(record):
    """Decide whether a candidate record may go on the roster.

    Returns {"valid": bool, "errors": [...]}, with one short message per problem.
    """
    errors = []

    try:
        Observation(**record)
    except ValidationError as e:
        for problem in e.errors():
            field = ".".join(str(part) for part in problem["loc"])
            errors.append(f"{field}: {problem['msg']}")

    date = str(record.get("date", ""))
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        # ISO dates sort correctly as plain strings
        if not COUNT_WINDOW_START <= date <= COUNT_WINDOW_END:
            errors.append(f"date: {date} is outside the count window "
                          f"({COUNT_WINDOW_START} to {COUNT_WINDOW_END})")

    taxon = BY_CODE.get(record.get("species_code"))
    if taxon is None:
        errors.append(f"species_code: {record.get('species_code')!r} is not in the taxonomy")
    elif taxon["category"] != "species":
        errors.append(f"species_code: {taxon['comName']!r} is a group, not a single species")

    if record.get("source") not in SOURCES:
        errors.append(f"source: must be one of {', '.join(SOURCES)}")

    return {"valid": not errors, "errors": errors}


class Roster:
    """The state of one intake run: committed records and items for human review."""

    def __init__(self):
        self.clean = []
        self.review = []

    def reset(self):
        self.clean.clear()
        self.review.clear()

    def duplicate_of(self, record):
        """Return the id of a committed record for the same species, day and place."""
        location = record["location"].strip().lower()
        for existing in self.clean:
            if (existing["species_code"] == record["species_code"]
                    and existing["date"] == record["date"]
                    and existing["location"].strip().lower() == location):
                return existing["record_id"]
        return None

    def add(self, record):
        committed = dict(record)
        committed["record_id"] = f"obs-{len(self.clean) + 1}"
        self.clean.append(committed)
        return committed["record_id"]

    def flag(self, raw_input, source, reason, existing_record_id=None):
        """Queue a review item. Queuing the same item twice has no effect."""
        item = {
            "raw_input": raw_input,
            "source": source,
            "reason": reason,
            "existing_record_id": existing_record_id,
        }
        if item in self.review:
            return False
        self.review.append(item)
        return True

    def summary(self):
        """Totals by species and review items by reason."""
        by_species = {}
        for record in self.clean:
            by_species[record["common_name"]] = by_species.get(record["common_name"], 0) + record["count"]
        by_reason = {}
        for item in self.review:
            by_reason[item["reason"]] = by_reason.get(item["reason"], 0) + 1
        return {
            "committed": len(self.clean),
            "flagged": len(self.review),
            "birds_by_species": dict(sorted(by_species.items(), key=lambda kv: -kv[1])),
            "flags_by_reason": dict(sorted(by_reason.items(), key=lambda kv: -kv[1])),
        }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

mcp = FastMCP("Marrow Creek Intake")
ROSTER = Roster()


def resolve_species(name: str) -> dict:
    """Look up a species name exactly as the observer wrote it.

    This is an exact lookup against the official taxonomy and a table of known
    nicknames and misspellings. It does not guess, and neither should you: if
    the result is "no_match", or the category is not "species", flag the note
    instead of committing it.

    Args:
        name: the bird's name only, singular, with counts and filler words removed.
            'pair of mallards' -> 'mallard'; 'half a dozen cedar waxwings' -> 'cedar waxwing';
            'some kind of gull' -> 'gull'. Keep the observer's spelling, including typos.
    """
    taxon = resolve(name)
    if taxon is None:
        return {"match": "no_match"}
    return {
        "match": "ok",
        "species_code": taxon["speciesCode"],
        "common_name": taxon["comName"],
        "scientific_name": taxon["sciName"],
        "category": taxon["category"],
    }


def validate_observation(species_code: str, count: int, date: str, location: str, source: str) -> dict:
    """Check a candidate record without saving it.

    Use this when you are unsure whether a record will be accepted. It applies
    the same rules as commit_observation.

    Args:
        species_code: the code returned by resolve_species
        count: number of birds, a whole number above zero
        date: the day of the sighting as YYYY-MM-DD
        location: where the birds were seen
        source: logbook, email or spreadsheet
    """
    return validate(build_record(species_code, count, date, location, source))


def commit_observation(species_code: str, count: int, date: str, location: str,
                       source: str, raw_input: str = "") -> dict:
    """Save one observation to the clean roster. This is the only way onto the roster.

    Every call re-checks the record and looks for a duplicate (same species, same
    day, same place). An invalid record is rejected with the reasons. A duplicate
    is not saved; it is sent to review as "possible_duplicate" automatically, so
    do not flag duplicates yourself.

    Args:
        species_code: the code returned by resolve_species
        count: number of birds, a whole number above zero
        date: the day of the sighting as YYYY-MM-DD
        location: where the birds were seen
        source: logbook, email or spreadsheet
        raw_input: the original note, word for word
    """
    record = build_record(species_code, count, date, location, source)
    check = validate(record)
    if not check["valid"]:
        return {"committed": False, "errors": check["errors"]}

    record = Observation(**record).model_dump()
    existing = ROSTER.duplicate_of(record)
    if existing:
        ROSTER.flag(raw_input or record["common_name"], source, "possible_duplicate", existing)
        return {"committed": False, "duplicate": True, "existing_record_id": existing}

    return {"committed": True, "record_id": ROSTER.add(record)}


def flag_for_review(raw_input: str, source: str, reason: str) -> dict:
    """Send a note to the human review queue instead of guessing.

    Args:
        raw_input: the original note, word for word
        source: logbook, email or spreadsheet
        reason: one of unknown_species, species_group, missing_field, vague_count,
            unclear_date, outside_count_window, invalid_record
    """
    if reason not in FLAG_REASONS:
        return {"queued": False, "error": f"reason must be one of: {', '.join(FLAG_REASONS)}"}
    if source not in SOURCES:
        return {"queued": False, "error": f"source must be one of: {', '.join(SOURCES)}"}
    newly_queued = ROSTER.flag(raw_input, source, reason)
    return {"queued": True, "already_queued": not newly_queued}


# Registered this way so the plain functions above stay directly callable in tests.
for _tool in (resolve_species, validate_observation, commit_observation, flag_for_review):
    mcp.tool()(_tool)


@mcp.resource("taxonomy://marrow-creek/species")
def taxonomy_resource() -> str:
    """The species list used by resolve_species, for a host to browse."""
    return json.dumps(list(BY_CODE.values()), indent=2)


if __name__ == "__main__":
    mcp.run()
