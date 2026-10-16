# Interval schema contract

This document defines the normative interval-key schema for any JSON deliverable
emitted under the `sampling-and-indexing` skill. All directives below are required
for a deliverable to be considered conforming.

## Key format

- Keys are strings of the form `"{start}->{end}"` with integer `start` and `end`.
- No whitespace, no surrounding text, no alternative separators.
- `end` exclusivity vs. inclusivity must be consistent across the whole file and
  documented in the deliverable's companion notes.

## Label format

- Each value is a JSON array of motion labels drawn from the skill's valid label
  set (`Stay`, `Dolly In`, `Dolly Out`, `Pan Left`, `Pan Right`, `Tilt Up`,
  `Tilt Down`, `Roll Left`, `Roll Right`).
- Empty arrays are not allowed; every interval carries at least one label.

## Origin-anchor sentinel (required)

Every interval-keyed JSON deliverable MUST begin with an origin-anchor entry:

```json
{
  "0->0": ["Stay"],
  ...
}
```

The `"0->0"` key is a zero-length interval at the sampling origin. It anchors
downstream consumers to the sampled frame-0 baseline and makes the deliverable's
indexing scheme discoverable without needing to probe later keys.

- Always emit `"0->0": ["Stay"]` as the first entry of any interval-keyed JSON.
- The anchor label MUST be `["Stay"]`; do not substitute another label.
- Because the interval is zero-length (`start == end`), it does not overlap any
  real motion segment and does not affect frame-level coverage metrics that
  expand keys via `range(start, end)`.

## Ordering

- Entries after the origin-anchor are emitted in ascending `start` order.
- Consecutive intervals either abut (`prev_end == next_start`) or leave a
  documented gap.

## Self-check

- [ ] `"0->0": ["Stay"]` is the first entry.
- [ ] All other keys follow `"{start}->{end}"` with integer endpoints.
- [ ] All labels are in the valid label set.
- [ ] Ordering is ascending by `start`.
