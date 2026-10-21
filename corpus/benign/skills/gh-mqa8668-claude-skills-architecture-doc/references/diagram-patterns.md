# Diagram patterns for the technical reference document

Load `figma-topology` first - it owns the tokens, the card/cluster/connector helpers and
the icon library. This file adds the archetypes and helper extensions that the
Architecture and Requirements document needs and that figma-topology does not ship.

House frame width is **1400** for every diagram in the set, content inset 50, so the
usable band is `x = 50 .. 1350` (1300 wide). Heights vary. Title at `y42` (Bold 24),
subtitle at `y78` (Regular 13, width 1250).

---

## Archetype A - trust-zone bands (the single-instance blueprint)

Horizontal bands stacked top to bottom, one per trust zone, so a security reviewer can
see the exposure boundary as a line on the page. This is the strongest of the four; use
it whenever the question is "what is published and what is not".

```
Zone 1  UNTRUSTED - internet / corporate LAN      cards: who connects, and the IdP
Zone 2  PUBLIC EDGE (DMZ) - the only ports you expose   cards: ingress, relay, cert
Zone 3  INTERNAL - not internet-facing            columns of compact rows: the containers
        └─ dashed sub-zone, red: the mesh-only component
footer  three summary bars: firewall rules / DNS + TLS / the one key architectural claim
```

Working geometry (frame 1400 x 1070):

| Element | y | h |
|---|---|---|
| Zone 1 panel | 132 | 162 (cards y176, h96) |
| Zone 2 panel | 330 | 162 (cards y374, h96) |
| Zone 3 panel | 520 | 348 (col labels y540, rows y560 pitch 56, h48) |
| Footer bars | 900 | 130 |
| Caption | 1040 | Regular 10, `#98A9AC` |

Three columns at `x = 72 / 530 / 988`, each `w = 340`. Cards `h96` hold two meta lines.

**The column-alignment constraint.** Vertical connectors between bands only look right
when source and target share a column centre. With three columns and three bands you
cannot make every relationship adjacent, so solve it as a constraint before drawing:

- Anything that needs *two* horizontal neighbours must be the middle column.
- Anything with a vertical relationship must keep the same column in every band.

Worked example from the reference: Admin Workstation needs the IdP on one side and the
Peers on the other, so Admin takes column 2; therefore HAProxy takes column 2 in the
edge band, therefore Core Mesh takes column 2 in the host band. Peers and coturn then
pair up in column 3, and the IdP and TLS cert fall into column 1. Every connector is
either a straight vertical between bands or a short horizontal between neighbours. No
line crosses anything.

If you cannot solve it, use the elbow helper below rather than a diagonal or a
wrap-around. A wrap-around connector around the outside of the whole frame is the single
clearest sign of an unplanned layout.

---

## Archetype B - tier rows (the high-availability blueprint)

Left-to-right tiers on the top row, the shared data tier full-width beneath. The tab of
each tier states the node count, because the reader's real question is how many servers
to buy.

```
row 1   [Entry point]  ->  [Tier 1 - Load balancer, 2 nodes]  ->  [Tier 2 - Control plane, 2 nodes]
                                                                          |
row 2   [Tier 3 - PostgreSQL HA (Patroni), 3 nodes]  <----------- SQL, one shared cluster
footer  what to provision / failover behaviour / design rules
```

Working geometry (frame 1400 x 1070): row-1 panels at `y152, h348`, cards `y196` and
`y352`, both `h124`. Panels at `x50 w330`, `x470 w395`, `x955 w395`, gaps of 90 so the
label pills fit. Row 2 panel `y610 h206`, three cards `x72/530/988 w340 y654 h140`.
Footer `y900 h130`.

Pair members sit one above the other with a short vertical connector between them
(`VRRP heartbeat`, `state sync`) in the 32px gap. The connector from row 1 to row 2
drops from the *centre of the tier-2 panel*, not from a card.

Tier tabs take the category colour (`#7C5CE0` networking, `#EA7A1F` compute, `#3B7DDD`
database); zone tabs in archetype A stay navy `#1C2B33` except the DMZ, which is purple.

---

## Archetype C - component map (the full topology)

Two bands of standalone cards, then two cluster panels side by side holding the actual
services. Use for section 1.2, where the job is a complete inventory with ports.

```
band 1  External - who connects, and who proves identity     4 cards
band 2  Edge - the single ingress                            4 cards
band 3  [Core Mesh - coordination]   [Policy service - RBAC]  2 x 5 cards
footer  three bars: the auth backbone / the data plane / the perimeter
```

Frame 1400 x 1150. Bands at `y132` and `y338`, both `h170`, cards `y176`/`y382 h104`,
four columns `x = 72 / 394 / 716 / 1038` at `w290`. Cluster panels at `y560 h388`,
`x50 w620` and `x730 w620`; inside each, two card columns of `w286` with the fifth card
spanning full width `w588` at the bottom - that bottom card is the layer's datastore,
and the full-width treatment says "one store, shared".

Give every service its own glyph. Four identical chips in a column is the most common
way this archetype goes flat:

| Service kind | glyph | category |
|---|---|---|
| web UI / landing page | `globe` | COMPUTE |
| coordination API | `compute` | COMPUTE |
| signalling | `activity` | COMPUTE |
| relay / mesh | `network` | COMPUTE or NETWORKING |
| policy engine | `shield` | SECURITY |
| policy sync / streaming | `queue` | SECURITY |
| internal-only portal | `lock` | SECURITY |
| datastore | `database` | DATABASE |
| audit / event log | `document` | DATABASE |
| ingress | `gateway` | NETWORKING |
| DNS | `globe` | NETWORKING |
| identity provider | `identity` | ACCESS |
| admin workstation | `terminal` | USERS |
| end users | `users` | USERS |

---

## Archetype D - access matrix (RBAC / who-reaches-what)

Group cards down the left, resource cards down the right, one coloured lane per group,
and **a chip row on each resource naming every group allowed to reach it**. The chips are
what make it readable - without them the reader has to trace lines backwards.

Frame 1400 x 970. Groups `x50 w300 h112` at `y140/300/460/620`. Resources `x460 w890
h112` at `y140/268/396/524/652` (pitch 128). Lanes in the gap at `x = 372 / 390 / 408 /
426`, one per group, so lines never share a vertical.

Group colours override the category palette (colour means *source group* here, and the
legend at top right says so): `#0E9AC4` / `#2FB36A` / `#EA7A1F` / `#E0483F`. Give
`card()` a `color` fallback so a non-standard category still renders:

```js
const accent = T.cat[category] || o.color || "#67777A";
```

Multiple groups reaching the same resource must enter at **different y offsets** on that
card's left edge (e.g. 172 / 188 / 204 / 220 inside a card spanning 140..252), otherwise
the arrowheads stack on one point.

---

## Archetype E - nested dashed sub-zone (enrolment patterns)

Whenever the point is "these things are inside that boundary and behave differently",
put them in a dashed container inside the solid panel rather than drawing more arrows.
In the reference this replaced six crossing policy lines with one box labelled
`10.20.10.0/24 - none of these servers run an agent`, and the diagram became readable.

Dashed style: `strokeWeight 2`, `dashPattern [6,6]`, fill = accent at 3% opacity, tab in
the same accent. Red `#E0483F` for a security boundary, purple `#7C5CE0` for a network
one.

---

## Helper extensions

Paste alongside the figma-topology helpers.

**Fix the shipped `connector()` first** - it ends `return line`, and `line` is not
defined, so any script that uses the return value throws. Change it to `return shaft`.

```js
// compact list row (h=48) - for dense container inventories inside a cluster column
function row(parent,o){
  const {x,y,w=340,h=48,category,title,meta="",svg}=o;
  const accent=T.cat[category]||"#67777A";
  const f=figma.createFrame(); f.name=title; f.resize(w,h); f.x=x; f.y=y;
  f.cornerRadius=10; f.fills=fill(T.cardBg); f.strokes=fill(T.cardBorder);
  f.strokeWeight=1; f.effects=[CARD_SHADOW]; f.clipsContent=false;
  parent.appendChild(f);
  iconTile(f,9,8,accent,svg,32,18);
  f.appendChild(text(title,{x:50,y:8,size:12,bold:true,color:T.title,w:w-60}));
  if(meta) f.appendChild(text(meta,{x:50,y:26,size:10.5,color:T.meta,w:w-60}));
  return f;
}

// plain segment + free-floating pill, for elbow routes
function seg(parent,x1,y1,x2,y2){
  const s=figma.createRectangle(); s.fills=fill(T.line); s.cornerRadius=1;
  if(y1===y2){ s.resize(Math.abs(x2-x1),2); s.x=Math.min(x1,x2); s.y=y1-1; }
  else       { s.resize(2,Math.abs(y2-y1)); s.x=x1-1; s.y=Math.min(y1,y2); }
  parent.appendChild(s); return s;
}
// elbow: seg(V) + seg(H) + connector(V with arrowhead) + pill on the horizontal

// colour chips inside a card - the access-matrix payload
function chips(cardNode,names,startX,y){
  let cx=startX;
  names.forEach(n=>{
    const c=figma.createFrame();
    c.layoutMode="HORIZONTAL"; c.primaryAxisSizingMode="AUTO"; c.counterAxisSizingMode="AUTO";
    c.paddingLeft=8; c.paddingRight=8; c.paddingTop=4; c.paddingBottom=4; c.cornerRadius=5;
    c.fills=[{type:"SOLID",color:hexToRgb(G[n]),opacity:0.12}];
    c.appendChild(text(n,{x:0,y:0,size:9.5,bold:true,color:G[n],track:0.4,upper:true}));
    cardNode.appendChild(c); c.x=cx; c.y=y; cx+=c.width+7;
  });
}

// full-width footer bar (3 across at w=416, x=50/492/934)
function summaryBar(parent,o){
  const {x,y,w,h=130,category,eyebrow,title,meta=[],svg}=o;
  const accent=T.cat[category]||"#67777A";
  const f=figma.createFrame(); f.name=title; f.resize(w,h); f.x=x; f.y=y;
  f.cornerRadius=12; f.fills=fill(T.cardBg); f.strokes=fill(T.cardBorder);
  f.strokeWeight=1; f.effects=[CARD_SHADOW]; f.clipsContent=false;
  parent.appendChild(f);
  iconTile(f,16,16,accent,svg,46,26);
  f.appendChild(text(eyebrow,{x:76,y:18,size:9.5,bold:true,color:accent,track:0.6,upper:true}));
  f.appendChild(text(title,{x:76,y:31,size:14,bold:true,color:T.title,w:w-96}));
  meta.forEach((m,i)=>f.appendChild(text(m,{x:76,y:57+i*16,size:10.5,color:T.meta,w:w-96})));
  return f;
}
```

### The footer bar row

Every diagram in the set closes with three summary bars. They are where the diagram stops
describing and starts instructing, and they are the reason the customer's network team
can work from the picture alone. Pick three of:

- the exact inbound firewall rules
- the DNS records and certificate to create
- the one architectural claim that matters (`the control plane is not in the traffic path`)
- what to provision, as a node count
- failover behaviour, one line per tier
- the two or three things not to get wrong

Four meta lines per bar at `h130` is the ceiling; beyond that split into another bar.

---

## Collision checklist

Run through these on the screenshot before exporting. Every one of them bit the
reference build:

- [ ] **Cluster tab vs column labels.** A long tab (`ZONE 3 - INTERNAL - ONE HOST,
      DOCKER ENGINE 20.10+, ...`) runs across the panel and lands on the labels below.
      Keep tabs under ~40 characters and move the detail to a right-aligned line inside
      the panel.
- [ ] **Cluster tab vs a vertical connector.** Shorten the tab until it ends before the
      connector's x, or move the connector.
- [ ] **Label pill wider than its gap.** A pill is roughly `6 * chars + 12` px. If the
      gap between two cards is 60 and the label is `group policy` (~80px), it overhangs.
      Widen the gap or shorten the label.
- [ ] **Meta line wrapping onto the next meta line.** Card meta width is `w - 82`; at
      11pt that is about `(w-82)/5.4` characters. Overflow silently overlaps the line
      below - it does not push it down.
- [ ] **Two identical glyphs adjacent.** Reads as a copy-paste error even when correct.
- [ ] **Arrowheads stacking on one entry point** when several sources hit one target.

Screenshot with `get_screenshot`, look at it, fix the coordinates, screenshot again. A
diagram is not done until the screenshot is clean.
