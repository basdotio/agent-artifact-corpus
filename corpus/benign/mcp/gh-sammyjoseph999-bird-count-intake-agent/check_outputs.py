"""Check the files written by intake_agent.py.

A model does not give the same answer on every run, so this does not compare
the output with one fixed roster. It checks properties that must hold however
the model worded things, and allows a small range where a call is borderline.

Usage:
    python intake_agent.py
    python check_outputs.py
"""
import json
import sys
from pathlib import Path

from intake_server import BY_CODE, validate

HERE = Path(__file__).resolve().parent
results = []


def check(description, passed, detail=""):
    results.append(passed)
    print(f"[{'PASS' if passed else 'FAIL'}] {description}" + (f"  ({detail})" if detail and not passed else ""))


def flagged(review, text, reasons):
    return any(text.lower() in item["raw_input"].lower() and item["reason"] in reasons for item in review)


def main():
    try:
        clean = json.loads((HERE / "clean_roster.json").read_text(encoding="utf-8"))
        review = json.loads((HERE / "review_queue.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit("Run `python intake_agent.py` first to create the output files.")

    print("Rules that must always hold")
    invalid = [r["record_id"] for r in clean
               if not validate({k: v for k, v in r.items() if k != "record_id"})["valid"]]
    check("every committed record passes validation", not invalid, f"invalid: {invalid}")
    keys = [(r["species_code"], r["date"], r["location"].strip().lower()) for r in clean]
    check("no sighting is on the roster twice", len(keys) == len(set(keys)))
    check("every committed record is a single species",
          all(BY_CODE[r["species_code"]]["category"] == "species" for r in clean))
    check("names match the taxonomy",
          all(BY_CODE[r["species_code"]]["comName"] == r["common_name"] for r in clean))
    names = {r["common_name"] for r in clean}
    check("no invented species on the roster", "Snowy Owl" not in names and not any("Gryphon" in n for n in names))

    print("\nExpected handling of the tricky notes")
    check("the made-up 'Marsh Gryphon Wren' is flagged unknown_species",
          flagged(review, "Gryphon", {"unknown_species"}))
    check("'some kind of gull' is flagged species_group", flagged(review, "gull", {"species_group"}))
    check("'a couple of hawks' is flagged species_group", flagged(review, "hawk", {"species_group"}))
    check("the Canada geese logged twice are caught as a possible duplicate",
          any(item["reason"] == "possible_duplicate" for item in review)
          and sum(r["species_code"] == "cangoo" for r in clean) == 1)
    check("the crows with no location are not on the roster", "American Crow" not in names)
    check("the zero-count titmouse is not on the roster", "Tufted Titmouse" not in names)
    check("the August house sparrows are not on the roster", "House Sparrow" not in names)

    print("\nTotals (a small range is allowed)")
    check(f"committed records between 20 and 23 (got {len(clean)})", 20 <= len(clean) <= 23)
    check(f"review items between 10 and 14 (got {len(review)})", 10 <= len(review) <= 14)

    print(f"\n{sum(results)} of {len(results)} checks passed.")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
