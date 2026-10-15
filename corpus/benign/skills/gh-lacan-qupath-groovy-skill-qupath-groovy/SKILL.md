---
name: qupath-groovy
description: Write, refine and polish Groovy scripts for QuPath 0.7.0 projects that the user runs from QuPath's built-in script editor. Use whenever the user asks for a QuPath script, a QuPath pipeline step, QuPath/ImageJ API usage, or asks to prototype, fix, polish, comment or license a .groovy script for QuPath.
---

# QuPath Groovy scripts

Target: **QuPath 0.7.0** only (`/Applications/QuPath-0.7.0-x64.app`), Groovy 5, ImageJ 1.54p, JTS 1.20.

The user keeps the script open in QuPath's script editor, which reloads the file when it changes on disk.
So: **edit the script file in place**. Never print the script in chat for copy-paste, never create
`script_v2.groovy` copies, never try to run QuPath yourself. The user runs it and reports back
(log output, stack trace, or what they see in the viewer).

## 1. Look up the API before using it

Never guess a method name or signature. The generated references are the source of truth for 0.7.0:

- `references/api/CLASSES.md`: one line per class: `fqcn [kind] summary (file)`. Find the class first.
- `references/api/<jar>.md`: one line per member, grep-friendly:
  `M QP.getAnnotationObjects() -> static Collection<PathObject> // summary` (`M` method, `C` constructor, `F` field, `E` enum constant).

```bash
R=.claude/skills/qupath-groovy/references/api
grep -h '^M QP\.\w*Annotation' $R/*.md          # QP/QPEx scripting helpers
grep -h '^C new ParticleAnalyzer' $R/ij-*.md     # ImageJ constructors
grep -h '^E RoiTools.CombineOp' $R/*.md          # enum constants
grep 'RoiTools\|IJTools' $R/CLASSES.md           # which class, which jar
```

Summaries are first sentences only; for parameters, units and exceptions print the full javadoc:
`python3 -I .claude/skills/qupath-groovy/scripts/show_doc.py QP createAnnotationsFromPixelClassifier`.

`QPEx` extends `QP`: search `QP.` and `QPEx.` both. A summary of `Deprecated.` means find the replacement.
Prefer QuPath API; drop to ImageJ (`ij-1.54p.md`) via `IJTools` only when QuPath lacks the operation.
Prose docs live in `qupath-docs/docs/` (scripting/, tutorials/) at the repository root.
To regenerate the API files after an upgrade: `python3 -I .claude/skills/qupath-groovy/scripts/dump_api.py <QuPath.app>`.

## 2. One script = one step between human checkpoints

A pipeline is a sequence of steps. **A step ends where the user must inspect or correct results.**
Example: `01-threshold-tissue` (user inspects and fixes tissue outlines) then `02-area-measurements`.

- Each step lives in its own folder, named `NN-kebab-name/`, holding `NN-kebab-name.groovy`.
- A step is fully unattended: no dialogs, `promptForFile`, `Dialogs.*`, waits, or "check this then continue".
  If the logic needs a human decision in the middle, split it into two steps.
- Written for **Run → Run for project**: it processes the *current image* only; QuPath loops over
  images and saves each `.qpdata`. Only project-level steps (e.g. aggregating results) loop over
  `getProject().getImageList()`, and they say so in their header.
- Re-runnable: before creating its objects/measurements, a step removes what *it* created on a previous
  run (identify them by class/name). It never touches what earlier steps or the user produced, since
  that is the user's validated work.
- Inputs come from earlier steps (by class name, measurement name, file under `PROJECT_BASE_DIR`);
  state them in the header. Outputs go to `buildFilePath(PROJECT_BASE_DIR, 'results', '<step-folder>')`.

## 3. Code layout (every phase)

Read `references/conventions.md` for the full template. Essentials:

1. Header comment (one line in prototype, full block when polished).
2. `// Settings` block: every tunable value, in calibrated units (µm, µm²), with its unit in the name.
3. Main logic, top to bottom, readable as a recipe.
4. Helper methods (settings are script locals and are **not** visible in methods: pass them as arguments).
5. **Imports at the very bottom**, always including `import static qupath.lib.gui.scripting.QPEx.*`
   so the script never depends on the editor's "Include default imports" toggle.

Logging: **never `println`/`print`**. Use the QuPath (SLF4J) logger declared at the bottom:
`@Field final Logger logger = getLogger()`, then `logger.info("Created {} annotations", n)`.
`info` for normal progress (one summary line per image), `warn` for skipped images, `error` before an early `return`.

## 4. Phases

**Prototype (default).** Fast iteration with the user. Comments are short labels (a few words) on
logical blocks only, never one per line. No license, no doc comments. One-line header with step
name and purpose. Keep the code as short as clarity allows; fix by editing in place.

**Polish (only when the user asks: "polish", "finalize", "document", "add license").**
1. Re-read the whole script; simplify anything left over from iteration; remove dead code.
2. Replace the header with the full block (see conventions) including the license from
   `license-header.txt` (BSD-3-Clause by default; full text in `LICENSE` at the repository root).
   Use another license only if the user asks for one for that script.
3. Rewrite comments to explain **why**, not how: the reason for a threshold, an ordering constraint,
   a QuPath quirk being worked around. Delete comments that restate the code.
4. Add a short Groovydoc to each helper method: what it returns and any non-obvious contract.
5. Do not change behaviour while polishing. If you spot a bug, tell the user instead of silently fixing it.

## 5. Before handing back

- Every API call you used exists in `references/api` with the arguments you pass.
- No `println`, no GUI calls (`getQuPath()`, `getCurrentViewer()`, dialogs) unless the user asked for one.
- Guards for: no image open, missing pixel calibration, missing inputs from previous steps.
- Tell the user in one or two lines what to run (Run vs Run for project) and what to inspect afterwards.

See `references/patterns.md` for idioms (objects, measurements, classifiers, ImageJ bridge, export)
and `references/pitfalls.md` for common mistakes in 0.7.0.
