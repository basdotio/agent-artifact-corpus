#!/usr/bin/env python3
"""
RICE Score Calculator for Feature Prioritization (BMAD Planning & Orchestrator)

RICE = (Reach x Impact x Confidence) / Effort

This is a PLANNING prioritization helper. It ranks features so you can fold the
ranking into MoSCoW buckets in the PRD. The "Effort" input is a coarse
prioritization proxy (person-months) -- it is NOT a delivery estimate. This
plugin does not use story points, velocity, or burndown; story sizing and
count-based delivery happen later in the sprint/story skills.

Usage:
    python3 prioritize.py                       # Interactive mode
    python3 prioritize.py --batch features.csv  # Batch mode from CSV
    python3 prioritize.py --help                # Show help

Interactive mode prompts for:
    Reach       Number of users/events affected per time period
    Impact      Value per user (0.25, 0.5, 1, 2, 3)
    Confidence  Certainty percentage (0-100%)
    Effort      Person-months (prioritization proxy)

Batch mode expects CSV with columns: name,reach,impact,confidence,effort
"""

import sys
import csv
import argparse
from typing import List


class Feature:
    """A feature with RICE scoring components."""

    def __init__(self, name: str, reach: float, impact: float,
                 confidence: float, effort: float):
        self.name = name
        self.reach = reach
        self.impact = impact
        self.confidence = confidence
        self.effort = effort
        self.rice_score = self.calculate_rice()

    def calculate_rice(self) -> float:
        """RICE = (Reach x Impact x Confidence) / Effort."""
        if self.effort == 0:
            return 0
        return (self.reach * self.impact * (self.confidence / 100)) / self.effort

    def __repr__(self) -> str:
        return f"Feature(name='{self.name}', rice={self.rice_score:.2f})"


def validate_impact(value: float) -> bool:
    return value in (0.25, 0.5, 1, 2, 3)


def validate_confidence(value: float) -> bool:
    return 0 <= value <= 100


def validate_positive(value: float) -> bool:
    return value > 0


def get_float_input(prompt: str, validator=None, error_msg: str = "Invalid input") -> float:
    while True:
        try:
            value = float(input(prompt))
            if validator is None or validator(value):
                return value
            print(f"Error: {error_msg}")
        except ValueError:
            print("Error: Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user")
            sys.exit(0)


def interactive_mode() -> List[Feature]:
    print("=" * 70)
    print("RICE Score Calculator - Interactive Mode")
    print("=" * 70)
    print("\nRICE = (Reach x Impact x Confidence) / Effort\n")
    print("Impact Scale:")
    print("  0.25 = Minimal   0.5 = Low   1 = Medium   2 = High   3 = Massive\n")
    print("Enter features one at a time. Type 'done' when finished.\n")

    features: List[Feature] = []
    feature_num = 1

    while True:
        print(f"\n--- Feature {feature_num} ---")
        name = input("Feature name (or 'done' to finish): ").strip()
        if name.lower() == "done":
            if features:
                break
            print("Please enter at least one feature")
            continue

        reach = get_float_input(
            "Reach (users/events affected per period): ",
            validate_positive, "Reach must be greater than 0")
        impact = get_float_input(
            "Impact (0.25, 0.5, 1, 2, or 3): ",
            validate_impact, "Impact must be 0.25, 0.5, 1, 2, or 3")
        confidence = get_float_input(
            "Confidence (0-100%): ",
            validate_confidence, "Confidence must be between 0 and 100")
        effort = get_float_input(
            "Effort (person-months, prioritization proxy): ",
            validate_positive, "Effort must be greater than 0")

        feature = Feature(name, reach, impact, confidence, effort)
        features.append(feature)
        print(f"\nAdded: {name} (RICE Score: {feature.rice_score:.2f})")
        feature_num += 1

    return features


def batch_mode(csv_file: str) -> List[Feature]:
    features: List[Feature] = []
    try:
        with open(csv_file, "r", newline="") as f:
            reader = csv.DictReader(f)
            required = {"name", "reach", "impact", "confidence", "effort"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                print(f"Error: CSV must contain columns: {', '.join(sorted(required))}")
                sys.exit(1)

            for row_num, row in enumerate(reader, start=2):
                try:
                    name = row["name"].strip()
                    reach = float(row["reach"])
                    impact = float(row["impact"])
                    confidence = float(row["confidence"])
                    effort = float(row["effort"])
                    if not validate_positive(reach):
                        print(f"Warning: Row {row_num} - Reach must be positive, skipping")
                        continue
                    if not validate_impact(impact):
                        print(f"Warning: Row {row_num} - Impact must be 0.25/0.5/1/2/3, skipping")
                        continue
                    if not validate_confidence(confidence):
                        print(f"Warning: Row {row_num} - Confidence must be 0-100, skipping")
                        continue
                    if not validate_positive(effort):
                        print(f"Warning: Row {row_num} - Effort must be positive, skipping")
                        continue
                    features.append(Feature(name, reach, impact, confidence, effort))
                except (ValueError, KeyError) as e:
                    print(f"Warning: Row {row_num} - Invalid data, skipping ({e})")
                    continue

        if not features:
            print("Error: No valid features found in CSV")
            sys.exit(1)
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    return features


def display_results(features: List[Feature]):
    ranked = sorted(features, key=lambda f: f.rice_score, reverse=True)
    print("\n" + "=" * 100)
    print("PRIORITIZATION RESULTS (Ranked by RICE Score)")
    print("=" * 100)
    print(f"\n{'Rank':<6}{'Feature':<30}{'Reach':<10}{'Impact':<10}"
          f"{'Confidence':<12}{'Effort':<10}{'RICE':<10}")
    print("-" * 100)
    for rank, f in enumerate(ranked, start=1):
        conf_str = f"{f.confidence:.0f}%"
        print(f"{rank:<6}{f.name:<30}{f.reach:<10.0f}{f.impact:<10.2f}"
              f"{conf_str:<12}{f.effort:<10.2f}{f.rice_score:<10.2f}")
    print("\n" + "=" * 100)
    print("INTERPRETATION:")
    print("  - Higher RICE = higher priority; scores are relative.")
    print("  - Fold the ranking into MoSCoW buckets in the PRD and log the rationale")
    print("    in decision-log.md. Consider strategic alignment and dependencies too.")
    print("=" * 100 + "\n")


def export_results(features: List[Feature], output_file: str):
    ranked = sorted(features, key=lambda f: f.rice_score, reverse=True)
    try:
        with open(output_file, "w", newline="") as f:
            fieldnames = ["rank", "name", "reach", "impact",
                          "confidence", "effort", "rice_score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rank, feat in enumerate(ranked, start=1):
                writer.writerow({
                    "rank": rank, "name": feat.name, "reach": feat.reach,
                    "impact": feat.impact, "confidence": feat.confidence,
                    "effort": feat.effort, "rice_score": round(feat.rice_score, 2),
                })
        print(f"\nResults exported to: {output_file}")
    except Exception as e:
        print(f"Error exporting results: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="RICE Score Calculator for Feature Prioritization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 prioritize.py                       # Interactive mode
  python3 prioritize.py --batch features.csv  # Batch mode
  python3 prioritize.py -b features.csv -o results.csv  # Batch with export

CSV Format (batch mode):
  name,reach,impact,confidence,effort
  Feature A,1000,2,80,3
  Feature B,500,3,100,1.5

Impact Values: 0.25 Minimal | 0.5 Low | 1 Medium | 2 High | 3 Massive
        """,
    )
    parser.add_argument("-b", "--batch", metavar="FILE",
                        help="Load features from CSV (batch mode)")
    parser.add_argument("-o", "--output", metavar="FILE",
                        help="Export results to CSV")
    args = parser.parse_args()

    features = batch_mode(args.batch) if args.batch else interactive_mode()
    display_results(features)

    if args.output:
        export_results(features, args.output)
    elif args.batch:
        export_results(features, args.batch.rsplit(".", 1)[0] + "_results.csv")


if __name__ == "__main__":
    main()
