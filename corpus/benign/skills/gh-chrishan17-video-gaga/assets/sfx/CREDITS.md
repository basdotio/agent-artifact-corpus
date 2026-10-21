# Sound effect recordings

All recordings here are by **Kenney** (www.kenney.nl), released under **CC0 1.0** (public domain): free for any use, credit appreciated but not required.

| Type | Takes | Source pack (file) |
|---|---|---|
| tick | 5 | UI Audio (switch1, 10, 11, 15, 17) |
| click | 4 | UI Audio (click3, click4, click5, mouseclick1) |
| type | 5 | UI Audio (switch12, 13, 14, 16, 18) |
| pop | 4 | Casino Audio (chip-lay-1, 2; chips-collide-1, 2) |
| paper | 5 | RPG Audio (bookFlip1–3); Casino Audio (card-shove-1, 2) |
| card | 4 | Casino Audio (card-place-1–4) |
| book | 4 | RPG Audio (bookClose, bookPlace1–3) |
| cloth | 3 | RPG Audio (cloth1–3) |
| wood | 5 | Impact Sounds (impactWood_light_000–004) |
| glass | 5 | Impact Sounds (impactGlass_light_000–004) |
| metal | 5 | Impact Sounds (impactMetal_light_000–004) |
| thud | 5 | Impact Sounds (impactPlank_medium_000–004) |
| step | 5 | Impact Sounds (footstep_concrete_000–004) |

Each take was converted to 48 kHz mono 16-bit WAV, high-passed (60–200 Hz by type, so no handling rumble) and low-passed at 16 kHz, trimmed to its onset with a short fade at the end, and levelled so its loudest 20 ms sits at −12 dBFS. `scripts/music.mjs` (`RECORDED`) sets each type's level in the mix.
