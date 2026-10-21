# Rigging, sockets, animation and secondary motion

Read this before Phase 6 (articulation) and again before Phases 7 and 8. Applies to any asset that
moves: characters and creatures fully, vehicles and hinged props for the pivot and socket rules.

Contents
1. Skeleton families and hierarchy
2. Binding and weights
3. Extreme-pose sheet
4. Sockets and functional parts
5. Animation library and event contract
6. Secondary motion (cloth, chains, wings, antennae)

## 1. Skeleton families and hierarchy

Keep the authoring rig and the delivery rig apart: RIG_CTRL holds animator controls, IK, pole
targets and constraints; RIG_DEF holds the deformation skeleton that ships. Export evaluated
deformation, never an expectation that the engine understands Blender constraints.

Rig families, so compatible assets share animation: humanoid biped, heavy or giant biped,
quadruped, winged, serpentine, wheeled vehicle, tracked vehicle, aircraft, hinged prop. One
family per asset; note it in the brief. A shared family saves animation work but does not
justify identical walk, reach or timing across roles.

Humanoid deformation hierarchy (names are a proposed convention, keep them stable across the
family):

```text
root                       ground origin, optional root motion
  pelvis
    spine_01 -> spine_02 -> chest -> neck -> head -> jaw
    clavicle.L -> upper_arm.L -> forearm.L -> hand.L -> fingers
    clavicle.R -> upper_arm.R -> forearm.R -> hand.R -> fingers
    thigh.L -> shin.L -> foot.L -> toe.L
    thigh.R -> shin.R -> foot.R -> toe.R
    garment and accessory bones where needed
```

Twist bones (upper arm, forearm, thigh), eye bones, jaw, breast or belly bones for heavy
builds, and cloth, wing, tail or antenna chains supplement this. Quadruped: spine chain from
pelvis through neck and head, four limbs with scapula, shoulder, elbow, carpus and hip, stifle,
hock, plus tail chain. Winged: humerus, radius, metacarpal, digit chains per wing with membrane
helper bones. Vehicles: body root, one bone or empty per wheel at the axle centre (child of a
steer pivot for steered wheels), per door at the hinge line, turret at the ring, barrel at the
trunnion, suspension bones if animated. Hinged props: base plus one bone per moving part at its
real pivot.

Rules: one root at the ground origin, a stable rest pose (A-pose or relaxed T-pose recorded in
the manifest), no negative or mirrored scale anywhere in the hierarchy, bone names without
numeric suffixes, DEF- prefix on deformation bones so export filters are trivial, object scale
applied before binding.

## 2. Binding and weights

Bind every deforming costume piece to the same skeleton. Normalise weights, remove tiny
influences, inspect unweighted vertices (validate.py fails on these). Start with four influences
per vertex as the delivery target and raise it only if the engine and a measured budget allow.
Rigid armour follows one bone or a controlled small set; flesh around shoulders and hips needs
smooth transitions and twist management. Blender's Armature modifier has a Preserve Volume
option that changes the result; verify deformation in the target engine rather than trusting a
viewport setting (Armature modifier reference:
https://docs.blender.org/manual/en/latest/modeling/modifiers/deform/armature.html).

Do not apply an Armature modifier as a cleanup step on a bound character; that bakes a pose into
the mesh and breaks the rig relationship. Apply only the modifiers meant for the delivery copy
(Mirror, Bevel, Subdivision, Solidify) and only on that copy.

Fix deformation problems in this order: joint placement, topology, weights. Corrective shape
keys are a targeted tool for a specific pose, not a substitute for a viable bind.

## 3. Extreme-pose sheet

Before accepting a rig, render (review_render.py with `--action` and `--frame`) a sheet of the
worst poses the asset will actually hit and inspect every separate part together:

Bipeds: arms overhead, forward reach, crossed-arm cast, deep elbow and knee bend, hip flexion,
full stride, wide stance, bow draw or two-handed grip, torso twist, crouch, death pose.
Quadrupeds: full stride at gallop, pounce crouch, rear, head turn, bite gape, tail curl.
Winged: full fold, full spread, downstroke, banked turn.
Vehicles: full steering lock, full suspension compression and rebound, doors and hatches at max,
turret and barrel at limits.
Props: hinge at both limits.

Pass criteria: no collapsed volume at joints, no interpenetration between armour or garment pieces,
no exposed holes, feet or wheels stay on their contact plane, the weapon stays in the hand.

## 4. Sockets and functional parts

Sockets are semantic attachment points: `SOCKET_hand.R`, `SOCKET_hand.L`, `SOCKET_weapon_tip`,
`SOCKET_back`, `SOCKET_head`, `SOCKET_chest`, `SOCKET_foot.L`, `SOCKET_mouth`, `SOCKET_muzzle`,
`SOCKET_exhaust`, `SOCKET_seat_driver`, `SOCKET_hinge_door.L`, `SOCKET_summon_origin`. Each is an
empty with an arrows display, parented to the bone or part it follows, with local +Y as the
forward of whatever attaches and +Z as its up. Record the convention and any custom properties in
the manifest (export_delivery.py does this).

Test a socket with its real attachment and animation: a weapon in the hand through the whole
attack, a rider in the seat through the gallop, a muzzle flash at the muzzle during recoil. An
empty at the hand origin proves nothing.

Hinged parts pivot at the hinge. Bows need real string and nock motion. Shields need a grip
orientation that works through every animation. A breath or projectile origin must agree with
the effect cone and the gameplay aim. Gameplay hit shapes stay separate from decorative teeth,
fingers and spikes.

## 5. Animation library and event contract

Author animations as individually named Actions with deliberate start and end frames and a loop
flag (custom property `loop` on the action, or a `_loop` suffix). Use one authoring frame rate
(30 fps default) but express gameplay events in seconds or normalised time; never assume a frame
count equals a cooldown.

Starting library by family (adapt to the actual game):

| Family | Minimum library |
| --- | --- |
| Player character | idle variants, forward/back/left/right locomotion, starts and stops, turns, basic attack, ability gestures, dash or dodge, hit reactions, stun, downed loop, revive, death |
| Melee enemy | idle, move, attack anticipation, active, recovery, hit variants, stagger, death |
| Ranged or caster enemy | idle, move, aim, cast or fire, recoil, interruption, death |
| Quadruped | idle, walk, run, turn, bite or lunge, recoil, death, with correct foot contacts and spine timing |
| Flying or floating | hover loop, flight loop, banking turns, attack, interruption, fall or dissolve |
| Boss | locomotion, each move family, phase transition, telegraph poses, stagger, death |
| Vehicle | idle, wheels spin (driven by code), suspension bounce, doors open and close, turret traverse, destroyed state |
| Interactable | open, close, locked, active, hit, break, channel states |

Per attack record: anticipation, authoritative active window, recovery, allowed cancels,
locomotion permission and interruption behaviour. Keep a clear silhouette change on major
attacks, and start any telegraph early enough for the intended escape window. Put these as pose
markers on the Action (`action.pose_markers`, shown with Show Pose Markers in the Action Editor)
named `active_start`, `active_end`, `hit`, `release`, `cancel_ok`, `footstep.L`; export_delivery.py
writes them to animation-contract.json in seconds.

Locomotion: in-place clips for an initial engine port, each tagged with its authored speed
(action custom property `speed_mps`) and blend direction; preserve root displacement separately if
root motion is adopted later, and let the engine validate that displacement. Layer upper-body
attacks over lower-body locomotion with an explicit reference pose and mask; keep pelvis and root
out of the additive layer unless deliberate. Test attacks while moving backward and sideways.
Foot IK corrects presentation to the floor without moving the authoritative position.

Delivery: bake IK and constraint results to the deformation skeleton, check interpolation between
samples, check loop seams for root drift and pops, keep the unbaked Action master. Ship the
neutral pose, event metadata and clip lengths with the animations.

## 6. Secondary motion

Three responsibilities stay explicit: the visible garment, the simulation or deformation
representation, and the collision representation. A detailed render robe is not automatically the
simulation mesh or the collision surface. The same applies to chains, tassels, antennae, wing
membranes, tank tracks and hanging cables.

Authoring process:
1. Build a low-resolution, evenly distributed simulation cage with stable panels and enough
   resolution for the intended folds. Transfer its motion to the render garment through a
   validated bind (Surface Deform or Mesh Deform in Blender, or the engine's cloth workflow).
2. Pin real attachment areas (shoulders, collar, belt, wing bones) with a graded transition. Leave
   intended hems free. Model real clearance around legs, elbows, mantle and belt before tuning
   any physics.
3. Create simple torso, pelvis, thigh and limb collision proxies aligned to the posed skeleton
   (COL_ objects). Test the render garment against the visible body and the proxies: an oversized
   capsule keeps cloth numerically outside while it visibly floats.
4. One owner per vertex's final motion. If the solver receives skinned positions, do not apply the
   armature transform a second time. Never stack two garment solvers.
5. Fixed-step updates and bounded iterations against a measured CPU budget. Test low frame rates,
   hitches, rapid reversals, backpedalling, strafing, casting, full dash distance.
6. Explicit reset or rebase on teleport, respawn, reconnect and large position corrections.
7. A distance or quality fallback: a small bone chain or an authored secondary-motion loop, with
   a clean freeze or blend into it.

Keep thickness and render subdivision from turning into self-collision noise. Separate the inner
robe from the outer cape with real space and a stated collision policy. Full simulation is for a
bounded number of nearby assets; everything else gets the bone fallback.
