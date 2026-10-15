#!/usr/bin/env python3
"""Compare relative file names, sizes and SHA-256 between two local payload trees.

Python 3.9+, standard library. Does not extract or execute either payload.
Exit 0: identical, 1: differences, 2: invalid input/execution failure.
"""
import argparse
import sys
from grea.tools._artifact_common import directory, inventory, compare, validate_output, write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected")
    parser.add_argument("actual")
    parser.add_argument("--exclude", action="append", default=[], help="Relative glob, applied to BOTH trees; explicit exclusions are reported")
    parser.add_argument("--output", help="New JSON file outside both inputs; default stdout")
    args = parser.parse_args()
    try:
        expected, actual = directory(args.expected), directory(args.actual)
        if expected == actual or expected in actual.parents or actual in expected.parents:
            raise ValueError("Input trees must be distinct and non-nested")
        if args.output:
            validate_output(args.output, (expected, actual))
        report = compare(inventory(expected, args.exclude), inventory(actual, args.exclude))
        report.update(expected=str(expected), actual=str(actual), excluded_globs=args.exclude,
                      runtime_tested=False)
        write_report(report, args.output, (expected, actual))
        return 0 if report["equal"] else 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
