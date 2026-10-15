# Cell parts

Flat vector parts used by the `Cell` composition (`remotion/src/illustrated/cell/`).

- Art: one sprite sheet generated with Google Gemini (image model), prompted for flat Kurzgesagt-style cell assets on a solid navy background.
- Cut and traced with `scripts/split.py` (default options), which uses [vtracer](https://github.com/visioncortex/vtracer) 0.6.5 for SVG tracing.
- Kept: `a00` nucleus, `a03`–`a06` mitochondria, `a09`–`a10` vesicles. The membrane, chromosomes and centrosomes are drawn in code.
