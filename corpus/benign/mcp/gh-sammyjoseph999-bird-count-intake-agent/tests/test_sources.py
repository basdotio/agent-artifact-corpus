"""Replays the tool calls a careful clerk would make for the bundled sources.

This checks the data and the server together: every name in the sources
resolves (or fails to) as intended, and the gate reaches the expected totals.
It says nothing about how a real model behaves; check_outputs.py covers that.
"""
from intake_server import commit_observation, flag_for_review, resolve_species

SAT, SUN = "2026-09-19", "2026-09-20"

# (name passed to resolve_species, count, date, location, source)
COMMITS = [
    ("Canada Goose", 34, SAT, "Mill Pond", "logbook"),
    ("mallard", 2, SAT, "Mill Pond", "logbook"),
    ("wood duck", 3, SAT, "Mill Pond", "logbook"),
    ("great blue heron", 1, SAT, "Mill Pond", "logbook"),
    ("cedar waxwing", 6, SAT, "Quarry Trail", "logbook"),
    ("chickadee", 5, SAT, "Quarry Trail", "logbook"),
    ("red tail", 1, SAT, "Quarry Trail", "logbook"),
    ("blue jay", 4, SAT, "Quarry Trail", "logbook"),
    ("robin", 20, SAT, "Old Orchard", "logbook"),
    ("flicker", 2, SAT, "Old Orchard", "logbook"),
    ("goldfinch", 7, SAT, "Old Orchard", "logbook"),
    ("kingfisher", 1, SAT, "Old Orchard", "logbook"),
    ("starling", 12, SAT, "Riverside Meadow", "email"),
    ("mourning dove", 3, SAT, "Riverside Meadow", "email"),
    ("cardinal", 2, SAT, "Riverside Meadow", "email"),
    ("turkey vulture", 1, SAT, "Riverside Meadow", "email"),
    ("bald eagle", 1, SUN, "Riverside Meadow", "email"),
    ("Killdeer", 2, SAT, "Mill Pond", "spreadsheet"),
    ("Osprey", 1, SAT, "mill pond", "spreadsheet"),
    ("White-throated Sparrow", 12, SUN, "Quarry Trail", "spreadsheet"),
    ("Junco", 6, SUN, "Quarry Trail", "spreadsheet"),
    ("Butterbutt", 9, SUN, "Old Orchard", "spreadsheet"),
]


def test_every_committable_sighting_resolves_to_a_species_and_commits(fresh_roster):
    for name, count, date, location, source in COMMITS:
        taxon = resolve_species(name)
        assert taxon["match"] == "ok" and taxon["category"] == "species", name
        result = commit_observation(taxon["species_code"], count, date, location, source, name)
        assert result["committed"] is True, (name, result)
    assert len(fresh_roster.clean) == 22
    assert len({(r["species_code"], r["date"], r["location"].lower()) for r in fresh_roster.clean}) == 22


def test_the_goose_logged_twice_is_caught(fresh_roster):
    commit_observation("cangoo", 34, SAT, "Mill Pond", "logbook", "Canada Goose x 34")
    taxon = resolve_species("Canda Goose")
    result = commit_observation(taxon["species_code"], 34, SAT, "Mill Pond", "spreadsheet", "Canda Goose")
    assert result["duplicate"] is True
    assert fresh_roster.review[0]["reason"] == "possible_duplicate"


def test_notes_that_must_not_reach_the_roster(fresh_roster):
    assert resolve_species("gull")["category"] == "spuh"
    assert resolve_species("hawk")["category"] == "spuh"
    assert resolve_species("Marsh Gryphon Wren")["match"] == "no_match"
    assert resolve_species("snowy owl")["match"] == "no_match"
    # blank location, zero count, date before the count week
    assert commit_observation("dowwoo", 2, SUN, "", "spreadsheet")["committed"] is False
    assert commit_observation("tuftit", 0, SUN, "Old Orchard", "spreadsheet")["committed"] is False
    assert commit_observation("houspa", 15, "2026-08-30", "Riverside Meadow", "spreadsheet")["committed"] is False
    assert flag_for_review("a flock of grackles", "logbook", "vague_count")["queued"] is True
    assert fresh_roster.clean == []
