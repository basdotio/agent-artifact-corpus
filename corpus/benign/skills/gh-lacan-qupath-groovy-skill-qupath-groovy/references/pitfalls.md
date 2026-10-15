# Pitfalls (QuPath 0.7.0)

## API
- **Deprecated since 0.6:** `removeObjects(objs, keepChildren)`, `removeObject(obj, keepChildren)`,
  `clearSelectedObjects`, `clearAllObjects`, `createSelectAllObject`. Use `removeObjects(objs)` (keeps
  descendants), `removeObjectsAndDescendants(objs)`, `createFullImageAnnotation(true)`.
- **Summaries are not enough:** the API dump keeps only first sentences. Run
  `python3 -I .claude/skills/qupath-groovy/scripts/show_doc.py <Class> <member>` whenever units,
  nullability or argument meaning matter (e.g. calibrated vs pixel areas).
- **Old forum snippets:** scripts written for 0.1/0.2 (`getPathClass(...).toString()`, `PathAnnotationObject` constructors,
  `QPEx.getCurrentImageData().getServer().getPixelHeightMicrons()`) often no longer compile. Check each
  call against `references/api` before reusing.
- **Overloads and `[]`:** Groovy cannot always pick between `Collection` and varargs overloads when passed an
  empty list. Use the dedicated method instead (`resetSelection()` rather than `selectObjects([])`).

## Script structure
- **Settings are locals:** variables declared with `def`/a type at top level are not visible inside methods.
  Pass them as arguments. Only `logger` is a `@Field`.
- **Variables without `def`** go into the script binding instead of being locals. Always declare them.
- **Imports at the bottom are fine** in Groovy; every script still needs the explicit
  `import static qupath.lib.gui.scripting.QPEx.*`.

## Hierarchy
- **Bulk over loops:** `addObject`/`removeObject` in a loop fires one event per object: very slow on images
  with many detections. Collect, then call `addObjects`/`removeObjects` once.
- **`addObjects` does not resolve parents.** Use `insertObjects` (or `resolveHierarchy()` afterwards)
  when downstream steps rely on `getChildObjects()`.
- **Selection matters:** many QP commands (`createAnnotationsFromPixelClassifier`, `runPlugin`,
  `addPixelClassifierMeasurements`) act on the *selected* objects, or the whole image if none. Always set
  the selection explicitly right before such a call.
- **`fireHierarchyUpdate()`** after modifying ROIs, classes or measurements of existing objects directly,
  so the viewer and measurement tables refresh.

## Batch ("Run for project")
- It saves every image's `.qpdata` after the script, overwriting. A step that should not modify data
  (pure export) should be run with "Run for project (without save)"; say so in its header.
- No GUI: `getCurrentViewer()`, `getQuPath()`, dialogs and `imp.show()` either fail or block batch runs.
- The image currently open in the viewer is processed too; unsaved changes on it are saved by the run.
- A project-level step that reads other images (`entry.readHierarchy()`) only sees saved data.

## Units
- Measurement names carry units, e.g. `Area µm^2`; QuPath writes `µm` with the micro sign, not `u`.
- `ROI.getArea()` is in pixels². Use `ROI.getScaledArea(cal)` for µm².
- Distances for JTS `buffer` are in pixels: divide µm by `cal.averagedPixelSizeMicrons`.
