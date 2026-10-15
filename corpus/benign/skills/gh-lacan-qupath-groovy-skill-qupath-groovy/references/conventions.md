# Script conventions

## Folder layout

```
<pipeline>/
├── 01-threshold-tissue/
│   └── 01-threshold-tissue.groovy
├── 02-area-measurements/
│   └── 02-area-measurements.groovy
└── 03-export-results/
    └── 03-export-results.groovy
```

The number gives the run order; the name says what the step does (verb + object).
Anything else a step needs (a classifier JSON, a small lookup CSV) sits next to its script.
Classifiers trained in QuPath stay in the project (`classifiers/`) and are loaded by name.

## Prototype template

```groovy
// 01 Threshold tissue: create "Tissue" annotations with the project pixel classifier.

// Settings
def classifierName = 'tissue'
def tissueClass = 'Tissue'
double minAreaUm2 = 50_000
double minHoleAreaUm2 = 5_000

// Checks
def imageData = getCurrentImageData()
if (imageData == null) {
    logger.error('No image open')
    return
}

// Remove previous run
def previous = getAnnotationObjects().findAll { it.pathClass == getPathClass(tissueClass) }
removeObjects(previous)

// Detect
resetSelection()
createAnnotationsFromPixelClassifier(classifierName, minAreaUm2, minHoleAreaUm2, 'SPLIT')

def tissue = getAnnotationObjects().findAll { it.pathClass == getPathClass(tissueClass) }
logger.info('{}: {} tissue region(s), {} µm² total', getCurrentImageName(), tissue.size(),
        String.format('%.0f', totalAreaUm2(tissue, imageData.server.pixelCalibration)))

// Helpers
double totalAreaUm2(Collection<PathObject> objects, PixelCalibration cal) {
    objects.sum { it.ROI.getScaledArea(cal) } ?: 0d
}

// Imports
import static qupath.lib.gui.scripting.QPEx.*
import groovy.transform.Field
import org.slf4j.Logger
import qupath.lib.images.servers.PixelCalibration
import qupath.lib.objects.PathObject

@Field final Logger logger = getLogger()
```

Notes:
- `@Field` turns `logger` into a script field so helper methods can use it too. It is initialized when
  the script object is created, so it may sit at the bottom with the imports.
- Settings are plain locals: pass them to helpers as arguments rather than making them `@Field`s,
  so each helper declares what it depends on.
- Use typed declarations (`double`, `int`, `Collection<PathObject>`) for settings and helper signatures;
  `def` is fine for short-lived locals.
- Prefer Groovy collection methods (`findAll`, `collect`, `groupBy`, `sum`) over manual loops.
- Prefer one bulk call (`addObjects`, `removeObjects`) over per-object calls in a loop: each per-object
  call fires a hierarchy event, which is slow on large images.

## Polished header

```groovy
/**
 * 01 Threshold tissue
 *
 * Creates "Tissue" annotations from the project pixel classifier "tissue".
 *
 * Run:       Run for project
 * Requires:  pixel classifier "tissue" saved in the project
 * Produces:  annotations of class "Tissue"; removes "Tissue" annotations from earlier runs
 * Checkpoint: inspect every image, fix outlines by hand before running 02-area-measurements
 *
 * QuPath 0.7.0
 *
 * <license-header.txt, with {YEAR} filled in>
 */
```

## Comment style in the polished phase

Write why, not how. The code already says how.

```groovy
// Bad (restates the code)
// Remove the previous tissue annotations
removeObjects(previous)

// Good (explains the reason)
// Re-running must not stack duplicates on top of the user's corrected outlines
removeObjects(previous)
```

```groovy
// Good: records a decision that is not visible in the code
// 50'000 µm² drops dust and coverslip debris while keeping the smallest biopsy fragments
double minAreaUm2 = 50_000
```

Helper methods get a short Groovydoc:

```groovy
/** Summed calibrated area (µm²) of the objects' ROIs; 0 when the collection is empty. */
double totalAreaUm2(Collection<PathObject> objects, PixelCalibration cal) { ... }
```
