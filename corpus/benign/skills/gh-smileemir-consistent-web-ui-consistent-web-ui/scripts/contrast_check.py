#!/usr/bin/env python3
"""WCAG 2.x contrast checker for design tokens - standard library only, Python 3.8+.

Reads one or more CSS files, finds the root-level custom properties of every
theme (base :root / html / @theme, plus variants such as [data-theme="dark"],
.dark, .theme-x, [data-bs-theme=...] and @media (prefers-color-scheme: dark)),
resolves var() chains and checks foreground/background pairs in each theme.

Colour syntax: hex, rgb()/rgba(), hsl()/hsla(), hwb(), lab(), lch(), oklab(),
oklch(), named colours, transparent, light-dark(), color-mix() in srgb / oklab /
oklch, and bare channel values such as "0 0% 100%" or "255, 255, 255" that
are used as hsl(var(--x)) or rgb(var(--x)). Wide-gamut values are clipped to
sRGB. Translucent foregrounds are composited over their background; a
translucent background is composited over --canvas (default white).

Examples
  contrast_check.py --pair "#767676" "#ffffff"
  contrast_check.py --css app/globals.css --pairs contrast-pairs.json
  contrast_check.py --css theme.css --pairs auto          # guess pairs from token names
  contrast_check.py --css theme.css --list-themes

Exit status: 0 all pass, 1 a pair fails or cannot be resolved, 2 usage error.
This checks the contrast formula only. Text size, weight, state layers and
images behind text still need a visual check on the real screen.
"""
import argparse
import colorsys
import json
import math
import re
import sys

NAMED = dict(item.split(":") for item in (
    "aliceblue:f0f8ff antiquewhite:faebd7 aqua:00ffff aquamarine:7fffd4 azure:f0ffff beige:f5f5dc "
    "bisque:ffe4c4 black:000000 blanchedalmond:ffebcd blue:0000ff blueviolet:8a2be2 brown:a52a2a "
    "burlywood:deb887 cadetblue:5f9ea0 chartreuse:7fff00 chocolate:d2691e coral:ff7f50 "
    "cornflowerblue:6495ed cornsilk:fff8dc crimson:dc143c cyan:00ffff darkblue:00008b darkcyan:008b8b "
    "darkgoldenrod:b8860b darkgray:a9a9a9 darkgreen:006400 darkgrey:a9a9a9 darkkhaki:bdb76b "
    "darkmagenta:8b008b darkolivegreen:556b2f darkorange:ff8c00 darkorchid:9932cc darkred:8b0000 "
    "darksalmon:e9967a darkseagreen:8fbc8f darkslateblue:483d8b darkslategray:2f4f4f "
    "darkslategrey:2f4f4f darkturquoise:00ced1 darkviolet:9400d3 deeppink:ff1493 deepskyblue:00bfff "
    "dimgray:696969 dimgrey:696969 dodgerblue:1e90ff firebrick:b22222 floralwhite:fffaf0 "
    "forestgreen:228b22 fuchsia:ff00ff gainsboro:dcdcdc ghostwhite:f8f8ff gold:ffd700 "
    "goldenrod:daa520 gray:808080 green:008000 greenyellow:adff2f grey:808080 honeydew:f0fff0 "
    "hotpink:ff69b4 indianred:cd5c5c indigo:4b0082 ivory:fffff0 khaki:f0e68c lavender:e6e6fa "
    "lavenderblush:fff0f5 lawngreen:7cfc00 lemonchiffon:fffacd lightblue:add8e6 lightcoral:f08080 "
    "lightcyan:e0ffff lightgoldenrodyellow:fafad2 lightgray:d3d3d3 lightgreen:90ee90 "
    "lightgrey:d3d3d3 lightpink:ffb6c1 lightsalmon:ffa07a lightseagreen:20b2aa lightskyblue:87cefa "
    "lightslategray:778899 lightslategrey:778899 lightsteelblue:b0c4de lightyellow:ffffe0 "
    "lime:00ff00 limegreen:32cd32 linen:faf0e6 magenta:ff00ff maroon:800000 "
    "mediumaquamarine:66cdaa mediumblue:0000cd mediumorchid:ba55d3 mediumpurple:9370db "
    "mediumseagreen:3cb371 mediumslateblue:7b68ee mediumspringgreen:00fa9a "
    "mediumturquoise:48d1cc mediumvioletred:c71585 midnightblue:191970 mintcream:f5fffa "
    "mistyrose:ffe4e1 moccasin:ffe4b5 navajowhite:ffdead navy:000080 oldlace:fdf5e6 olive:808000 "
    "olivedrab:6b8e23 orange:ffa500 orangered:ff4500 orchid:da70d6 palegoldenrod:eee8aa "
    "palegreen:98fb98 paleturquoise:afeeee palevioletred:db7093 papayawhip:ffefd5 "
    "peachpuff:ffdab9 peru:cd853f pink:ffc0cb plum:dda0dd powderblue:b0e0e6 purple:800080 "
    "rebeccapurple:663399 red:ff0000 rosybrown:bc8f8f royalblue:4169e1 saddlebrown:8b4513 "
    "salmon:fa8072 sandybrown:f4a460 seagreen:2e8b57 seashell:fff5ee sienna:a0522d silver:c0c0c0 "
    "skyblue:87ceeb slateblue:6a5acd slategray:708090 slategrey:708090 snow:fffafa "
    "springgreen:00ff7f steelblue:4682b4 tan:d2b48c teal:008080 thistle:d8bfd8 tomato:ff6347 "
    "turquoise:40e0d0 violet:ee82ee wheat:f5deb3 white:ffffff whitesmoke:f5f5f5 yellow:ffff00 "
    "yellowgreen:9acd32").split())

COMMENT = re.compile(r"/\*.*?\*/", re.S)
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*)?")
MARKER_ATTR = re.compile(r"\[data-(?:theme|bs-theme|mode|color-scheme|color-mode)\s*=\s*[\"']?([\w-]+)[\"']?\s*\]")
MARKER_CLASS = re.compile(r"(?<![\w-])\.(dark|light)(?![\w-])|(?<![\w-])\.theme-([\w-]+)")
ROOTISH = re.compile(r"^(?::root|html|:host|body|\*)?$")
TRANSPARENT_AT = ("@layer", "@supports", "@theme", "@scope", "@container")


# --------------------------------------------------------------------------- #
# CSS reading
# --------------------------------------------------------------------------- #
def matching_brace(text, start):
    depth, i = 1, start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return i


def top_level_decls(body):
    decls, depth, current = {}, 0, []
    for ch in body + ";":
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                current = []
            continue
        if depth:
            continue
        if ch == ";":
            text = "".join(current).strip()
            current = []
            if text.startswith("--") and ":" in text:
                name, value = text.split(":", 1)
                decls[name.strip()] = re.sub(r"\s*!important\s*$", "", value.strip())
        else:
            current.append(ch)
    return decls


def css_rules(css):
    """Yield (conditions, selector, custom-property dict) for every rule."""
    out = []

    def walk(text, conditions, parent):
        i, last = 0, 0
        while i < len(text):
            if text[i] != "{":
                i += 1
                continue
            prelude = text[last:i].split(";")[-1].split("}")[-1].strip()
            end = matching_brace(text, i + 1)
            body = text[i + 1:end - 1]
            if prelude.startswith("@"):
                if prelude.startswith("@media") or prelude.startswith(TRANSPARENT_AT):
                    if prelude.startswith("@theme"):
                        out.append((conditions, ":root", top_level_decls(body)))
                    walk(body, conditions + [prelude], parent)
            else:
                selector = (parent + " " + prelude.replace("&", "")).strip() if parent else prelude
                out.append((conditions, selector, top_level_decls(body)))
                if "{" in body:
                    walk(body, conditions, selector)
            i = last = end
    walk(COMMENT.sub(" ", css), [], "")
    return out


def theme_of(conditions, selector):
    """Return a theme name ('base' or variant) or None when the rule is not theme-level."""
    names = []
    for cond in conditions:
        if cond.startswith("@media"):
            scheme = re.search(r"prefers-color-scheme\s*:\s*(dark|light)", cond)
            if not scheme:
                return None
            names.append(scheme.group(1) + " (system)")
    parts = []
    for piece in selector.split(","):
        clean = re.sub(r":not\([^)]*\)", "", piece).strip()
        markers = [m for m in MARKER_ATTR.findall(clean)]
        markers += [a or b for a, b in MARKER_CLASS.findall(clean)]
        rest = MARKER_CLASS.sub("", MARKER_ATTR.sub("", clean)).strip()
        if not ROOTISH.match(rest):
            continue
        parts.append(markers)
    if not parts:
        return None
    markers = parts[0]
    if names and not markers:
        return names[0]
    if markers:
        return markers[0]
    return "base"


def load_themes(paths):
    themes = {"base": {}}
    origin = {}
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as handle:
            css = handle.read()
        for conditions, selector, decls in css_rules(css):
            if not decls:
                continue
            name = theme_of(conditions, selector)
            if name is None:
                continue
            themes.setdefault(name, {}).update(decls)
            origin.setdefault(name, selector if not conditions else " ".join(conditions) + " " + selector)
    resolved = {"base": dict(themes["base"])}
    for name, overrides in themes.items():
        if name != "base":
            merged = dict(themes["base"])
            merged.update(overrides)
            resolved[name] = merged
    return resolved, themes, origin


# --------------------------------------------------------------------------- #
# Colour parsing
# --------------------------------------------------------------------------- #
def split_args(text):
    parts, depth, current = [], 0, []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    parts.append("".join(current).strip())
    return parts


def substitute(value, tokens, depth=0):
    """Replace var() references textually (with fallbacks); None if unresolved."""
    if depth > 24:
        return None
    out, i = [], 0
    while True:
        m = VAR.search(value, i)
        if not m:
            out.append(value[i:])
            break
        out.append(value[i:m.start()])
        end = matching_paren(value, m.start() + 4)
        inner = value[m.start() + 4:end - 1]
        args = split_args(inner)
        name = args[0].strip()
        fallback = ",".join(args[1:]).strip() if len(args) > 1 else None
        if name in tokens:
            replacement = substitute(tokens[name], tokens, depth + 1)
        elif fallback:
            replacement = substitute(fallback, tokens, depth + 1)
        else:
            replacement = None
        if replacement is None:
            return None
        out.append(replacement)
        i = end
    return "".join(out)


def matching_paren(text, start):
    depth, i = 1, start
    while i < len(text) and depth:
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
        i += 1
    return i


def number(token, scale=1.0, percent_scale=None):
    token = token.strip()
    if token in ("none", ""):
        return 0.0
    if token.endswith("%"):
        return float(token[:-1]) / 100 * (percent_scale if percent_scale is not None else scale)
    return float(token) * (1 if scale == 1.0 else 1)


def hue(token):
    token = token.strip()
    if token == "none":
        return 0.0
    for unit, factor in (("deg", 1.0), ("grad", 0.9), ("rad", 180 / math.pi), ("turn", 360.0)):
        if token.endswith(unit):
            return float(token[:-len(unit)]) * factor
    return float(token)


def channels(args_text):
    """Split modern/legacy function arguments into channel tokens and alpha token."""
    text = args_text.replace(",", " ")
    alpha = None
    if "/" in text:
        text, alpha = text.split("/", 1)
        alpha = alpha.strip()
    parts = text.split()
    if alpha is None and len(parts) == 4:
        alpha = parts.pop()
    return parts, alpha


def alpha_value(token):
    if token is None:
        return 1.0
    token = token.strip()
    return float(token[:-1]) / 100 if token.endswith("%") else float(token)


def clip(x):
    return min(1.0, max(0.0, x))


def linear_to_srgb(c):
    c = clip(c)
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklab_to_srgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(bl)


def srgb_to_oklab(r, g, b):
    r, g, b = srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def lab_to_srgb(L, a, b):
    kappa, eps = 24389 / 27, 216 / 24389
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200
    xr = fx ** 3 if fx ** 3 > eps else (116 * fx - 16) / kappa
    yr = ((L + 16) / 116) ** 3 if L > kappa * eps else L / kappa
    zr = fz ** 3 if fz ** 3 > eps else (116 * fz - 16) / kappa
    X, Y, Z = xr * 0.96422, yr, zr * 0.82521
    X, Y, Z = (0.9554734527042182 * X - 0.023098536874261423 * Y + 0.0632593086610217 * Z,
               -0.028369706963208136 * X + 1.0099954580058226 * Y + 0.021041398966943008 * Z,
               0.012314001688319899 * X - 0.020507696433477912 * Y + 1.3303659366080753 * Z)
    r = 3.2409699419045226 * X - 1.537383177570094 * Y - 0.4986107602930034 * Z
    g = -0.9692436362808796 * X + 1.8759675015077202 * Y + 0.04155505740717559 * Z
    bl = 0.05563007969699366 * X - 0.20397695888897652 * Y + 1.0569715142428786 * Z
    return linear_to_srgb(r), linear_to_srgb(g), linear_to_srgb(bl)


def parse_color(value, scheme="light"):
    """Return (r, g, b, a) with sRGB channels in 0..1, or None."""
    if value is None:
        return None
    v = value.strip().lower()
    if not v:
        return None
    if v == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    if v in NAMED:
        v = "#" + NAMED[v]
    if v.startswith("#"):
        h = v[1:]
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) not in (6, 8) or not re.fullmatch(r"[0-9a-f]+", h):
            return None
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return (rgb[0], rgb[1], rgb[2], int(h[6:8], 16) / 255 if len(h) == 8 else 1.0)
    fn = re.match(r"^([a-z-]+)\((.*)\)$", v, re.S)
    try:
        if fn:
            name, inner = fn.group(1), fn.group(2)
            if name == "light-dark":
                light, dark = split_args(inner)[:2]
                return parse_color(dark if scheme == "dark" else light, scheme)
            if name == "color-mix":
                return color_mix(inner, scheme)
            parts, alpha = channels(inner)
            a = alpha_value(alpha)
            if name in ("rgb", "rgba"):
                rgb = [number(p) / (1 if p.strip().endswith("%") else 255) for p in parts[:3]]
                return (clip(rgb[0]), clip(rgb[1]), clip(rgb[2]), a)
            if name in ("hsl", "hsla"):
                r, g, b = colorsys.hls_to_rgb((hue(parts[0]) % 360) / 360, number(parts[2], percent_scale=1),
                                              number(parts[1], percent_scale=1))
                return (r, g, b, a)
            if name == "hwb":
                w, bk = number(parts[1], percent_scale=1), number(parts[2], percent_scale=1)
                if w + bk >= 1:
                    gray = w / (w + bk)
                    return (gray, gray, gray, a)
                r, g, b = colorsys.hls_to_rgb((hue(parts[0]) % 360) / 360, 0.5, 1.0)
                return tuple(c * (1 - w - bk) + w for c in (r, g, b)) + (a,)
            if name in ("oklab", "oklch"):
                L = number(parts[0], percent_scale=1)
                if name == "oklab":
                    aa, bb = number(parts[1], percent_scale=0.4), number(parts[2], percent_scale=0.4)
                else:
                    c, h = number(parts[1], percent_scale=0.4), math.radians(hue(parts[2]))
                    aa, bb = c * math.cos(h), c * math.sin(h)
                return oklab_to_srgb(L, aa, bb) + (a,)
            if name in ("lab", "lch"):
                L = number(parts[0], percent_scale=100)
                if name == "lab":
                    aa, bb = number(parts[1], percent_scale=125), number(parts[2], percent_scale=125)
                else:
                    c, h = number(parts[1], percent_scale=150), math.radians(hue(parts[2]))
                    aa, bb = c * math.cos(h), c * math.sin(h)
                return lab_to_srgb(L, aa, bb) + (a,)
            return None
        # bare channels, e.g. "0 0% 100%" (hsl) or "255, 255, 255" (rgb)
        parts, alpha = channels(v)
        if len(parts) == 3:
            if parts[1].endswith("%") and parts[2].endswith("%"):
                return parse_color("hsl(%s %s %s / %s)" % (parts[0], parts[1], parts[2], alpha or "1"), scheme)
            if all(re.fullmatch(r"\d{1,3}(\.\d+)?", p) for p in parts):
                return parse_color("rgb(%s %s %s / %s)" % (parts[0], parts[1], parts[2], alpha or "1"), scheme)
    except (ValueError, IndexError, ZeroDivisionError):
        return None
    return None


def color_mix(inner, scheme):
    args = split_args(inner)
    if len(args) != 3:
        return None
    space = args[0].replace("in", "", 1).strip().split()[0]
    items = []
    for arg in args[1:]:
        m = re.search(r"\s(\d*\.?\d+)%\s*$", " " + arg)
        pct = float(m.group(1)) / 100 if m else None
        color = parse_color(arg[:m.start() - 1] if m else arg, scheme)
        if color is None:
            return None
        items.append((color, pct))
    (c1, p1), (c2, p2) = items
    if p1 is None and p2 is None:
        p1, p2 = 0.5, 0.5
    elif p1 is None:
        p1 = 1 - p2
    elif p2 is None:
        p2 = 1 - p1
    total = p1 + p2
    if total <= 0:
        return None
    w2 = p2 / total
    alpha = c1[3] * (1 - w2) + c2[3] * w2
    if space in ("oklab", "oklch"):
        a1, a2 = srgb_to_oklab(*c1[:3]), srgb_to_oklab(*c2[:3])
        if space == "oklch":
            (L1, A1, B1), (L2, A2, B2) = a1, a2
            C1, C2 = math.hypot(A1, B1), math.hypot(A2, B2)
            H1, H2 = math.atan2(B1, A1), math.atan2(B2, A2)
            d = (H2 - H1 + math.pi) % (2 * math.pi) - math.pi
            L, C, H = L1 + (L2 - L1) * w2, C1 + (C2 - C1) * w2, H1 + d * w2
            rgb = oklab_to_srgb(L, C * math.cos(H), C * math.sin(H))
        else:
            rgb = oklab_to_srgb(*[x + (y - x) * w2 for x, y in zip(a1, a2)])
    else:
        rgb = tuple(x + (y - x) * w2 for x, y in zip(c1[:3], c2[:3]))
    if total < 1:
        alpha *= total
    return rgb + (alpha,)


# --------------------------------------------------------------------------- #
# Contrast
# --------------------------------------------------------------------------- #
def luminance(rgb):
    r, g, b = (srgb_to_linear(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def composite(top_color, bottom):
    a = top_color[3]
    return tuple(t * a + b * (1 - a) for t, b in zip(top_color[:3], bottom[:3])) + (1.0,)


def contrast(fg, bg):
    l1, l2 = luminance(fg), luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def to_hex(color):
    return "#" + "".join("%02x" % round(clip(c) * 255) for c in color[:3])


def resolve(ref, tokens, scheme):
    """ref is a token name (--x, or x when --x exists and x is not a colour) or a literal colour."""
    if not ref.startswith("--") and parse_color(ref, scheme) is None and ("--" + ref) in tokens:
        ref = "--" + ref
    raw = tokens.get(ref) if ref.startswith("--") else ref
    if ref.startswith("--") and raw is None:
        return None, "token not defined at root level"
    text = substitute(raw, tokens)
    if text is None:
        return None, "var() chain cannot be resolved"
    color = parse_color(text, scheme)
    if color is None:
        return None, "unsupported colour value: " + text.strip()[:60]
    return color, None


def evaluate(pairs, themes, canvas_ref):
    results = []
    for theme, tokens in themes.items():
        scheme = "dark" if "dark" in theme else "light"
        canvas, _ = resolve(canvas_ref, tokens, scheme) if canvas_ref else ((1, 1, 1, 1), None)
        canvas = canvas if canvas and canvas[3] == 1 else (1.0, 1.0, 1.0, 1.0)
        for pair in pairs:
            row = {"theme": theme, "use": pair.get("use", ""), "fg": pair["fg"], "bg": pair["bg"],
                   "min": float(pair.get("min", 3.0 if pair.get("large") else 4.5))}
            fg, err_fg = resolve(pair["fg"], tokens, scheme)
            bg, err_bg = resolve(pair["bg"], tokens, scheme)
            if fg is None or bg is None:
                row.update(status="UNRESOLVED", reason=err_fg or err_bg)
                results.append(row)
                continue
            notes = []
            if bg[3] < 1:
                bg = composite(bg, canvas)
                notes.append("background composited over canvas")
            if fg[3] < 1:
                fg = composite(fg, bg)
                notes.append("foreground alpha composited")
            ratio = contrast(fg, bg)
            row.update(status="PASS" if ratio >= row["min"] else "FAIL", ratio=round(ratio, 2),
                       fg_hex=to_hex(fg), bg_hex=to_hex(bg), notes=notes)
            results.append(row)
    return results


# --------------------------------------------------------------------------- #
# Pair suggestion from token names
# --------------------------------------------------------------------------- #
TEXTY = re.compile(r"(?:^|-)(?:text|fg|foreground|ink|content|heading|body|copy|label|link)(?:-|$)")
BGISH = re.compile(r"(?:^|-)(?:bg|background|surface|canvas|paper|base|page|card|popover|panel)(?:-|$)")


ALIAS = re.compile(r"^\s*var\(\s*(--[\w-]+)\s*\)\s*$")


def suggest_pairs(tokens):
    """Guess text/background pairs from common naming conventions (confirm before relying on them)."""
    names = [n for n in tokens if parse_color(substitute(tokens[n], tokens) or "") is not None]
    # a token that is only var(--other) duplicates --other; keep the source token
    names = [n for n in names if not (ALIAS.match(tokens[n]) and ALIAS.match(tokens[n]).group(1) in tokens)]
    nameset = set(names)
    pairs, seen = [], set()

    def add(fg, bg, use):
        if fg in nameset and bg in nameset and (fg, bg) not in seen and fg != bg:
            seen.add((fg, bg))
            pairs.append({"fg": fg, "bg": bg, "use": use, "min": 4.5})

    for n in names:
        core = n[2:]
        if core.endswith("-foreground"):
            add(n, "--" + core[:-len("-foreground")], "text on " + core[:-len("-foreground")])
        if core.endswith("-fg"):
            add(n, "--" + core[:-3] + "-bg", "text on " + core[:-3])
            add(n, "--" + core[:-3], "text on " + core[:-3])
        if "on-" in core:
            base = core.replace("on-", "", 1)
            add(n, "--" + base, "text on " + base)
        if core.endswith("-text"):
            add(n, "--" + core[:-5] + "-bg", "text on " + core[:-5])
            add(n, "--" + core[:-5] + "-background", "text on " + core[:-5])
    primary_bg = [n for n in names if BGISH.search(n[2:]) and not TEXTY.search(n[2:])]
    main_bg = [n for n in primary_bg if re.search(r"(?:^|-)(?:bg|background|canvas|surface|page|base)$", n[2:])]
    texts = [n for n in names if TEXTY.search(n[2:]) and not n[2:].endswith("-foreground")]
    for fg in texts[:12]:
        for bg in (main_bg or primary_bg)[:3]:
            add(fg, bg, "text on page")
    if "--foreground" in nameset and "--background" in nameset:
        add("--foreground", "--background", "body text")
    return pairs


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def render(results, guessed=False, only_failures=False):
    lines, current = [], None
    for row in results:
        if only_failures and row["status"] == "PASS":
            continue
        if row["theme"] != current:
            current = row["theme"]
            lines.append("Theme: " + current)
        if row["status"] == "UNRESOLVED":
            lines.append("  UNRESOLVED  %-28s %s on %s - %s" % (row["use"][:28], row["fg"], row["bg"], row["reason"]))
            continue
        sign = ">=" if row["status"] == "PASS" else "< "
        note = (" (" + "; ".join(row["notes"]) + ")") if row["notes"] else ""
        refs = "%s on %s" % (row["fg"], row["bg"])
        values = "%s on %s" % (row["fg_hex"], row["bg_hex"])
        shown = values if refs.lower() == values.lower() or not (row["fg"].startswith("--") or row["bg"].startswith("--")) \
            else refs + "  " + values
        lines.append("  %-4s %6.2f:1 %s %-4g %-28s %s%s" % (
            row["status"], row["ratio"], sign, row["min"], row["use"][:28], shown, note))
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "UNRESOLVED")}
    lines.append("Summary: %(PASS)d pass, %(FAIL)d fail, %(UNRESOLVED)d unresolved" % counts)
    if guessed:
        lines.append("Pairs were guessed from token names: confirm each one matches real text/background use.")
    return "\n".join(lines), counts


def take_pairs(argv):
    """Pull '--pair FG BG' out before argparse, because token names start with '--'."""
    pairs, rest, i = [], [], 0
    while i < len(argv):
        if argv[i] == "--pair":
            if i + 2 >= len(argv):
                raise IndexError("--pair needs FG and BG")
            pairs.append((argv[i + 1], argv[i + 2]))
            i += 3
        else:
            rest.append(argv[i])
            i += 1
    return pairs, rest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        literal_pairs, argv = take_pairs(argv)
    except IndexError:
        print("contrast_check.py: error: --pair needs FG and BG", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description="WCAG 2.x contrast check for colours and CSS tokens")
    parser.add_argument("--css", action="append", default=[], help="CSS file with theme tokens; repeatable")
    parser.add_argument("--pairs", help="JSON file {\"pairs\": [{fg, bg, use, min|large}]} or 'auto'")
    parser.add_argument("--pair", nargs=2, action="append", default=[], metavar=("FG", "BG"),
                        help="Colour or token pair, e.g. --pair --text --surface; repeatable")
    parser.add_argument("--min", type=float, default=4.5, help="Minimum ratio for --pair (default 4.5)")
    parser.add_argument("--theme", action="append", default=[], help="Only check these theme names")
    parser.add_argument("--canvas", help="Token or colour under translucent backgrounds (default white)")
    parser.add_argument("--list-themes", action="store_true", help="List detected themes and exit")
    parser.add_argument("--suggest-pairs", action="store_true", help="Print guessed pairs as JSON and exit")
    parser.add_argument("--only-failures", action="store_true", help="Print only failing or unresolved pairs")
    parser.add_argument("--json", action="store_true", help="Emit JSON results")
    args = parser.parse_args(argv)

    try:
        themes, raw, origin = load_themes(args.css) if args.css else ({"base": {}}, {"base": {}}, {})
    except OSError as error:
        parser.error(str(error))
    if args.list_themes:
        for name in themes:
            print("%-18s %3d tokens  %s" % (name, len(raw.get(name, {})), origin.get(name, ":root")))
        return 0
    if args.suggest_pairs:
        print(json.dumps({"pairs": suggest_pairs(themes["base"])}, indent=1))
        return 0
    pairs = [{"fg": fg, "bg": bg, "use": "pair", "min": args.min} for fg, bg in literal_pairs]
    if args.pairs == "auto":
        pairs += suggest_pairs(themes["base"])
    elif args.pairs:
        try:
            with open(args.pairs, encoding="utf-8") as handle:
                pairs += json.load(handle)["pairs"]
        except (OSError, ValueError, KeyError) as error:
            parser.error("cannot read pairs file: %s" % error)
    if not pairs:
        parser.error("give --pair FG BG, --pairs FILE or --pairs auto")
    selected = {k: v for k, v in themes.items() if not args.theme or k in args.theme}
    if not args.css:
        selected = {"literal": {}}
    results = evaluate(pairs, selected, args.canvas)
    text, counts = render(results, guessed=args.pairs == "auto", only_failures=args.only_failures)
    print(json.dumps({"results": results, "summary": counts}, indent=1) if args.json else text)
    return 0 if counts["FAIL"] == 0 and counts["UNRESOLVED"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
