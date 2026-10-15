"""Historical pigments (approximate sRGB of the paint as it looks on the palette) and Palette."""

from dataclasses import dataclass

import numpy as np

from atelier.color import hex_to_linear, mix


@dataclass(frozen=True)
class Pigment:
    name: str
    hex: str
    note: str

    @property
    def linear(self):
        return hex_to_linear(self.hex)


PIGMENTS = {p.name: p for p in [
    Pigment("lead_white", "#EDE6D6", "Flake white; warm, flexible, the standard oil white until the 20th century."),
    Pigment("titanium_white", "#F6F6F2", "Modern (1920s) cool opaque white with very high tinting strength."),
    Pigment("zinc_white", "#F0F3F2", "Cool semi-transparent white (1834); clean tints and scumbles."),
    Pigment("ivory_black", "#262220", "Bone-char black; warm, fairly transparent, slow drying."),
    Pigment("lamp_black", "#1C1D1F", "Soot black; cool, opaque, overpowering in mixtures."),
    Pigment("raw_umber", "#5E4C3A", "Cool greenish-brown earth with manganese; fast drying, classic toned grounds."),
    Pigment("burnt_umber", "#563626", "Roasted umber; warm dark brown for underpainting and darks."),
    Pigment("raw_sienna", "#B07A35", "Transparent yellow-brown earth; warm glazes and flesh underlayers."),
    Pigment("burnt_sienna", "#9A4A2A", "Roasted sienna; transparent warm red-brown."),
    Pigment("yellow_ochre", "#C8963C", "Opaque natural earth yellow; muted and dependable since prehistory."),
    Pigment("red_ochre", "#A33B2E", "Venetian red earth; opaque, cool brick red."),
    Pigment("naples_yellow", "#EFCB7F", "Lead antimonate; pale opaque warm yellow for skies and flesh."),
    Pigment("lead_tin_yellow", "#EDD35B", "Opaque lemon yellow of the old masters (Vermeer), forgotten after 1750."),
    Pigment("cadmium_yellow", "#FAB80A", "Opaque brilliant warm yellow (1840s); Turner's and the Impressionists' sun."),
    Pigment("indian_yellow", "#E09B22", "Transparent glowing golden yellow; Turner's glaze for light."),
    Pigment("vermilion", "#E0402C", "Mercury sulfide; opaque scarlet, the old masters' red."),
    Pigment("madder_lake", "#A3203A", "Transparent crimson from madder root; glazes for shadows and drapery."),
    Pigment("cadmium_red", "#CF2A20", "Opaque modern red (1910s), cleaner than vermilion."),
    Pigment("ultramarine", "#253C99", "Lapis lazuli blue (synthetic since 1826); warm, transparent, deep."),
    Pigment("prussian_blue", "#0F3050", "First modern synthetic pigment (1704); cold greenish blue, very strong."),
    Pigment("cobalt_blue", "#1F4FA8", "Pure mid blue (1802); semi-opaque, clean in skies."),
    Pigment("cerulean_blue", "#2B7EB5", "Cool opaque greenish sky blue (1860s); the Impressionists' sky."),
    Pigment("viridian", "#2F7A64", "Transparent cool emerald green (1838); glazes and cool shadows."),
    Pigment("terre_verte", "#7B8561", "Green earth; weak dull green for flesh underpainting (verdaccio)."),
]}


def color_of(c):
    """Linear RGB of a pigment name, a '#rrggbb' string or a linear RGB triple."""
    if isinstance(c, str):
        if c in PIGMENTS:
            return PIGMENTS[c].linear
        if not c.startswith("#"):
            raise KeyError(f"unknown pigment {c!r}; known: {', '.join(PIGMENTS)}")
        return hex_to_linear(c)
    return np.asarray(c, np.float64)


class Palette:
    """A limited palette of named pigments: pal["name"] and pal.mix((name, weight), ...)."""

    def __init__(self, names):
        unknown = [n for n in names if n not in PIGMENTS]
        if unknown:
            raise KeyError(f"unknown pigments {unknown}; known: {', '.join(PIGMENTS)}")
        self.names = list(names)

    def __getitem__(self, name):
        if name not in self.names:
            raise KeyError(f"{name!r} is not on this palette ({', '.join(self.names)})")
        return PIGMENTS[name].linear

    def mix(self, *parts):
        """Kubelka-Munk mix of (pigment name or linear RGB color, weight) parts."""
        return mix(*[(self[c] if isinstance(c, str) else np.asarray(c, np.float64), w) for c, w in parts])
