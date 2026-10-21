# Category reference

Read the section for the asset's category before Phase 0 of SKILL.md. Each section covers:
what to measure in the reference, how to construct it in bpy, which parts stay separate,
topology rules, UV and material policy, articulation and sockets, and what the acceptance
check looks for. The construction helpers named here live in `assets/build_template.py`.

Contents
1. Construction techniques (all categories)
2. Characters (bipeds)
3. Creatures (quadrupeds, winged, serpentine, multi-limbed)
4. Architecture (modular kits and hero buildings)
5. Vehicles (wheeled, tracked, aircraft, watercraft, hover)
6. Props and weapons
7. Environment pieces (rocks, foliage, terrain chunks)

## 1. Construction techniques

Code-driven modelling works when each part is built from a measured construction, not sculpted
free-hand. Pick the technique per part:

| Need | Technique | Helper |
| --- | --- | --- |
| Organic mass with joints (torso, limbs, neck, tail) | Skin modifier over a joint chain with radii, plus Subdivision | `skin_chain` |
| Fused organic base for sculpting | Join blockout pieces, voxel Remesh at 1/200 of height, then `push` sculpting | `join_meshes`, `remesh_voxel`, `push` |
| Hard-surface shell (car body, hull, fuselage, torso armour) | Loft cross sections read at stations from the side and top views | `loft` |
| Rotational parts (wheels, rims, columns, bolts, vases, barrels) | Lathe a 2D profile | `profile_spin` |
| Extruded profiles (arches, mouldings, beams, tracks, trims, rails) | Extrude a 2D outline | `profile_extrude` |
| Cables, horns, tails, pipes, tentacles, railings, roots | Curve with bevel depth and taper | `curve_tube` |
| Panels, plates, cloth, cladding, roofs | Grid or extracted faces plus Solidify | `grid`, `solidify` |
| Symmetry | Mirror modifier with clipping, applied only on the delivery copy | `mirror` |
| Cut-outs (windows, wheel wells, vents, panel lines) | Boolean with a hidden cutter, then Bevel for light-catching edges | `boolean`, `bevel` |
| Repetition (windows, rivets, treads, teeth, stairs) | Array, optionally along a curve | `array` |
| Tapering limbs and spires | Scale cross sections along an axis | `taper` |
| Low mesh over a sculpt | Base cage with joint loops, Shrinkwrap to HIGH, then Subdivision level 1 | `shrinkwrap` |
| Extra LODs | Duplicate, Decimate, then fix the silhouette by hand | `lod_copy` |

Measure everything from the brief. Every constant in a build script is a real dimension in
metres with a comment saying which reference view it came from. A guessed value gets the comment
`# inferred` so the manifest can list it.

Blockout budget: 15 to 60 primitives is normal for a character or vehicle. Fewer usually means
the silhouette is missing a mass; more usually means detail arrived before the silhouette passed.

## 2. Characters (bipeds)

Read the reference for: total height, head height (the proportion unit: realistic 7.5 to 8 heads,
heroic 8.5, stylised 3 to 6), shoulder width in heads, hip width, arm length (wrist at mid-thigh
when relaxed), leg length (crotch at roughly half height), stance width, posture line, costume
layers in overlap order, weapon and its grip.

Scale cues when no height is given: adult male 1.75 to 1.85 m, adult female 1.62 to 1.72 m,
a sword grip 0.1 m per hand, a doorway 2.1 m, a standard step 0.17 m.

Construct: `skin_chain` for pelvis, spine, chest, neck, head, both arms and legs with radii per
segment; separate spheres for skull and joints that need mass; boxes for hands and feet; jaw,
eyes, teeth, tongue, horns and hair volumes as separate objects. Costume as separate solidified
surfaces built outward in overlap order: body, inner garment, outer garment, belts and straps,
mantle or hood, cape and ornaments. Give garments real circumference and clearance for a full
stride; a skin-tight cone cannot be turned into a skirt later by simulation settings. Sleeves are
separate tubes with real arm openings; never bridge the armpit with accidental geometry.
Armour models the real overlap order: pauldron over the upper-arm plate, couter over the
vambrace, tassets over the thigh plates, each with visible edge thickness and bevels that catch
light.

Keep a complete body under the costume in the master; make coverage cuts only on the export copy
and test every equipment combination for holes.

Techniques for faces, smooth analytic forms, hands, the neck join, armour over clothing and strand hair:

- Face: calibrate a front and a profile blueprint of the head (a pixel scale, the pupil height, the
  facial midline, 30 to 50 landmarks in world space) and fit the head to them: the midline profile
  to the side silhouette, the outline to the front one, eyeballs placed from the pupils with the
  lids wrapping them, ears from the profile landmarks. Done when the overlays through calibrated
  reference cameras show landmark errors under about 1 mm. Three-quarter concept views are
  usually not metric (AI or painted views disagree with the blueprints by several percent); use
  them to judge likeness, never to measure. Texture the skin by projecting the de-lit blueprints
  through rest-pose UV maps (front, and profile mirrored for the far side), blended by which way
  the rest normal faces; strip painted brows and lashes and grow them as strands.
- Smooth analytic forms (SDF heads, bodies): tables of widths or depths need smoothing, or
  linear interpolation shows as shading bands; blend two descriptions of the same surface by
  position weight, not smooth union, which bulges where they coincide.
- Hands: build them in a local frame (palm normal, thumb side, length) and mirror the frame for
  the other hand; a rotated copy of one hand puts the thumb behind and reverses the finger order.
  Relaxed hands at the thighs have the thumb forward. Fingerless-glove cuts end at the fingertip,
  or curled fists open holes in the glove.
- Neck: the body's neck follows the head's neck just inside it (1 to 2 mm) so the textured head
  owns the visible skin and there is no step; give both the same skin texture mapping.
- Armour and straps over clothing: sample the garment surface on rays around a limb axis and
  offset along the ray, designing each outline in (angle around the limb, height) space. Plates
  then hug the leather whatever the limb shape, and outlines stay exact. Layer high collars and
  gorgets as body, undersuit up to the neckline, collar with a few mm of air around the neck,
  gorget resting on the shoulders over the collar base, then pauldrons. Check clearances with
  mesh overlap tests, not by eye.
- Strand hair: give each class of hair its own collider. The envelope that keeps long hair
  outside the pauldrons is far too fat beside the neck and turns short face-framing locks into a
  sideways tuft. Shading: a Principled Hair BSDF fitted by colour models a dense hair volume, so
  its transmission makes a sparse backlit lock read blonde; use it as a highlight layer (about 15
  percent, transmission weakened) over a Principled base, and check a thin lock against a dark
  background, not only the dense mass.

Topology (LOW): continuous loops around eyes, mouth, shoulders, elbows, wrists, hips, knees and
ankles; three or more segments on each side of a bending joint; no long thin triangles or high
valence poles on a crease; clavicle geometry that lets an arm rise without collapsing the chest;
individual finger joint sections when hands grip or draw; a jaw with a sensible pivot and a
lip-to-cheek transition. Quads in the editable source, triangulated delivery, and the intended
triangulation locked before baking.

UV and material: unique texture space for the face and focal costume areas, shared trims for
repeated straps, buckles and chain; consistent texel density across the body; roles such as
skin, hair, woven cloth, worn leather, corroded metal each with a believable roughness range.

Articulation: humanoid deformation skeleton (see rigging-animation.md), sockets for both hands,
weapon tip, back mount, head, chest and feet.

Acceptance specifics: role and silhouette readable at gameplay size in greyscale; feet contact
the floor; hands hold their weapon; shoulders, elbows, hips and knees deform cleanly on the
extreme-pose sheet; no holes between costume pieces in any pose.

## 3. Creatures

Read the reference for: body length and shoulder height, head length as the proportion unit,
limb count and gait type, joint placement (scapula, shoulder, elbow, carpus; hip, stifle, hock),
neck length and range, tail length and taper, wing span and fold, jaw gape, membranes, spines,
plates, scales and where they stop, the action it must perform (bite, lunge, breath, pounce).

Scale cues: a large dog 0.6 m at the shoulder, a horse 1.6 m, a bear 1.0 m on all fours; wing
span roughly 2 to 2.5 times body length for flight-capable designs.

Construct: `skin_chain` for spine (nose to tail tip) and each limb with the correct joint count
and positions. A quadruped's apparent backward knee is the hock; the stifle sits higher near the
body, and the scapula floats on the ribcage. Ribcage and pelvis as separate ellipsoids so the
shoulder and hip motion has masses to slide over. Wings: leading-edge chain (humerus, radius,
metacarpal, digits) plus membranes built as grids bridged between the digit chains and the body,
with enough resolution to fold without reversing their surface. Tails, horns, tendrils and
tongues with `curve_tube`. Jaw, tongue, teeth, eyes, claws and membranes as separate objects
where they need independent shading, deformation or articulation.

Topology: loops at every joint listed above, extra loops where the neck curves and the tail arcs,
membrane grids aligned to fold lines, a jaw loop that can open to the reference gape. Test neck
curvature, mouth opening, wing fold and tail arc before accepting topology.

UV and material: skin, scales, plates, membrane and teeth as distinct roles; membranes may need
two-sided shading and translucency tested against cost; symmetry mirroring is fine for hide,
unique space for the head.

Articulation: quadruped or winged rig family, sockets for mouth (breath, bite origin), eyes,
feet, saddle or rider point, and effect points on chest or back. Mouth socket forward must agree
with the attack direction.

Acceptance specifics: gait-critical joints in the right place, wings fold and unfold without
self-intersection, neck and jaw reach the reference action pose, silhouette readable at distance.

## 4. Architecture

Read the reference for: storey height, door and window openings and their rhythm, wall thickness,
roof pitch and overhang, plinth and cornice lines, repeat modules, ornament families, materials by
surface (stone, plaster, timber, tile, metal), damage and weathering pattern, and what is a
separate object (doors, shutters, gates, banners).

Scale cues: door 0.9 x 2.1 m, storey 3.0 to 3.6 m (grander 4 to 5 m), step 0.17 m rise, brick
course 0.075 m, window sill 0.9 m, railing 1.0 m, medieval wall 0.6 to 1.2 m thick.

Construct as a kit on the gameplay grid (`--cell` from init_master): floor tiles, wall segments
(plain, window, door, corner, end cap), pillars, arches (`profile_extrude` or `profile_spin` for
half domes), roof segments (extruded pitch profile), trims and cornices (`profile_extrude`, or
a curve with a profile bevel object), stairs (`array`), railings (`curve_tube` and `array`). Every
piece's origin sits at its grid corner on the floor so pieces snap; wall thickness and floor
thickness are constants shared by every piece. Hero buildings are assembled from the kit plus a
few unique pieces, never sculpted as one blob.

Parts: doors, gates and shutters are separate objects with the pivot at the hinge line. Colliders
are simple prisms per piece, independent from ornament density. Two or three silhouette variants
per wall type (damaged, vined, plain) beat unique geometry everywhere.

Topology: clean quads with bevels only where light catches, controlled reduction is fine on
rubble and ornament; planar faces stay planar for snapping seams; no doubled faces where pieces
overlap at seams.

UV and material: tileable materials for large surfaces (stone, plaster, timber) with a trim sheet
for edges, cornices, mouldings and door frames; unique decals for signs and damage; small props
share atlases. Never a unique large texture per stone. Texel density constant across the kit.
Set the tileable UV scale so the brick course or plank width matches the metre scale.

Articulation: hinge pivots for doors and gates, sockets for torches, banners, signs and effect
points. Interactables (chest, gate, portal) get named open/close states.

Acceptance specifics: a 2 x 2 assembly of the kit shows no seams, gaps or z-fighting; door
clearance passes the REF_door proxy; the collider set blocks the player where the visual does;
the tileable scale reads right next to the REF_ruler.

## 5. Vehicles

Read the reference for: overall length, width, height, wheelbase and track (or hull length and
beam, span and fuselage length), wheel diameter, ground clearance, body sections and panel gaps,
glazing, doors and hatches, turrets and weapons, lights, exhausts, intakes, suspension travel,
and the interior visible through glass or open cockpits.

Scale cues: car wheel 0.6 to 0.75 m, truck wheel 1.0 m, sedan 4.5 m long, 1.8 m wide, 1.45 m
tall; door handle 0.95 m from ground; tank 6 to 8 m long, 3.5 m wide; light aircraft 7 to 9 m
span; seat height 0.45 m above the floor inside.

Construct: body shell with `loft` from cross sections measured at 6 to 12 stations along the
length (height from the side view, width from the top view, corner radii from the front view),
then Subdivision or Bevel; wheels with `profile_spin` (tyre, rim, hub) as separate objects with
their origin at the axle centre; wheel wells and windows via `boolean`; doors, hatches, hood, trunk
and turret as separate objects cut from the shell with panel gaps and inner thickness; tracks as
an `array` of one link along a curve; suspension arms and axles as simple cylinders; interior only
to the depth that is visible. Front of the vehicle faces -Y like everything else.

Parts: separate objects for anything that moves (wheels, steering knuckles, doors, hatches,
turret, barrel, props, rotors, flaps, rudder) and for glass. Lights and exhausts are separate for
material reasons. Vehicle origin at the ground centre under the wheelbase midpoint.

Topology: even quad flow along body lines, supporting loops at panel edges, bevelled edges with
thickness at every exposed edge; wheels around 32 to 48 segments at LOD0; no ngons on curved
panels.

UV and material: painted metal, chrome, rubber, glass, plastic, fabric and light emissive as
roles; unique space for the body, shared trims and atlases for wheels, interior and hardware;
decals for numbers and insignia; roughness variation from wear and dust, not noise.

Articulation: a rig or empty hierarchy with real pivots: wheels spin about their axle and steer
about the kingpin, doors about the hinge line, turret about its ring, barrel about its trunnion.
Sockets for driver seat, passenger seats, weapon mounts, exhaust and light effects, tow points,
camera mounts. Colliders: a body hull plus wheel cylinders, or a convex set.

Acceptance specifics: wheels sit on the ground with the reference clearance, wheelbase and track
match the reference within 2 percent, doors open without clipping, the silhouette reads from the
game camera, glass does not hide the driver when it should not.

## 6. Props and weapons

Read the reference for: overall dimensions, grip or contact point, moving parts and hinges,
material roles, wear, what is decorative versus functional.

Scale cues: hand grip diameter 0.03 to 0.045 m, sword blade 0.7 to 0.9 m, rifle 1.0 m, pistol
0.2 m, barrel 0.9 m tall, crate 0.5 to 1.0 m, torch 0.5 m, chest 0.8 x 0.5 x 0.5 m.

Construct: primitives plus `bevel` for hard surface, `profile_spin` for anything round (bottle,
barrel, bolt head, pommel), `profile_extrude` for blades and beams, `curve_tube` for straps,
chains and cables, `boolean` for cut-outs. Weapon origin at the grip centre, local +Y toward the
tip or muzzle, +Z toward the edge or sights, so it matches the hand socket convention.

Parts: separate objects at every hinge (lid, gate, trigger, bolt), with the origin at the pivot.
Strings on bows and cables on winches are separate so they can flex.

Topology: light and clean; small props under a few hundred triangles, hero weapons a few thousand
with real edge bevels; no hidden interior geometry.

UV and material: shared atlases for small props of one family, unique space for hero weapons,
trims for straps and metal edges.

Articulation: hinge empties or bones, `SOCKET_grip` and `SOCKET_tip` (or muzzle) with the
convention above; the socket must be tested with the actual hand and animation, not an empty at
the hand origin.

Acceptance specifics: grip fits a hand of the character it belongs to, hinge motion passes through
its real range without clipping, the silhouette survives at gameplay distance.

## 7. Environment pieces

Read the reference for: overall size, silhouette layers (mass, secondary forms, surface break-up),
tiling or instancing intent, contact with the ground, material roles.

Construct: rocks from a subdivided box or sphere with `push` displacement and voxel Remesh, then
Decimate for LODs; trees with `curve_tube` trunks and branches plus card or shell canopies; terrain
chunks as displaced grids; cliffs as lofted profiles. Keep the bottom flat or buried so placement
does not float.

Parts: single objects where possible; separate canopies for wind; separate collision proxies.

Topology: controlled reduction is fine here (rubble, rocks); align the pivot to the ground contact
and keep the silhouette at each LOD.

UV and material: tileable rock, bark and soil with a triplanar or box projection and a detail
normal; leaf cards with opaque cut-outs tested before any true transparency.

Acceptance specifics: reads as its material at distance, no floating on flat ground, LODs preserve
the outline, instances tile without visible repetition at gameplay density.
