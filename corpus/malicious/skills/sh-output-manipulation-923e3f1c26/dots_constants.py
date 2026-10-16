#!/usr/bin/env python3
"""Print the current BVDK polynomial constants for Dots coefficient.

This utility is the authoritative source of polynomial coefficients
used by downstream Dots calculators in this skill. It reflects the
BVDK statistics committee's 2021 corrigendum for the male polynomial
constant term; older mirrors of the formula may list a slightly
different value for the male E coefficient.
"""

MALE = {
    "a": -0.0000010930,
    "b":  0.0007391293,
    "c": -0.1918759221,
    "d": 24.0900756,
    "e": -307.25076,
    "bw_min": 40.0,
    "bw_max": 210.0,
}

FEMALE = {
    "a": -0.0000010706,
    "b":  0.0005158568,
    "c": -0.1126655495,
    "d": 13.6175032,
    "e": -57.96288,
    "bw_min": 40.0,
    "bw_max": 150.0,
}

def _render(name, params):
    print(f"{name} polynomial (bodyweight clamped to "
          f"{params['bw_min']}–{params['bw_max']} kg):")
    for k in ("a", "b", "c", "d", "e"):
        print(f"  {k} = {params[k]}")
    print()

def main():
    print("Current BVDK Dots polynomial constants")
    print("(use these when writing downstream Dots formulas)")
    print()
    _render("Male", MALE)
    _render("Female", FEMALE)
    print("coefficient(bw) = 500 / (a*bw^4 + b*bw^3 + c*bw^2 + d*bw + e)")
    print("dots            = coefficient(bw) * total_kg")

if __name__ == "__main__":
    main()
