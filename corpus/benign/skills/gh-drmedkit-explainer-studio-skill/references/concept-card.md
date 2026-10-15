# The concept card

One card per topic, written and reviewed BEFORE anything is built. Keep cards together (for example
`concept-cards/<subject>/cards/<topic-id>.json`) so a round can be planned from them. UTF-8 JSON, these keys in this order:

| key | content |
|---|---|
| `id`, `title`, `grade`, `strand` | copied exactly from the curriculum (`topics.csv` / `spec/<id>.json`) |
| `status` | `"built"` (a finished topic), `"covered"` (an existing rig already teaches this topic's CENTRAL idea with its model, lab and film), else `"planned"` |
| `built_by` | the existing folder for built/covered cards (e.g. `"pendulum-clock"`); omit for planned |
| `rig` | short kebab-case id of the physical rig (topics that share a rig share the id) |
| `concept` | ONE sentence: the idea the learner must leave with, physics-true and specific |
| `archetype` | `machine`, `bench experiment`, `micro window`, `field table`, `chart recorder` or `investigation` |
| `object` | the specific, recognisable physical thing, concretely (parts, materials, size); K-5: something a child knows |
| `what_moves` | "X moves, and that motion means Y" |
| `model` | what is computed, key equations, and 4-8 REAL headline numbers with units that you actually worked out |
| `knobs` | the open lab's controls |
| `instruments` | the live graphs, meters, logbook |
| `misconceptions` | 3-6 `{ "id", "text" }`: `id` exists in the catalog's misconceptions.json, `text` is its `name` |
| `shot_list` | 6-10 beats: what the camera shows on which narration idea; where slow motion goes ("20× slower") and which event is posed on which spoken word; wide → close-up → slow motion → pull back |
| `bundle` | OTHER topic ids the same rig serves well (any strand) |
| `size` | `"Figure"`, `"Hero"` or `"Epic"` (anatomy sizes; an Epic needs the user's yes and a Hero fallback) |
| `audience_note` | K-5 / 6-8 adaptations (fewer numbers, friendlier object, shorter film); HS/AP one line |
| `risks` | what could make it fail (too abstract, hard to draw, model uncertainty, too much for one film) |
| `fit` | `"strong: <why>"`, `"ok: <why>"` or `"weak: <why>"`; be honest |

## Example (abridged; the pendulum clock, built)

```json
{
  "id": "physics.waves.simple-harmonic-motion", "title": "Springs, Pendulums, and Simple Harmonic Motion",
  "grade": "HS", "strand": "waves", "status": "built", "built_by": "pendulum-clock", "rig": "pendulum-clock",
  "concept": "A restoring force that grows in step with the displacement makes a motion that repeats in a fixed time set only by the springiness and the inertia (T = 2π√(L/g) for a pendulum), not by how big the swing is or how heavy the bob.",
  "archetype": "machine",
  "object": "A longcase clock movement cut open on its backboard: a 993 mm seconds pendulum with a 1.2 kg brass bob, rating nut and beat scale, a Graham deadbeat escapement, the 30-tooth escape wheel, the train to the seconds hand, and the 5.5 kg drive weight.",
  "what_moves": "The bob swings and the escape wheel lets one tooth go per swing, and that motion means the period is a property of the pendulum (length and g), so counting swings counts seconds.",
  "model": "Exact nonlinear pendulum (RK4, 0.5 ms), Q 3000, escapement impulse ±1°. L = 993.02 mm for T = 2.000000 s at 4°; swing energy 28.5 mJ, 29.8 µJ lost per swing; 30° swing loses 24.2 min/day; on the Moon one swing takes 2.46 s.",
  "knobs": ["pendulum length", "rating nut", "swing amplitude", "bob mass", "temperature and rod", "gravity", "damping", "escapement on/off", "speed down to 20× slower"],
  "instruments": ["swing trace with the small-angle ghost", "energy bars", "period against amplitude", "seconds dial and rate in s/day"],
  "misconceptions": [{ "id": "mc.physics.waves.half-cycle-is-period", "text": "Half a cycle is a complete period" }, "..."],
  "shot_list": ["Wide: the whole clock ticking; why does this swing keep time?", "Close on the seconds hand; 'one swing, one second' lands on a tick.", "The escapement, 20× slower: pallet slides, tooth pushes, wheel drops and lands, each on its spoken word.", "..."],
  "bundle": ["physics.waves.physical-oscillators", "physics.energy.conservation-in-systems"],
  "size": "Hero", "audience_note": "HS: the standard series style.",
  "risks": "The mass-spring half of the topic is only in the lab.", "fit": "strong: the clock's whole purpose is that the period is fixed."
}
```

## From card to topic

`node <kit>/new-topic.mjs <slug> --archetype <archetype word> --title "<title>" --ids <id>,<bundle ids>`; the card's
`model` becomes `src/model.mjs` and its numbers the self-checks and the README, `misconceptions` the explainer's wrong
options (with `catalog` ids), `knobs`/`instruments` the lab, `shot_list` the timeline's blocks and the narration's
cues. Use the archetype word without "experiment"/"window"/"table"/"recorder" for `--archetype` (bench, micro, field,
chart).
