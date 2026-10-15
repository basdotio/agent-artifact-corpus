"""Checks for the deterministic part of the project. No API key needed."""
import pytest

from intake_server import (
    Roster,
    build_record,
    commit_observation,
    flag_for_review,
    resolve,
    resolve_species,
    validate,
    validate_observation,
)


def record(**overrides):
    values = dict(species_code="cangoo", count=34, date="2026-09-19", location="Mill Pond", source="logbook")
    values.update(overrides)
    return build_record(**values)


# --- taxonomy lookup --------------------------------------------------------

@pytest.mark.parametrize("text, code", [
    ("Canada Goose", "cangoo"),
    ("canada goose", "cangoo"),
    ("  Canda Goose ", "cangoo"),       # known typo
    ("red-tailed hawk", "rethaw"),      # punctuation is ignored
    ("Butterbutt", "yerwar"),           # nickname
    ("chickadee", "bkcchi"),
])
def test_resolve_finds_names_nicknames_and_typos(text, code):
    assert resolve(text)["speciesCode"] == code


@pytest.mark.parametrize("text", ["Marsh Gryphon Wren", "snowy owl", "", "pair of mallards"])
def test_resolve_does_not_guess(text):
    assert resolve(text) is None


def test_resolve_species_reports_groups_as_groups():
    result = resolve_species("gull")
    assert result["match"] == "ok"
    assert result["category"] == "spuh"


def test_resolve_species_no_match():
    assert resolve_species("Marsh Gryphon Wren") == {"match": "no_match"}


# --- validation -------------------------------------------------------------

def test_valid_record_passes():
    assert validate(record()) == {"valid": True, "errors": []}


def test_names_come_from_the_taxonomy():
    built = record(species_code="amerob")
    assert built["common_name"] == "American Robin"
    assert built["scientific_name"] == "Turdus migratorius"


@pytest.mark.parametrize("overrides, expected", [
    ({"count": 0}, "count"),
    ({"count": -3}, "count"),
    ({"count": "a few"}, "count"),
    ({"location": ""}, "location"),
    ({"location": "   "}, "location"),
    ({"date": "9/19"}, "date"),
    ({"date": "2026-08-30"}, "outside the count window"),
    ({"date": "2026-09-21"}, "outside the count window"),
    ({"species_code": "x-gull"}, "group"),
    ({"species_code": "notacode"}, "not in the taxonomy"),
    ({"source": "rumour"}, "source"),
])
def test_invalid_records_are_rejected(overrides, expected):
    result = validate(record(**overrides))
    assert result["valid"] is False
    assert any(expected in error for error in result["errors"])


def test_window_edges_are_inside():
    assert validate(record(date="2026-09-14"))["valid"]
    assert validate(record(date="2026-09-20"))["valid"]


def test_validate_observation_does_not_save(fresh_roster):
    assert validate_observation("cangoo", 34, "2026-09-19", "Mill Pond", "logbook")["valid"]
    assert fresh_roster.clean == []


# --- roster -----------------------------------------------------------------

def test_roster_assigns_sequential_ids():
    roster = Roster()
    assert roster.add(record()) == "obs-1"
    assert roster.add(record(species_code="mallar3")) == "obs-2"


def test_duplicate_ignores_case_and_spacing_of_location():
    roster = Roster()
    roster.add(record(location="Mill Pond"))
    assert roster.duplicate_of(record(location="  mill pond ")) == "obs-1"


@pytest.mark.parametrize("overrides", [
    {"species_code": "mallar3"},
    {"date": "2026-09-20"},
    {"location": "Quarry Trail"},
])
def test_different_species_day_or_place_is_not_a_duplicate(overrides):
    roster = Roster()
    roster.add(record())
    assert roster.duplicate_of(record(**overrides)) is None


def test_flagging_twice_queues_once():
    roster = Roster()
    assert roster.flag("some kind of gull", "logbook", "species_group") is True
    assert roster.flag("some kind of gull", "logbook", "species_group") is False
    assert len(roster.review) == 1


# --- the commit gate --------------------------------------------------------

def test_commit_saves_a_valid_record(fresh_roster):
    result = commit_observation("cangoo", 34, "2026-09-19", "Mill Pond", "logbook", "Canada Goose x 34")
    assert result == {"committed": True, "record_id": "obs-1"}
    assert fresh_roster.clean[0]["common_name"] == "Canada Goose"


def test_commit_rejects_invalid_records_without_saving(fresh_roster):
    result = commit_observation("tuftit", 0, "2026-09-20", "Old Orchard", "spreadsheet")
    assert result["committed"] is False
    assert result["errors"]
    assert fresh_roster.clean == [] and fresh_roster.review == []


def test_commit_rejects_groups(fresh_roster):
    assert commit_observation("x-hawk", 2, "2026-09-19", "Riverside Meadow", "email")["committed"] is False
    assert fresh_roster.clean == []


def test_commit_sends_duplicates_to_review(fresh_roster):
    commit_observation("cangoo", 34, "2026-09-19", "Mill Pond", "logbook", "Canada Goose x 34")
    result = commit_observation("cangoo", 34, "2026-09-19", "mill pond", "spreadsheet", "Canda Goose, 34")
    assert result == {"committed": False, "duplicate": True, "existing_record_id": "obs-1"}
    assert len(fresh_roster.clean) == 1
    assert fresh_roster.review == [{
        "raw_input": "Canda Goose, 34",
        "source": "spreadsheet",
        "reason": "possible_duplicate",
        "existing_record_id": "obs-1",
    }]


def test_count_given_as_text_digits_is_stored_as_a_number(fresh_roster):
    commit_observation("killde", "2", "2026-09-19", "Mill Pond", "spreadsheet")
    assert fresh_roster.clean[0]["count"] == 2


# --- flagging ---------------------------------------------------------------

def test_flag_for_review_queues_an_item(fresh_roster):
    assert flag_for_review("a couple of hawks", "email", "species_group")["queued"] is True
    assert fresh_roster.review[0]["reason"] == "species_group"


def test_flag_for_review_rejects_unknown_reasons(fresh_roster):
    result = flag_for_review("a couple of hawks", "email", "looked_weird")
    assert result["queued"] is False
    assert fresh_roster.review == []


def test_agent_cannot_flag_duplicates_itself(fresh_roster):
    assert flag_for_review("Canda Goose", "spreadsheet", "possible_duplicate")["queued"] is False
