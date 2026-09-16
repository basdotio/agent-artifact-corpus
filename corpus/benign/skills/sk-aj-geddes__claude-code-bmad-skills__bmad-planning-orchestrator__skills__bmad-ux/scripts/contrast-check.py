#!/usr/bin/env python3
"""
Color Contrast Ratio Calculator -- bmad-ux planning skill
WCAG 2.1 compliance checker for design token color pairs.

Usage:
    python contrast-check.py #000000 #ffffff
    python contrast-check.py 000000 ffffff
    python contrast-check.py "#333" "#fff"

Run from the plugin root:
    python "${CLAUDE_PLUGIN_ROOT}/skills/bmad-ux/scripts/contrast-check.py" #fg #bg

Use this to verify color pairs before committing them to DESIGN.md.
"""

import sys


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    except (ValueError, IndexError):
        raise ValueError(f"Invalid hex color: #{hex_color}")


def relative_luminance(rgb):
    """
    Calculate relative luminance per WCAG formula.
    https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """
    r, g, b = rgb
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0
    r = r / 12.92 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(color1, color2):
    """
    Calculate contrast ratio between two colors.
    https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
    """
    lum1 = relative_luminance(hex_to_rgb(color1))
    lum2 = relative_luminance(hex_to_rgb(color2))
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def check_wcag_compliance(ratio):
    """Check WCAG 2.1 compliance levels."""
    return {
        'ratio': ratio,
        'aa_normal': ratio >= 4.5,
        'aa_large': ratio >= 3.0,
        'aaa_normal': ratio >= 7.0,
        'aaa_large': ratio >= 4.5,
        'ui_components': ratio >= 3.0,
    }


def print_results(color1, color2, results):
    """Print formatted results."""
    ratio = results['ratio']

    print("\n" + "=" * 70)
    print("               COLOR CONTRAST CHECKER  (bmad-ux planning)")
    print("=" * 70)
    print(f"\nForeground: {color1.upper()}")
    print(f"Background: {color2.upper()}")
    print(f"\nContrast Ratio: {ratio:.2f}:1")
    print("\n" + "-" * 70)
    print("WCAG 2.1 COMPLIANCE:")
    print("-" * 70)

    print("\nLevel AA:")
    print(f"  Normal text (< 18px):      {'PASS' if results['aa_normal'] else 'FAIL'} (requires 4.5:1)")
    print(f"  Large text (>= 18px):      {'PASS' if results['aa_large'] else 'FAIL'} (requires 3.0:1)")
    print(f"  UI Components:             {'PASS' if results['ui_components'] else 'FAIL'} (requires 3.0:1)")

    print("\nLevel AAA:")
    print(f"  Normal text (< 18px):      {'PASS' if results['aaa_normal'] else 'FAIL'} (requires 7.0:1)")
    print(f"  Large text (>= 18px):      {'PASS' if results['aaa_large'] else 'FAIL'} (requires 4.5:1)")

    print("\n" + "-" * 70)
    print("DESIGN.md VERDICT:")
    print("-" * 70)

    if results['aa_normal']:
        print("  This pair is APPROVED for all text sizes in DESIGN.md.")
    elif results['aa_large']:
        print("  APPROVED for large text only (>= 18px or bold >= 14px).")
        print("  Do NOT specify this pair for normal body text.")
    elif results['ui_components']:
        print("  APPROVED for UI components / graphics only. Not for text.")
    else:
        print("  REJECTED -- fails WCAG 2.1 AA. Adjust colors before committing to DESIGN.md.")

    if results['aaa_normal']:
        print("  Bonus: also meets WCAG 2.1 AAA (enhanced contrast).")

    print("\n" + "-" * 70)
    print("TEXT SIZE REFERENCE:")
    print("-" * 70)
    print("  Normal text:  < 18px (or < 14px bold)")
    print("  Large text:   >= 18px (or >= 14px bold)")
    print("\n" + "=" * 70 + "\n")


def suggest_improvements(color1, color2, results):
    """Suggest color adjustments if contrast is insufficient."""
    if results['aa_normal']:
        return

    ratio = results['ratio']

    print("SUGGESTIONS FOR DESIGN.md:")
    print("-" * 70)

    if ratio < 3.0:
        print("  Contrast is very low. Consider:")
        print("  1. Use a much darker foreground against this background")
        print("  2. Use a much lighter background under this foreground")
        print("  3. Add a contrasting border or outline")
        print("  4. Choose a different palette")
    elif ratio < 4.5:
        print("  Close to compliance. Small adjustments may resolve it:")
        print("  1. Darken the foreground color slightly")
        print("  2. Lighten the background color slightly")

    print("\n  Common safe pairs:")
    print("    Dark on light: #333333 on #FFFFFF = 12.63:1")
    print("    Light on dark: #FFFFFF on #333333 = 12.63:1")
    print(f"\n  Re-check: python contrast-check.py <new-fg> <new-bg>")
    print()


def main():
    if len(sys.argv) != 3:
        print("\n" + "=" * 70)
        print("               COLOR CONTRAST CHECKER  (bmad-ux planning)")
        print("=" * 70)
        print("\nUsage:")
        print("  python contrast-check.py <foreground> <background>")
        print("\nExamples:")
        print("  python contrast-check.py #000000 #ffffff")
        print("  python contrast-check.py 333 fff")
        print('  python contrast-check.py "#1a1a1a" "#f5f5f5"')
        print("\nNote: Both 3-digit and 6-digit hex codes are supported.")
        print("      The # symbol is optional.")
        print("\n" + "=" * 70 + "\n")
        sys.exit(1)

    color1 = sys.argv[1]
    color2 = sys.argv[2]

    try:
        hex_to_rgb(color1)
        hex_to_rgb(color2)

        ratio = contrast_ratio(color1, color2)
        results = check_wcag_compliance(ratio)

        print_results(color1, color2, results)
        suggest_improvements(color1, color2, results)

        sys.exit(0 if results['aa_normal'] else 1)

    except ValueError as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("Please provide valid hex colors (e.g., #000000 or 000 or #fff)\n", file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
