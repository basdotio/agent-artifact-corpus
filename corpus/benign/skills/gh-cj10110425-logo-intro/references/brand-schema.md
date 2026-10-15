# Brand config

A brand is one JSON object. Coordinates are **logo units**, the same units as the logo's SVG `viewBox`.

## Example A: text wordmark with a badge (`brands/cheatgtm.json`)

```jsonc
{
  "name": "CheatGTM",                       // used for the page title and the lockup's aria-label
  "theme": { ... },
  "mark": {
    "viewBox": [0, 0, 36, 36],              // the mark's box; the text wordmark is laid out to its right
    "paths": [{ "d": "M18 8.25v19.5…", "stroke": 3.25, "cap": "round", "join": "round" }],
    "badge": { "x": 0, "y": 0, "width": 36, "height": 36, "radius": 10, "color": "#c6f23a" }
  },
  "wordmark": {
    "text": "CheatGTM",
    "font": { "family": "Manrope", "weight": 800, "letterSpacing": -0.045,
              "css": "https://fonts.googleapis.com/css2?family=Manrope:wght@800&display=swap" },
    "fontSize": 27.7,                       // logo units (default: mark height / 1.3)
    "gap": 10                               // logo units between mark and text (default: 0.28 × mark height)
  },
  "lockIn": { "type": "badge" }
}
```

## Example B: outlined (path) wordmark with a two-part mark

```jsonc
{
  "name": "Example",
  "viewBox": [0, 0, 579, 130],              // one coordinate system for mark and letters
  "theme": { ... },
  "mark": { "paths": [{ "d": "M24.5 80…Z", "part": 0 }, { "d": "M74.4 85…Z", "part": 1 }] },
  "wordmark": {
    "letters": [["M190.7 27.3…Z"], ["M303.7 121.8…Z", "M339.7 86.1…Z"]],   // one array per letter, counters included
    "xHeight": 70                           // optional; sets the shimmer band width and letter pull-out distance
  },
  "lockIn": { "type": "assemble", "direction": [0.7071, 0.7071], "distance": 28 }
}
```

## Fields

### `theme`
| Field | Default | Notes |
|---|---|---|
| `background` | `#fbfbf9` | Page ground and the colour the canvas clears to |
| `ink` | `#15181a` | Colour of the mark and wordmark |
| `markInk` | `ink` | Colour of the mark during the close-up, when it differs from the letters |
| `bloom` | lime/mint/aqua/butter/lilac | Five colours for the gradient blob; the first carries the most weight |
| `bloomOpacity` | `0.88` | Use lower values on dark grounds |
| `shimmer` | `#7c5cff`, `#19c3e6`, `#ff4fb8` | The three colours of the sweeping band |

### `mark.paths[]`
| Field | Notes |
|---|---|
| `d` | SVG path data |
| `stroke` | Stroke width. Omit it for filled paths |
| `cap`, `join` | Stroke line cap and join |
| `fillRule` | `nonzero` (default) or `evenodd` |
| `part` | `0` (default) or `1`. In `assemble` part 1 moves opposite to part 0; in `rise` only part 1 moves |
| `color` | Fixed colour for this path. Without it the path uses `theme.ink`. The shimmer passes over coloured paths as a tint |
| `gradient` | `{ "from": [x, y], "to": [x, y], "stops": [[0, "#828afc"], [1, "#a35aff"]] }`, a linear gradient in logo units. Use it instead of `color` |

### `mark.clip`
Optional path data. Part 1 is drawn only inside it, and the clip stays put while part 1 moves.

### `mark.badge`
Optional shape drawn behind the mark: a rounded rectangle (`x`, `y`, `width`, `height`, `radius`) or any path (`d`), plus a `color`. It pops in at the lock-in, and the shimmer tints it as it passes.

### `wordmark`
Use `text` (with `font`, `fontSize`, `gap`, optional `baselineShift` in ems) **or** `letters` (arrays of path data in the shared `viewBox`).

### `scale`
Lockup size multiplier for this brand. Defaults to `1`. Raise it (for example to `1.3`) for long wordmarks that would otherwise leave the mark small.

### `closeUp`
Mark size at the start of the zoom as a multiple of the screen diagonal. Defaults to `1.2`. Lower it (about `0.8`) for hollow marks such as rings, so the opening frame shows the shape rather than its empty centre.

### `lockIn`
- `badge`: the badge pops in with an overshoot.
- `assemble`: the parts start `distance` apart along `direction` and snap together.
- `rise`: part 1 travels in from `direction` by `distance` while part 0 stays. Use it with `mark.clip` so the part appears only inside a shape, like layers filling a ring.
- `spin`: the mark turns through `angle` degrees (default 120) and snaps into place. Use a multiple of the mark's symmetry so the resting pose looks the same before and after.
- `pulse`: the mark dips and returns.

`at` sets when the lock-in starts, in seconds. The default is `2.6`, which comes after the wordmark. Set it below 2 (for example `1.1`) to play the lock-in on the landed mark first; the wordmark then waits until it finishes.

In every mode the mark pulses. The bloom hollows into an expanding ring at 2.65 s.

## Timeline (seconds)
| Beat | Start | What happens |
|---|---|---|
| Mark | 0.18 | Close-up zoom-out with spin, lens warp, spectral fringes and zoom blur |
| Wordmark | 1.15 | Mark slides aside; letters pull out one by one, unblurring |
| Bloom | 0.85 | Mesh-gradient blob grows behind the lockup |
| Lock-in | 2.60 | Badge pops or parts snap; the blob hollows into a ring |
| Shimmer | 3.15 | One band sweeps the lockup at 105° |
| Hold | 4.05 | Rest until 5.0 |
