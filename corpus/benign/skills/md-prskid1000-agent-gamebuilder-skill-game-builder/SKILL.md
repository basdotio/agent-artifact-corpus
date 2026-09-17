---
name: game-builder
description: >
  Universal Godot 4 game building skill. Covers ALL game genres: 2D (top-down,
  platformer, side-scroller, puzzle), 3D (FPS, TPS, voxel, racing, open-world),
  and all gameplay systems (combat, inventory, AI, dialogue, save/load, audio,
  multiplayer). Every code hint references .docs/ for correct Godot API syntax.
  Diagnoses what the user wants, routes to the correct architecture, and builds
  production-quality games step by step.
---

# Game Builder — Universal Godot 4 Skill

Builds any type of game in Godot 4. Routes to the correct architecture based on
what the user describes, then follows structured build plans with .docs-verified
API usage.

---

## Quick Start — What Are You Building?

```
What dimension?
+-- 2D
|   +-- Side-view with gravity/jumping?  -> 2D Platformer
|   +-- Top-down movement (8-dir)?       -> 2D Top-Down (RPG/adventure/farming)
|   +-- Side-scrolling (no platforming)? -> 2D Side-Scroller (beat-em-up/shooter)
|   +-- Grid/tile-based logic?           -> 2D Puzzle / Strategy
|   +-- Physics-driven?                  -> 2D Physics Game
|
+-- 3D
|   +-- First-person view?              -> 3D FPS / First-Person
|   +-- Third-person camera?            -> 3D TPS / Action-Adventure
|   +-- Block placing / voxel world?    -> 3D Voxel (Minecraft-like)
|   +-- Vehicle / racing?               -> 3D Racing
|   +-- Open world exploration?         -> 3D Open-World
|
+-- Not sure -> Describe your game and I'll route you
```

### Genre -> Architecture Map

| Genre | Dimension | Architecture | Reference |
|-------|-----------|-------------|-----------|
| Platformer (Mario, Celeste, Hollow Knight) | 2D | CharacterBody2D Grounded mode | 2d-games.md > Platformer |
| Top-down RPG (Zelda, Hades) | 2D | CharacterBody2D Floating mode | 2d-games.md > Top-Down |
| Farming sim (Stardew Valley) | 2D | Top-down + TileMap + day cycle | 2d-games.md > Top-Down |
| Metroidvania | 2D | Platformer + interconnected map | 2d-games.md > Platformer |
| Bullet hell / twin-stick shooter | 2D | Top-down + projectile pool | 2d-games.md > Top-Down |
| Puzzle / match-3 / grid-based | 2D | Grid array + TileMapLayer | 2d-games.md > Puzzle/Grid |
| Visual novel / dialogue-heavy | 2D | Control nodes + dialogue system | game-systems.md > Dialogue |
| Beat-em-up / side-scroll action | 2D | Side-scroller + combat | 2d-games.md > Side-Scroller |
| Tower defense | 2D | Top-down + path follow + waves | 2d-games.md > Top-Down |
| FPS (Doom, Half-Life) | 3D | CharacterBody3D + Camera3D | 3d-games.md > First-Person |
| Third-person action (Souls-like) | 3D | CharacterBody3D + SpringArm3D | 3d-games.md > Third-Person |
| Voxel / Minecraft-like | 3D | Chunk system + ArrayMesh | 3d-games.md > Voxel |
| Racing (arcade or sim) | 3D | VehicleBody3D or RigidBody3D | 3d-games.md > Racing |
| 3D platformer (Mario 64) | 3D | CharacterBody3D + Camera3D orbit | 3d-games.md > Third-Person |
| Horror / stealth | 3D/2D | FPS or TPS + AI detection | 3d-games.md + game-systems.md > AI |
| Survival crafting | 3D | Voxel/open-world + inventory + crafting | 3d-games.md + game-systems.md |
| Multiplayer | Any | ENet/WebSocket/WebRTC | game-systems.md > Multiplayer |

---

## Reference Files

| File | What It Covers |
|------|---------------|
| [Godot Foundations](references/godot-foundations.md) | Core Godot concepts, ALL .docs paths, engine guide, project setup patterns, asset prompts |
| [2D Games](references/2d-games.md) | Platformer, top-down, side-scroller, puzzle/grid — scene trees, movement, physics, cameras |
| [3D Games](references/3d-games.md) | First-person, third-person, voxel, racing, open-world — scene trees, cameras, shaders |
| [Game Systems](references/game-systems.md) | Combat, AI, inventory, dialogue, quests, save/load, audio, UI, multiplayer, day/night |

---

## Universal Build Workflow

Every game follows this order regardless of genre:

### Phase 1: Foundation
1. Project settings (resolution, renderer, texture filter, physics engine)
2. Input map (all actions with keyboard + controller bindings)
3. Physics/collision layers (named in Project Settings)
4. Autoloads (Enum, Data, EventBus as needed)
5. Folder structure: `audio/`, `global/`, `graphics/`, `scenes/`, `shaders/`, `resources/`

### Phase 2: Player
6. Player scene (CharacterBody2D or CharacterBody3D)
7. Movement system (genre-appropriate: platformer gravity, top-down 8-dir, FPS mouselook)
8. Animation system (AnimationTree for 2D directional, AnimationPlayer for 3D)
9. Camera (Camera2D smooth follow, Camera3D with SpringArm3D, etc.)

### Phase 3: World
10. Level/world scene structure
11. Terrain system (TileMapLayer for 2D, mesh/voxel for 3D)
12. Navigation (NavigationRegion2D/3D for enemy pathfinding)
13. Level transitions or chunk loading

### Phase 4: Gameplay
14. Core mechanic (combat, farming, building, puzzles — genre-specific)
15. Enemy/NPC AI (state machine or behavior tree)
16. Items, inventory, resources

### Phase 5: Polish
17. UI/HUD (health bars, menus, dialogue)
18. Audio (SFX pooling, music crossfade)
19. Save/load system
20. VFX, shaders, screen effects
21. Playtesting and balance

---

## .docs Godot API Reference (ALWAYS USE)

**CRITICAL:** Before writing ANY Godot API call, verify the correct syntax in `.docs/godot-docs-md/`. The agent MUST reference these docs for every class, method, property, and signal used. This prevents incorrect API usage.

### Most-Used Class References

| Class | .docs Path | Used For |
|-------|-----------|----------|
| CharacterBody2D | `.docs/godot-docs-md/classes/class_characterbody2d.md` | 2D player/enemy movement |
| CharacterBody3D | `.docs/godot-docs-md/classes/class_characterbody3d.md` | 3D player/enemy movement |
| RigidBody2D | `.docs/godot-docs-md/classes/class_rigidbody2d.md` | Physics-driven 2D objects |
| RigidBody3D | `.docs/godot-docs-md/classes/class_rigidbody3d.md` | Physics-driven 3D objects |
| StaticBody2D | `.docs/godot-docs-md/classes/class_staticbody2d.md` | Non-moving 2D colliders |
| StaticBody3D | `.docs/godot-docs-md/classes/class_staticbody3d.md` | Non-moving 3D colliders |
| Area2D | `.docs/godot-docs-md/classes/class_area2d.md` | Triggers, hitboxes, pickups |
| Area3D | `.docs/godot-docs-md/classes/class_area3d.md` | 3D triggers and detection |
| AnimationTree | `.docs/godot-docs-md/classes/class_animationtree.md` | Complex animation blending |
| AnimationPlayer | `.docs/godot-docs-md/classes/class_animationplayer.md` | Direct animation playback |
| TileMapLayer | `.docs/godot-docs-md/classes/class_tilemaplayer.md` | 2D tile-based levels |
| NavigationAgent2D | `.docs/godot-docs-md/classes/class_navigationagent2d.md` | 2D enemy pathfinding |
| NavigationAgent3D | `.docs/godot-docs-md/classes/class_navigationagent3d.md` | 3D enemy pathfinding |
| Camera2D | `.docs/godot-docs-md/classes/class_camera2d.md` | 2D camera follow/limits |
| Camera3D | `.docs/godot-docs-md/classes/class_camera3d.md` | 3D camera |
| SpringArm3D | `.docs/godot-docs-md/classes/class_springarm3d.md` | TPS camera collision |
| RayCast2D | `.docs/godot-docs-md/classes/class_raycast2d.md` | 2D line-of-sight/interaction |
| RayCast3D | `.docs/godot-docs-md/classes/class_raycast3d.md` | 3D aiming/block interaction |
| Input | `.docs/godot-docs-md/classes/class_input.md` | Input reading |
| VehicleBody3D | `.docs/godot-docs-md/classes/class_vehiclebody3d.md` | Racing vehicle physics |
| VehicleWheel3D | `.docs/godot-docs-md/classes/class_vehiclewheel3d.md` | Wheel physics |
| ArrayMesh | `.docs/godot-docs-md/classes/class_arraymesh.md` | Custom mesh generation |
| FastNoiseLite | `.docs/godot-docs-md/classes/class_fastnoiselite.md` | Procedural generation |
| WorkerThreadPool | `.docs/godot-docs-md/classes/class_workerthreadpool.md` | Async heavy tasks |
| Resource | `.docs/godot-docs-md/classes/class_resource.md` | Custom data containers |
| Texture2DArray | `.docs/godot-docs-md/classes/class_texture2darray.md` | Spritesheet arrays |
| ShaderMaterial | `.docs/godot-docs-md/classes/class_shadermaterial.md` | Custom shaders |
| MultiplayerAPI | `.docs/godot-docs-md/classes/class_multiplayerapi.md` | Networking |
| ENetMultiplayerPeer | `.docs/godot-docs-md/classes/class_enetmultiplayerpeer.md` | ENet networking |
| Mutex | `.docs/godot-docs-md/classes/class_mutex.md` | Thread safety |
| FileAccess | `.docs/godot-docs-md/classes/class_fileaccess.md` | File I/O for saves |
| JSON | `.docs/godot-docs-md/classes/class_json.md` | JSON serialization |
| Tween | `.docs/godot-docs-md/classes/class_tween.md` | Code-based animation |
| Timer | `.docs/godot-docs-md/classes/class_timer.md` | Timed events |
| GPUParticles2D | `.docs/godot-docs-md/classes/class_gpuparticles2d.md` | 2D particle effects |
| GPUParticles3D | `.docs/godot-docs-md/classes/class_gpuparticles3d.md` | 3D particle effects |

### Key Tutorials

| Topic | .docs Path |
|-------|-----------|
| Using CharacterBody2D | `.docs/godot-docs-md/tutorials/physics/using_character_body_2d.md` |
| Input handling | `.docs/godot-docs-md/tutorials/inputs/input_examples.md` |
| Physics introduction | `.docs/godot-docs-md/tutorials/physics/physics_introduction.md` |
| 3D transforms | `.docs/godot-docs-md/tutorials/3d/using_transforms.md` |
| Singletons/Autoload | `.docs/godot-docs-md/tutorials/scripting/singletons_autoload.md` |
| Signals | `.docs/godot-docs-md/tutorials/scripting/gdscript/gdscript_signals.md` |
| GDScript basics | `.docs/godot-docs-md/tutorials/scripting/gdscript/gdscript_basics.md` |
| High-level multiplayer | `.docs/godot-docs-md/tutorials/networking/high_level_multiplayer.md` |
| Project organization | `.docs/godot-docs-md/tutorials/best_practices/project_organization.md` |
| 3D spring arm camera | `.docs/godot-docs-md/tutorials/3d/spring_arm.md` |

---

## Mandatory Guidelines

### .docs Verification Rule

**Every line of Godot API code must be verifiable against .docs.** Before using any class, method, or property:
1. Check `.docs/godot-docs-md/classes/class_[name].md` for correct signature
2. Verify parameter types and return types
3. Check for deprecated methods (Godot 4 renamed many things from Godot 3)
4. Cite the .docs path in code comments when using non-obvious API

### Incremental Verification

After every build phase, the game must run cleanly:
1. Run project (F5) — confirm main scene loads
2. No runtime or parse errors in Output/Debugger
3. New behavior is testable
4. Fix errors before proceeding

### Animation Standard (2D)

- Horizontal frame strips per action/direction
- Set h_frames/v_frames on Sprite2D
- Prefer flip_h for left-facing
- `.docs/godot-docs-md/classes/class_sprite2d.md` for frame properties

### Asset Prompt Generation (ComfyUI)

Generate independent prompts for: OpenDUI (text-to-image), Flux Kontext (image edit), Chatterbox TTS (text-to-speech). One prompt per asset, no "same as above". Details in godot-foundations.md.

---

## Example Reference Files

Working examples live in `.examples/`:
- `.examples/godot-valley/` — 2D farming/life-sim
- `.examples/godot-craft/` — 3D voxel open-world
- `.examples/godot-craft/addons/godot-sqlite/` — SQLite addon (copy for voxel games)
