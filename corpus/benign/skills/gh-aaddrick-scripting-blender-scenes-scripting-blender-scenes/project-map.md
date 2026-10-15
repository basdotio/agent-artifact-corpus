# Writing a project map

Every rule in this skill assumes you can find the project's build entry point, its generators and its checks. Agents that skipped this wrote new modellers for parts that already had generators. Write the map as a project skill (`.claude/skills/<project>/SKILL.md` that says "REQUIRED: use scripting-blender-scenes") or as a `CLAUDE.md` section. Keep it to facts an agent can't derive quickly.

## On a Quick job: five lines

A one-off diagnosis, a single prop or a small fix needs a note, not a map. It can sit at the top of your working notes or in `CLAUDE.md`:

```
Build: <command that rebuilds or renders, or "none: one-off script">
Conventions: <units, up axis, forward axis; hinge axes and which sign opens>
Outputs: <where files go; what is client-bound>
Risks in the brief: <the 1–3 things that could be wrong, e.g. contact, z-fighting, frame count>
Checks: <how each risk is measured, and the tolerance>
```

On a Standard job, start from these five lines and add only the sections below that the job uses. Grow it into the full map once a second agent, a second session or a second deliverable depends on it.

## What to record

| Section | Contents |
|---|---|
| **Build** | The one command that rebuilds the scene from scripts; module order; how to write a scene hash; environment variables and toggles, with the values the final render uses |
| **Conventions** | Units, up axis, forward axis, which side is `.L`, hinge axis and sign, object and bone naming patterns, the rig contract file |
| **Generators and guards** | Where each kind of geometry is generated (shells, cuts, detail layers), and which guards they already run |
| **Shared check libraries** | Clash and penetration, extent regression, mirror and side, shape gate, rig integrity, contract check, joint sweep, physics, determinism, still metrics. Give each one's command line and its self-test |
| **Thresholds in force** | Each limit with its value and where it is declared, including exception lists. Flag any exception tolerance equal to the limit it guards |
| **Local environment** | Blender build and version, GPU and device quirks, locks or slots for shared hardware, typical build and render times |
| **Known issues** | Parked defects and accepted failures, with where each is written up |
| **Where checks live** | The folder for per-change checks and verdicts, and where reusable checks get promoted |

## Rules for the map

- Record a path only after confirming it exists.
- Prefer one shared library per measurement over several near-duplicates. If the project has duplicates, name the one to use.
- Update the map in the same change that moves or adds a tool.
- Put incident history (what went wrong, with IDs) in a separate file, so agents load it only when tracing a decision.
