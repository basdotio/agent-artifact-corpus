# Diagrams

A diagram on a slide explains a mechanism: how data flows, what depends on what, what happens in which order. It builds in the same order the speaker explains it.

## Kinds and when to use them

| Explains | Diagram |
|---|---|
| a process, left to right | flow: nodes and arrows, one node per step |
| a loop, a flywheel | cycle: the flow plus a return edge underneath |
| a system | architecture: boxes for components, grouped by boundary (client, cloud, partner) |
| order in time | timeline or roadmap: one axis, milestones |
| a hierarchy | tree or org chart, at most three levels |
| overlap of two ideas | 2×2 matrix; Venn only for two or three sets |
| a funnel | stages as bars of decreasing width, with the drop-off between them |
| before / after | two panels with the same layout, the changed parts in the accent |

## Layout

- **Use a grid, not a force layout.** Put nodes on columns and rows you choose. Readers follow left-to-right and top-to-bottom; the main path goes that way.
- Nodes of the same kind share size and style. Sizes carry meaning only if you say so.
- Edges are straight or orthogonal (H/V segments) or one smooth curve for a return path. No crossing edges on the main path.
- Label edges only when the label adds information ("every 5 min", "HTTPS"). Place the label on the edge, not in a legend.
- One accent: the node or path that the slide is about.
- Text inside nodes: a title (display font, 40–48 px) and at most one line of detail (22–24 px).

Nodes can be HTML (`div`s positioned in canvas pixels) or SVG. HTML is easier for text that wraps and for `morph`; SVG is easier for edges. Mixing is fine: HTML nodes plus one full-slide `<svg class="art">` on top for edges (demo slide 6).

## Build order

1. The first node (often carried in by `morph` from the previous slide).
2. Each next step: the edge draws (`data-anim="draw"`), then the node pops (`data-anim="pop"`, delay 0.3–0.5 s so it lands when the edge arrives).
3. The last step closes the loop, and the flow starts moving.

```js
// edges: draw on their step; flows: dashed copies that move once everything is there
svg('path', { d, class: 'edge', 'data-step': s, 'data-anim': 'draw', 'data-dur': .6 }, g);
const flow = svg('path', { d, class: 'flow', 'data-step': 3, 'data-anim': 'fade' }, g);
// frame:
flow.style.strokeDashoffset = -st.T * 70;   // constant process: linear is right here
```

With `.flow { stroke-dasharray: 1 38; stroke-linecap: round; stroke-width: 9 }` the dashes become dots running along the edge.

## Arrowheads

Use `<marker>` only for static diagrams: markers do not follow `draw` and they appear at full size while the line is still at zero. For animated edges, add the arrowhead as a separate small path at the end, faded in at the end of the draw (`data-delay` = edge delay + edge duration × 0.8).

## Architecture diagrams

- Group boxes by boundary with a dashed container and a label in the corner ("Customer VPC", "Our cloud").
- Draw requests as edges with a direction; draw data stores as a distinct shape (a cylinder or a box with a double top rule).
- Build by request path: show what happens to one request, step by step, and light the path in the accent. Then show the rest in ink.
- A second slide can `zoom` into one box (`data-origin` on it) to show its inside.

## Timelines and roadmaps

- One horizontal axis, ticks per quarter or month, labels under the axis.
- Milestones alternate above and below the axis so labels never collide.
- "Today" is a distinct marker. The past is solid, the future dashed (demo slide 13).
- Build: the solid line runs to each milestone in turn, one per step; the milestone pops when the line reaches it.

## Illustrations as diagrams

A product drawn like a technical drawing explains more than a photo: line art in ink, one accent for the part being discussed, dimension lines in muted, numbered badges that match the callouts (demo slide 5). Draw it with `data-anim="draw"` in the order a person would sketch it: base, main body, details, dimensions.
