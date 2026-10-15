# Patterns (QuPath 0.7.0)

Short idioms, all checked against `references/api`. Imports needed are listed after each snippet;
they go at the bottom of the script.

## Guards

```groovy
def imageData = getCurrentImageData()
if (imageData == null) {
    logger.error('No image open')
    return
}
def cal = imageData.server.pixelCalibration
if (!cal.hasPixelSizeMicrons()) {
    logger.warn('{}: no pixel size, skipped', getCurrentImageName())
    return
}
def tissue = getAnnotationObjects().findAll { it.pathClass == getPathClass('Tissue') }
if (tissue.isEmpty()) {
    logger.warn('{}: no "Tissue" annotation; run 01-threshold-tissue first', getCurrentImageName())
    return
}
```

A top-level `return` ends the script for this image; "Run for project" continues with the next one.

## Objects

```groovy
// Create, then add in one call
def roi = ROIs.createRectangleROI(x, y, w, h, ImagePlane.getDefaultPlane())
def annotation = PathObjects.createAnnotationObject(roi, getPathClass('Region'))
addObjects([annotation])            // flat add
insertObjects([annotation])         // add and resolve parent/child by location

// Children and contained detections
def cells = parent.getChildObjects().findAll { it.isDetection() }
def inside = getCurrentHierarchy().getAllDetectionsForROI(parent.ROI)

// Remove only what this step created earlier; descendants are kept
removeObjects(getAnnotationObjects().findAll { it.pathClass == getPathClass('Region') })
// Remove with descendants (e.g. annotations holding detected cells)
removeObjectsAndDescendants(previous)
```
Imports: `qupath.lib.objects.PathObjects`, `qupath.lib.roi.ROIs`, `qupath.lib.regions.ImagePlane`

## Geometry (JTS)

```groovy
def geom = annotation.ROI.geometry
def ring = geom.buffer(-50 / cal.averagedPixelSizeMicrons)       // 50 µm inward
def roi = GeometryTools.geometryToROI(geom.difference(ring), annotation.ROI.imagePlane)
```
Imports: `qupath.lib.roi.GeometryTools`

## Measurements

```groovy
// Calibrated area, written as a measurement
double areaUm2 = obj.ROI.getScaledArea(cal)
obj.measurements.put('Tissue area µm^2', areaUm2)

// Reading
double v = obj.measurements.get('Num Detections') ?: 0
```
The map view (`getMeasurements()`) is simplest; use `getMeasurementList().put(name, double)` in hot
loops over many detections.
Built-in shape features: `addShapeMeasurements(imageData, objects, 'AREA', 'LENGTH')`.

## Classifiers and built-in commands

```groovy
resetSelection()                     // nothing selected = whole image
createAnnotationsFromPixelClassifier('tissue', minAreaUm2, minHoleAreaUm2, 'SPLIT')

selectObjects(tissue)                // restrict to these parents
addPixelClassifierMeasurements('tissue', 'tissue')
runObjectClassifier('cell-types')
```
Options for `createAnnotationsFromPixelClassifier`: `E PixelClassifierTools.CreateObjectOptions.*`
(`SPLIT`, `DELETE_EXISTING`, `INCLUDE_IGNORED`, `SELECT_NEW`). Classifiers are loaded by name from the
project's `classifiers/` folder.

For built-in commands with many parameters (cell detection, positive cell detection, superpixels...):
ask the user to run the command once in the GUI, then copy the exact `runPlugin(...)` line from
**Workflow → Create script**. Parameter names and defaults are not in the javadoc.

## ImageJ bridge (when QuPath lacks the operation)

```groovy
def server = imageData.server
double downsample = 4
def request = RegionRequest.createInstance(server.path, downsample, parent.ROI)
def imp = IJTools.convertToImagePlus(server, request).image   // calibrated, origin set

IJ.run(imp, 'Gaussian Blur...', 'sigma=2')
imp.processor.setThreshold(threshold, Double.MAX_VALUE)
def ijRoi = ThresholdToSelection.run(imp)
if (ijRoi != null) {
    def roi = IJTools.convertToROI(ijRoi, imp.calibration, downsample, parent.ROI.imagePlane)
    insertObjects([PathObjects.createAnnotationObject(roi, getPathClass('Positive'))])
}
```
Imports: `ij.IJ`, `ij.plugin.filter.ThresholdToSelection`,
`qupath.imagej.tools.IJTools`, `qupath.lib.regions.RegionRequest`, `qupath.lib.objects.PathObjects`

- Choose `downsample` so the region fits in memory; whole-slide regions at downsample 1 will not.
- `IJ.run` command strings and option keys are the ImageJ macro recorder's; they are not in the javadoc.
  Ask the user to record the command in Fiji if unsure.
- Never call anything that opens an ImageJ window (`imp.show()`, `IJ.run` commands with dialogs and no options).

## Export

Per image (runs inside "Run for project"):
```groovy
def outDir = buildFilePath(PROJECT_BASE_DIR, 'results', '02-area-measurements')
mkdirs(outDir)
saveAnnotationMeasurements(buildFilePath(outDir, getCurrentImageName() + '.csv'))
```

Project level (a separate step, run once with **Run**, not "Run for project"):
```groovy
def rows = getProject().imageList.collect { entry ->
    def hierarchy = entry.readHierarchy()
    def tissue = hierarchy.annotationObjects.findAll { it.pathClass == getPathClass('Tissue') }
    [entry.imageName, tissue.sum { it.measurements.get('Tissue area µm^2') ?: 0 } ?: 0]
}
def file = new File(buildFilePath(PROJECT_BASE_DIR, 'results', 'summary.csv'))
file.parentFile.mkdirs()
file.text = (['Image,Tissue area µm^2'] + rows.collect { it.join(',') }).join('\n')
logger.info('Wrote {} rows to {}', rows.size(), file)
```
`readHierarchy()` reads the saved `.qpdata`, so results from images still open with unsaved changes are
not included. Say so in the step header.
