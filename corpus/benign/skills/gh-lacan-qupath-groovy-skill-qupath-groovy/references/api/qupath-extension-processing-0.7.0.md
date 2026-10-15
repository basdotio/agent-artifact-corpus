# qupath-extension-processing-0.7.0

## qupath.imagej.gui.IJExtension.IJExtensionCommands [Class]
Commands to install with the ImageJ extension.
F IJExtension.IJExtensionCommands.actionCellDetection -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionCellMembraneDetection -> final org.controlsfx.control.action.Action // Deprecated.
F IJExtension.IJExtensionCommands.actionDoG -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionExtractRegion -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionImageJDirectory -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionImportROIs -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionLegacyMacroRunner -> final org.controlsfx.control.action.Action // Deprecated.
F IJExtension.IJExtensionCommands.actionPixelCount -> final org.controlsfx.control.action.Action // Deprecated.
F IJExtension.IJExtensionCommands.actionPositiveCellDetection -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionScriptRunner -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionShowImageJ -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionSimpleTissueDetection -> final org.controlsfx.control.action.Action // Deprecated.
F IJExtension.IJExtensionCommands.actionSLIC -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionSnapshot -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.actionSubcellularDetection -> final org.controlsfx.control.action.Action // Deprecated.
F IJExtension.IJExtensionCommands.actionTiles -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.SEP_0 -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.SEP_1 -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.SEP_2 -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.SEP_2B -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.SEP_3 -> final org.controlsfx.control.action.Action // 
F IJExtension.IJExtensionCommands.SEP_4 -> final org.controlsfx.control.action.Action // 

## qupath.imagej.gui.IJExtension [Class]
QuPath extension & associated static helper methods used to support integration of ImageJ with QuPath.
C new Description -> Constructor // 
C new IJExtension() // 
M IJExtension.extractOverlay(qupath.lib.objects.hierarchy.PathObjectHierarchy hierarchy, qupath.lib.regions.RegionRequest request, qupath.lib.gui.viewer.OverlayOptions options, Predicate<qupath.lib.objects.PathObject> filter) -> static Overlay // Extract an ImageJ overlay for the specified region.
M IJExtension.extractROI(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.objects.PathObject pathObject, qupath.lib.regions.RegionRequest request, boolean setROI) -> static qupath.lib.images.PathImage<ImagePlus> // Similar to extractROI(ImageServer, ROI, RegionRequest, boolean), except that the title of the ImagePlus is set according to the parent object type (which is used to get the ROI).
M IJExtension.extractROI(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.roi.interfaces.ROI pathROI, qupath.lib.regions.RegionRequest request, boolean setROI) -> static qupath.lib.images.PathImage<ImagePlus> // Extract a region of interest from an image as an ImageJ ImagePlus.
M IJExtension.extractROIWithOverlay(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.objects.PathObject pathObject, qupath.lib.objects.hierarchy.PathObjectHierarchy hierarchy, qupath.lib.regions.RegionRequest request, boolean setROI, qupath.lib.gui.viewer.OverlayOptions options) -> static qupath.lib.images.PathImage<ImagePlus> // Extract an image region as an ImagePlus, optionally setting ImageJ Rois corresponding to QuPath objects.
M IJExtension.getDescription() -> String // 
M IJExtension.getImageJIcon(int width, int height) -> static Image // Try to read the ImageJ icon from its jar.
M IJExtension.getImageJInstance() -> static ImageJ // Get an instance of ImageJ, or start one, for interactive use (with GUI displayed).
M IJExtension.getImageJPath() -> static String // Get the path for a local ImageJ installation, if set.
M IJExtension.getName() -> String // 
M IJExtension.getQuPathVersion() -> qupath.lib.common.Version // Returns the version stored within this jar, because it is matched to the QuPath version.
M IJExtension.imageJPathProperty() -> static StringProperty // Property representing the path to a local ImageJ installation, or null if no path has been set.
M IJExtension.installExtension(qupath.lib.gui.QuPathGUI qupath) -> void // 
M IJExtension.setImageJPath(String path) -> static void // Set the path for a local ImageJ installation, if required.

## qupath.imagej.gui.ImageJMacroRunner [Class]
QuPath plugin for running ImageJ macros & returning detected regions.
C new Description -> Constructor // 
C new ImageJMacroRunner(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M ImageJMacroRunner.getDescription() -> String // Deprecated.
M ImageJMacroRunner.getLastResultsDescription() -> String // Deprecated.
M ImageJMacroRunner.getName() -> String // Deprecated.
M ImageJMacroRunner.runPlugin(qupath.lib.plugins.TaskRunner runner, qupath.lib.images.ImageData<BufferedImage> imageData, String arg) -> boolean // Deprecated.

## qupath.imagej.gui.scripts.ImageJScriptRunner.ApplyToObjects [Enum]
Enum representing the objects that the script should be applied to.
E ImageJScriptRunner.ApplyToObjects.ANNOTATIONS // 
E ImageJScriptRunner.ApplyToObjects.CELLS // 
E ImageJScriptRunner.ApplyToObjects.DETECTIONS // 
E ImageJScriptRunner.ApplyToObjects.IMAGE // 
E ImageJScriptRunner.ApplyToObjects.SELECTED // 
E ImageJScriptRunner.ApplyToObjects.TILES // 
E ImageJScriptRunner.ApplyToObjects.TMA_CORES // 
M ImageJScriptRunner.ApplyToObjects.toString() -> String // 
M ImageJScriptRunner.ApplyToObjects.valueOf(String name) -> static ImageJScriptRunner.ApplyToObjects // Returns the enum constant of this class with the specified name.
M ImageJScriptRunner.ApplyToObjects.values() -> static ImageJScriptRunner.ApplyToObjects[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.imagej.gui.scripts.ImageJScriptRunner.Builder [Class]

M ImageJScriptRunner.Builder.addToWorkflow() -> ImageJScriptRunner.Builder // Request that the script is stored in the workflow history when it is run for an ImageData.
M ImageJScriptRunner.Builder.addToWorkflow(boolean doAdd) -> ImageJScriptRunner.Builder // Optionally request that the script is stored in the workflow history when it is run for an ImageData.
M ImageJScriptRunner.Builder.applyToObjects(ImageJScriptRunner.ApplyToObjects objectType) -> ImageJScriptRunner.Builder // Specify the objects that the script should be applied to.
M ImageJScriptRunner.Builder.build() -> ImageJScriptRunner // Build a new ImageJScriptRunner with the parameters specified in this builder.
M ImageJScriptRunner.Builder.channelIndices(int... inds) -> ImageJScriptRunner.Builder // Optionally specify a subset of image channels to pass to ImageJ.
M ImageJScriptRunner.Builder.channelNames(String... names) -> ImageJScriptRunner.Builder // Optionally specify a subset of image channels to pass to ImageJ, based on channel names.
M ImageJScriptRunner.Builder.channels(Collection<? extends qupath.lib.images.servers.ColorTransforms.ColorTransform> channels) -> ImageJScriptRunner.Builder // Optionally specify channels to pass to ImageJ.
M ImageJScriptRunner.Builder.channels(qupath.lib.images.servers.ColorTransforms.ColorTransform channel, qupath.lib.images.servers.ColorTransforms.ColorTransform... channels) -> ImageJScriptRunner.Builder // Optionally specify channels to pass to ImageJ.
M ImageJScriptRunner.Builder.clearChildObjects() -> ImageJScriptRunner.Builder // Request that the child objects are removed from any objects that are passed to the script runner.
M ImageJScriptRunner.Builder.clearChildObjects(boolean doClear) -> ImageJScriptRunner.Builder // Optionally request that the child objects are removed from any objects that are passed to the script runner.
M ImageJScriptRunner.Builder.closeOpenImages(boolean doClose) -> ImageJScriptRunner.Builder // Request that any images left open after the macro are closed.
M ImageJScriptRunner.Builder.downsample(qupath.lib.images.servers.downsamples.DownsampleCalculator downsample) -> ImageJScriptRunner.Builder // Specify how images should be downsampled when passing them to ImageJ.
M ImageJScriptRunner.Builder.file(String path) -> ImageJScriptRunner.Builder // Specify the path to a file containing the script or macro.
M ImageJScriptRunner.Builder.fixedDownsample(double downsample) -> ImageJScriptRunner.Builder // Use a fixed downsample value when passing images to ImageJ.
M ImageJScriptRunner.Builder.groovyText(String groovy) -> ImageJScriptRunner.Builder // Specify the exact text for an ImageJ macro.
M ImageJScriptRunner.Builder.macroText(String macroText) -> ImageJScriptRunner.Builder // Specify the exact text for an ImageJ macro.
M ImageJScriptRunner.Builder.maxDimension(int maxDim) -> ImageJScriptRunner.Builder // Resize images to have a width and height ≤ a specified value when passing images to ImageJ.
M ImageJScriptRunner.Builder.nThreads(int nThreads) -> ImageJScriptRunner.Builder // Specify the number of parallel threads to use.
M ImageJScriptRunner.Builder.overlayToAnnotations() -> ImageJScriptRunner.Builder // Convert Rois on the overlay of the current image at the end of the script to QuPath annotation objects.
M ImageJScriptRunner.Builder.overlayToDetections() -> ImageJScriptRunner.Builder // Convert Rois on the overlay of the current image at the end of the script to QuPath detection objects.
M ImageJScriptRunner.Builder.overlayToObjects(ImageJScriptRunner.PathObjectType type) -> ImageJScriptRunner.Builder // Convert Rois on the overlay of the current image at the end of the script to the specified QuPath object type.
M ImageJScriptRunner.Builder.overlayToTiles() -> ImageJScriptRunner.Builder // Convert Rois on the overlay of the current image at the end of the script to QuPath tile objects.
M ImageJScriptRunner.Builder.padding(int padding) -> ImageJScriptRunner.Builder // Specify how much padding to add around the ROI.
M ImageJScriptRunner.Builder.pixelSize(qupath.lib.images.servers.PixelCalibration targetCalibration) -> ImageJScriptRunner.Builder // Resize images to have a target pixel value when passing images to ImageJ.
M ImageJScriptRunner.Builder.pixelSizeMicrons(double pixelSizeMicrons) -> ImageJScriptRunner.Builder // Resize images to have a target pixel value in µm when passing images to ImageJ.
M ImageJScriptRunner.Builder.roiToAnnotation() -> ImageJScriptRunner.Builder // Convert any active Roi at the end of the script to a QuPath annotation object.
M ImageJScriptRunner.Builder.roiToDetection() -> ImageJScriptRunner.Builder // Convert any active Roi at the end of the script to a QuPath detection object.
M ImageJScriptRunner.Builder.roiToObject(ImageJScriptRunner.PathObjectType type) -> ImageJScriptRunner.Builder // Convert any active Roi at the end of the script to the specified QuPath object type.
M ImageJScriptRunner.Builder.roiToTile() -> ImageJScriptRunner.Builder // Convert any active Roi at the end of the script to a QuPath tile object.
M ImageJScriptRunner.Builder.scriptEngine(String scriptEngine) -> ImageJScriptRunner.Builder // Specify the name of any script engine to use.
M ImageJScriptRunner.Builder.scriptFile(File file) -> ImageJScriptRunner.Builder // Specify a file containing the script or macro.
M ImageJScriptRunner.Builder.scriptFile(Path path) -> ImageJScriptRunner.Builder // Specify a path to the script or macro.
M ImageJScriptRunner.Builder.setImageJOverlay() -> ImageJScriptRunner.Builder // Add any QuPath objects within the field of view to an ImageJ overlay.
M ImageJScriptRunner.Builder.setImageJOverlay(boolean doSet) -> ImageJScriptRunner.Builder // Optionally add any QuPath objects within the field of view to an ImageJ overlay.
M ImageJScriptRunner.Builder.setImageJRoi() -> ImageJScriptRunner.Builder // Set the ROI for the QuPath object being set as a Roi on the ImagePlus.
M ImageJScriptRunner.Builder.setImageJRoi(boolean doSet) -> ImageJScriptRunner.Builder // Optionally set the ROI for the QuPath object being set as a Roi on the ImagePlus.
M ImageJScriptRunner.Builder.taskRunner(qupath.lib.plugins.TaskRunner taskRunner) -> ImageJScriptRunner.Builder // Provide an optional task runner.
M ImageJScriptRunner.Builder.text(String script) -> ImageJScriptRunner.Builder // Specify the exact text for the script or macro.

## qupath.imagej.gui.scripts.ImageJScriptRunner.ImageJScriptParameters [Class]
Class to store parameters used to run ImageJ macros or scripts from QuPath.
M ImageJScriptRunner.ImageJScriptParameters.doAddToWorkflow() -> boolean // Query whether the script should be logged in the history of the ImageData.
M ImageJScriptRunner.ImageJScriptParameters.doCloseOpenImages() -> boolean // Request that any lingering open images are closed after the script has run.
M ImageJScriptRunner.ImageJScriptParameters.doRemoveChildObjects() -> boolean // Query whether child objects should be removed from the parent object after the script is complete.
M ImageJScriptRunner.ImageJScriptParameters.doSetOverlay() -> boolean // Query whether the Overlay should be set when an image is passed to ImageJ.
M ImageJScriptRunner.ImageJScriptParameters.doSetRoi() -> boolean // Query whether the Roi should be set when an image is passed to ImageJ.
M ImageJScriptRunner.ImageJScriptParameters.getActiveRoiToObjectFunction() -> Function<qupath.lib.roi.interfaces.ROI, qupath.lib.objects.PathObject> // Get a function to convert an ImageJ active Roi into a QuPath object.
M ImageJScriptRunner.ImageJScriptParameters.getApplyToObjects() -> ImageJScriptRunner.ApplyToObjects // Get the objects to which this script should be applied.
M ImageJScriptRunner.ImageJScriptParameters.getChannels() -> List<qupath.lib.images.servers.ColorTransforms.ColorTransform> // 
M ImageJScriptRunner.ImageJScriptParameters.getDownsample() -> qupath.lib.images.servers.downsamples.DownsampleCalculator // Get the calculator used to determine how much to downsample image regions that will be send to ImageJ.
M ImageJScriptRunner.ImageJScriptParameters.getOverlayRoiToObjectFunction() -> Function<qupath.lib.roi.interfaces.ROI, qupath.lib.objects.PathObject> // Get a function to convert an ImageJ Roi on an Overlay into a QuPath object.
M ImageJScriptRunner.ImageJScriptParameters.getPadding() -> int // Get the padding to add around the ROI.
M ImageJScriptRunner.ImageJScriptParameters.getScriptEngineName() -> String // Get the name of the script engine to use, or null if no script engine is specified.
M ImageJScriptRunner.ImageJScriptParameters.getTaskRunner() -> qupath.lib.plugins.TaskRunner // Get a task runner for running script tasks.
M ImageJScriptRunner.ImageJScriptParameters.getText() -> String // Get the text of the macro or script.

## qupath.imagej.gui.scripts.ImageJScriptRunner.PathObjectType [Enum]

E ImageJScriptRunner.PathObjectType.ANNOTATION // 
E ImageJScriptRunner.PathObjectType.CELL // 
E ImageJScriptRunner.PathObjectType.DETECTION // 
E ImageJScriptRunner.PathObjectType.NONE // 
E ImageJScriptRunner.PathObjectType.TILE // 
E ImageJScriptRunner.PathObjectType.TMA_CORE // 
M ImageJScriptRunner.PathObjectType.valueOf(String name) -> static ImageJScriptRunner.PathObjectType // Returns the enum constant of this class with the specified name.
M ImageJScriptRunner.PathObjectType.values() -> static ImageJScriptRunner.PathObjectType[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.imagej.gui.scripts.ImageJScriptRunner [Class]
Class to run ImageJ macros and scripts.
C new Description -> Constructor // 
C new ImageJScriptRunner(ImageJScriptRunner.ImageJScriptParameters params) // 
M ImageJScriptRunner.builder() -> static ImageJScriptRunner.Builder // Create a new builder for an instance of ImageJScriptRunner.
M ImageJScriptRunner.builder(ImageJScriptRunner.ImageJScriptParameters params) -> static ImageJScriptRunner.Builder // Create a new builder for an instance of ImageJScriptRunner, initializing using the provided parameters.
M ImageJScriptRunner.createDetectionOrPointAnnotation(qupath.lib.roi.interfaces.ROI roi) -> static qupath.lib.objects.PathObject // Function to create an annotation object from any PointsROI, and detection object from any other ROI.
M ImageJScriptRunner.fromJson(String json) -> static ImageJScriptRunner // Create a script runner from a JSON representation of ImageJScriptRunner.ImageJScriptParameters.
M ImageJScriptRunner.fromMap(Map<String,?> paramMap) -> static ImageJScriptRunner // Create a script runner from a map representation of ImageJScriptRunner.ImageJScriptParameters.
M ImageJScriptRunner.fromParams(ImageJScriptRunner.ImageJScriptParameters params) -> static ImageJScriptRunner // Create a script runner from the specified parameters.
M ImageJScriptRunner.getObjectsToProcess(qupath.lib.objects.hierarchy.PathObjectHierarchy hierarchy, ImageJScriptRunner.ApplyToObjects applyTo) -> static List<qupath.lib.objects.PathObject> // Query which objects in a hierarchy would be used with the specified ImageJScriptRunner.ApplyToObjects value.
M ImageJScriptRunner.main(String[] args) -> static void // Example program to log a script.
M ImageJScriptRunner.run() -> void // Run the script for the 'current' image data, as requested from QP.
M ImageJScriptRunner.run(qupath.lib.images.ImageData<BufferedImage> imageData) -> void // Run the script for the specified image data.
M ImageJScriptRunner.test() -> void // Test the script for the 'current' image data, as requested from QP.
M ImageJScriptRunner.test(qupath.lib.images.ImageData<BufferedImage> imageData) -> void // Test the script for the specified image data.

## qupath.imagej.gui.scripts.ImageJScriptRunnerController.LanguageOption [Enum]
Options for the script language.
E ImageJScriptRunnerController.LanguageOption.GROOVY // Groovy language
E ImageJScriptRunnerController.LanguageOption.MACRO // ImageJ macro language
M ImageJScriptRunnerController.LanguageOption.valueOf(String name) -> static ImageJScriptRunnerController.LanguageOption // Returns the enum constant of this class with the specified name.
M ImageJScriptRunnerController.LanguageOption.values() -> static ImageJScriptRunnerController.LanguageOption[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.imagej.gui.scripts.ImageJScriptRunnerController.ResolutionOption [Enum]
Options for specifying how the resolution of an image region is determined.
E ImageJScriptRunnerController.ResolutionOption.FIXED_DOWNSAMPLE // Use a fixed downsample value;
E ImageJScriptRunnerController.ResolutionOption.LARGEST_DIMENSION // Resize so that the width and height are ≤ a fixed length;
E ImageJScriptRunnerController.ResolutionOption.PIXEL_SIZE // Resize to a target pixel size.
M ImageJScriptRunnerController.ResolutionOption.toString() -> String // 
M ImageJScriptRunnerController.ResolutionOption.valueOf(String name) -> static ImageJScriptRunnerController.ResolutionOption // Returns the enum constant of this class with the specified name.
M ImageJScriptRunnerController.ResolutionOption.values() -> static ImageJScriptRunnerController.ResolutionOption[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.imagej.gui.scripts.ImageJScriptRunnerController [Class]
Controller class for the ImageJ script runner.
M ImageJScriptRunnerController.createInstance(qupath.lib.gui.QuPathGUI qupath) -> static ImageJScriptRunnerController // Create a new instance.
M ImageJScriptRunnerController.doCopy(ActionEvent event) -> void // 
M ImageJScriptRunnerController.doCut(ActionEvent event) -> void // 
M ImageJScriptRunnerController.doPaste(ActionEvent event) -> void // 
M ImageJScriptRunnerController.doRedo(ActionEvent event) -> void // 
M ImageJScriptRunnerController.doUndo(ActionEvent event) -> void // 
M ImageJScriptRunnerController.getTitle() -> static String // Get the title to use for this window.
M ImageJScriptRunnerController.openMacro(Path path) -> void // 
M ImageJScriptRunnerController.promptToCreateNewMacro() -> void // 

## qupath.process.gui.ProcessingExtension.ObjectClassificationCommands [Class]

F ProcessingExtension.ObjectClassificationCommands.actionComposite -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.ObjectClassificationCommands.actionIntensity -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.ObjectClassificationCommands.actionLoadObjectClassifier -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.ObjectClassificationCommands.actionMeasurement -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.ObjectClassificationCommands.actionObjectClassifier -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.ObjectClassificationCommands.SEP -> final org.controlsfx.control.action.Action // 

## qupath.process.gui.ProcessingExtension.OpenCVCommands [Class]
Commands based on OpenCV.
F ProcessingExtension.OpenCVCommands.actionDelaunay -> final org.controlsfx.control.action.Action // Deprecated.
F ProcessingExtension.OpenCVCommands.actionDensityMap -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.OpenCVCommands.actionDensityMapLoad -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.OpenCVCommands.actionFastCellCounts -> final org.controlsfx.control.action.Action // Deprecated.

## qupath.process.gui.ProcessingExtension.OtherCommands [Class]

F ProcessingExtension.OtherCommands.actionChannelTraining -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.OtherCommands.actionCreateRegions -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.OtherCommands.actionSplitProject -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.OtherCommands.actionTrainingImage -> final org.controlsfx.control.action.Action // 

## qupath.process.gui.ProcessingExtension.PixelClassificationCommands [Class]

F ProcessingExtension.PixelClassificationCommands.actionLoadPixelClassifier -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.PixelClassificationCommands.actionPixelClassifier -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.PixelClassificationCommands.actionSimpleThreshold -> final org.controlsfx.control.action.Action // 
F ProcessingExtension.PixelClassificationCommands.SEP -> final org.controlsfx.control.action.Action // 

## qupath.process.gui.ProcessingExtension [Class]
General-purpose processing and machine learning commands.
C new Description -> Constructor // 
C new ProcessingExtension() // 
M ProcessingExtension.getDescription() -> String // 
M ProcessingExtension.getName() -> String // 
M ProcessingExtension.getQuPathVersion() -> qupath.lib.common.Version // Returns the version stored within this jar, because it is matched to the QuPath version.
M ProcessingExtension.getVersion() -> qupath.lib.common.Version // 
M ProcessingExtension.installExtension(qupath.lib.gui.QuPathGUI qupath) -> void // 

## qupath.process.gui.WandToolEventHandler.WandPreferences [Class]

F WandToolEventHandler.WandPreferences.useOverlays -> final BooleanProperty // 
F WandToolEventHandler.WandPreferences.wandSensitivity -> final DoubleProperty // 
F WandToolEventHandler.WandPreferences.wandSigma -> final DoubleProperty // 
F WandToolEventHandler.WandPreferences.wandType -> final ObjectProperty<WandToolEventHandler.WandType> // 
C new Description -> Constructor // 
C new WandPreferences() // 

## qupath.process.gui.WandToolEventHandler.WandType [Enum]
Enum reflecting different color images that may be used by the Wand tool.
E WandToolEventHandler.WandType.GRAY // Grayscale image
E WandToolEventHandler.WandType.LAB_DISTANCE // Color image converted to CIELAB, Euclidean distance calculated
E WandToolEventHandler.WandType.RGB // Color image (default behavior in v0.1.2 and before)
M WandToolEventHandler.WandType.valueOf(String name) -> static WandToolEventHandler.WandType // Returns the enum constant of this class with the specified name.
M WandToolEventHandler.WandType.values() -> static WandToolEventHandler.WandType[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.process.gui.WandToolEventHandler [Class]
Wand tool, which acts rather like the brush - except that it expands regions (sometimes rather too eagerly?) based upon local pixel values.
C new Description -> Constructor // 
C new WandToolEventHandler(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M WandToolEventHandler.getWandSensitivity() -> static double // Query the wand sensitivity value, which influences how similar local intensity values must be for the wand region growing.
M WandToolEventHandler.getWandSigmaPixels() -> static double // Query the Gaussian sigma value used to smooth the image when applying the wand.
M WandToolEventHandler.getWandUseOverlays() -> static boolean // Query whether the wand tool should be influenced by pixel values painted on image overlays.
M WandToolEventHandler.handle(MouseEvent arg0) -> void // 
M WandToolEventHandler.mouseClicked(MouseEvent arg0) -> void // 
M WandToolEventHandler.setWandSensitivity(double sensitivity) -> static void // Set the wand sensitivity value, which influences how similar local intensity values must be for the wand region growing.
M WandToolEventHandler.setWandSigmaPixels(double sigma) -> static void // Set the Gaussian sigma value used to smooth the image when applying the wand.
M WandToolEventHandler.setWandUseOverlays(boolean useOverlays) -> static void // Set whether the wand tool should be influenced by pixel values painted on image overlays.
M WandToolEventHandler.wandSensitivityProperty() -> static DoubleProperty // Property representing the wand sensitivity value, which influences how similar local intensity values must be for the wand region growing.
M WandToolEventHandler.wandSigmaPixelsProperty() -> static DoubleProperty // Property representing the Gaussian sigma value used to smooth the image when applying the wand.
M WandToolEventHandler.wandTypeProperty() -> static ObjectProperty<WandToolEventHandler.WandType> // Property specifying whether the wand tool should be influenced by pixel values painted on image overlays.
M WandToolEventHandler.wandUseOverlaysProperty() -> static BooleanProperty // Property specifying whether the wand tool should be influenced by pixel values painted on image overlays.

## qupath.process.gui.commands.CellIntensityClassificationCommand [Class]
Command to (sub)classify cells as Negative/Positive or Negative/1+/2+/3+ based on a single (usually intensity-based) measurement.
C new Description -> Constructor // 
C new CellIntensityClassificationCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M CellIntensityClassificationCommand.run() -> void // 

## qupath.process.gui.commands.CreateChannelTrainingImagesCommand [Class]
Command to create training images based upon channel names, and add these to a project.
C new Description -> Constructor // 
C new CreateChannelTrainingImagesCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M CreateChannelTrainingImagesCommand.run() -> void // 

## qupath.process.gui.commands.CreateCompositeClassifierCommand [Class]
Command to create a composite classifier by merging together two or more other classifiers.
C new Description -> Constructor // 
C new CreateCompositeClassifierCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M CreateCompositeClassifierCommand.run() -> void // 

## qupath.process.gui.commands.CreateRegionAnnotationsCommand [Class]
Command to help create annotations defining regions that will be further annotated for algorithm training.
C new Description -> Constructor // 
C new CreateRegionAnnotationsCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M CreateRegionAnnotationsCommand.run() -> void // 

## qupath.process.gui.commands.CreateTrainingImageCommand [Class]
Command to generate a SparseImageServer from multiple image regions across a project.
C new Description -> Constructor // 
C new CreateTrainingImageCommand() // 
M CreateTrainingImageCommand.promptToCreateTrainingImage(qupath.lib.projects.Project<BufferedImage> project, List<qupath.lib.objects.classes.PathClass> availableClasses) -> static qupath.lib.projects.ProjectImageEntry<BufferedImage> // Prompt to create a training image, based upon annotations throughout a project.

## qupath.process.gui.commands.DensityMapCommand [Class]
Command for generating density maps from detections on an image.
C new Description -> Constructor // 
C new DensityMapCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M DensityMapCommand.run() -> void // 

## qupath.process.gui.commands.ExportTrainingRegionsCommand [Class]
Command to help export training regions as labelled images to train AI algorithms elsewhere.
C new Description -> Constructor // 
C new ExportTrainingRegionsCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M ExportTrainingRegionsCommand.run() -> void // 

## qupath.process.gui.commands.ObjectClassifierCommand [Class]
Command used to create and show a suitable dialog box for interactive display of OpenCV classifiers.
C new Description -> Constructor // 
C new ObjectClassifierCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M ObjectClassifierCommand.run() -> void // 

## qupath.process.gui.commands.ObjectClassifierLoadCommand [Class]
Command to apply a pre-trained object classifier to an image.
C new Description -> Constructor // 
C new ObjectClassifierLoadCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M ObjectClassifierLoadCommand.run() -> void // 

## qupath.process.gui.commands.PixelClassifierCommand [Class]
Open GUI for the current viewer to train a new pixel classifier.
C new Description -> Constructor // 
C new PixelClassifierCommand() // 
M PixelClassifierCommand.run() -> void // 

## qupath.process.gui.commands.SimpleThresholdCommand [Class]
Apply simple thresholding to an image via the pixel classification framework to support thresholding at any resolution, optionally with visual feedback via an overlay.
C new Description -> Constructor // 
C new SimpleThresholdCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M SimpleThresholdCommand.run() -> void // 

## qupath.process.gui.commands.SingleMeasurementClassificationCommand [Class]
Command to (sub)classify objects based on a single measurement.
C new Description -> Constructor // 
C new SingleMeasurementClassificationCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M SingleMeasurementClassificationCommand.run() -> void // 

## qupath.process.gui.commands.SplitProjectTrainingCommand [Class]
Divide a project into training, validation and test sets but flagging individual image entries.
F SplitProjectTrainingCommand.TRAIN_VALIDATION_TEST_METADATA_KEY -> static final String // Metadata key for the flag indicating the image type (Train, Validation, Test or None).
F SplitProjectTrainingCommand.VALUE_NONE -> static final String // Metadata value for unassigned images.
F SplitProjectTrainingCommand.VALUE_TEST -> static final String // Metadata value for test images.
F SplitProjectTrainingCommand.VALUE_TRAINING -> static final String // Metadata value for training images.
F SplitProjectTrainingCommand.VALUE_VALIDATION -> static final String // Metadata value for validation images.
C new Description -> Constructor // 
C new SplitProjectTrainingCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M SplitProjectTrainingCommand.run() -> void // 

## qupath.process.gui.commands.density.DensityMapDialog [Class]
Dialog for interactively generating a custom density map.
C new Description -> Constructor // 
C new DensityMapDialog(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M DensityMapDialog.deregister() -> void // Deregister listeners.
M DensityMapDialog.getStage() -> Stage // Get the stage.
M DensityMapDialog.updateDefaults(qupath.lib.images.ImageData<BufferedImage> imageData) -> boolean // Update default parameters with a specified ImageData.

## qupath.process.gui.commands.density.DensityMapUI [Class]
UI elements associated with density maps.
F DensityMapUI.ANY_CLASS_OR_NONE -> static final qupath.lib.objects.classes.PathClass // Ignore classification entirely (i.e.
F DensityMapUI.ANY_POSITIVE_CLASS -> static final qupath.lib.objects.classes.PathClass // Accept any positive classification, including 1+, 2+, 3+.
F DensityMapUI.ANY_SPECIFIED_CLASS -> static final qupath.lib.objects.classes.PathClass // Any classification, but not no classification.
C new Description -> Constructor // 
C new DensityMapUI() // 
M DensityMapUI.createButtonPane(qupath.lib.gui.QuPathGUI qupath, ObjectExpression<qupath.lib.images.ImageData<BufferedImage>> imageData, ObjectExpression<qupath.lib.analysis.heatmaps.DensityMaps.DensityMapBuilder> builder, StringExpression densityMapName, ObjectExpression<qupath.lib.gui.viewer.overlays.PixelClassificationOverlay> overlay, boolean enableUnsavedButton) -> static Pane // Create a pane containing standardized buttons associated with processing a density map (find hotspots, threshold, export map).
M DensityMapUI.createSaveDensityMapPane(ObjectExpression<qupath.lib.projects.Project<BufferedImage>> project, ObjectExpression<qupath.lib.analysis.heatmaps.DensityMaps.DensityMapBuilder> densityMap, StringProperty savedName) -> static Pane // Create a pane that can be used to save a DensityMaps.DensityMapBuilder, with standardized display and prompts.

## qupath.process.gui.commands.ml.BoundaryStrategy [Class]
Helper class for handling the boundaries of training annotations when creating a pixel classifier.
M BoundaryStrategy.equals(Object obj) -> boolean // 
M BoundaryStrategy.getBoundaryClass(qupath.lib.objects.classes.PathClass pathClass) -> qupath.lib.objects.classes.PathClass // Get the classification to be used for the annotation boundary, given the classification of the annotated region.
M BoundaryStrategy.getBoundaryThickness() -> double // Get the boundary thickness, in pixels.
M BoundaryStrategy.getClassifyBoundaryStrategy(qupath.lib.objects.classes.PathClass pathClass, double thickness) -> static BoundaryStrategy // Create a boundary strategy that trains a classifier for a specific PathClass for annotation boundaries.
M BoundaryStrategy.getDerivedBoundaryStrategy(double thickness) -> static BoundaryStrategy // Create a boundary strategy that trains a classifier for a PathClass derived from the original classification for annotation boundaries.
M BoundaryStrategy.getSkipBoundaryStrategy() -> static BoundaryStrategy // Create a boundary strategy that ignores boundaries, not using them for classifier training.
M BoundaryStrategy.hashCode() -> int // 
M BoundaryStrategy.setThickness(BoundaryStrategy strategy, double thickness) -> static BoundaryStrategy // Create a boundary strategy with the specified thickness.
M BoundaryStrategy.toString() -> String // 

## qupath.process.gui.commands.ml.ClassificationResolution [Class]
Wrapper for a PixelCalibration to be used to define classifier resolution.
M ClassificationResolution.equals(Object obj) -> boolean // 
M ClassificationResolution.getDefaultResolutions(qupath.lib.images.ImageData<?> imageData, ClassificationResolution selected) -> static List<ClassificationResolution> // Get a list of default resolutions to show, derived from PixelCalibration objects.
M ClassificationResolution.getName() -> String // Get the simple name for this resolution.
M ClassificationResolution.getPixelCalibration() -> qupath.lib.images.servers.PixelCalibration // Get the PixelCalibration used to apply this resolution.
M ClassificationResolution.hashCode() -> int // 
M ClassificationResolution.toString() -> String // 

## qupath.process.gui.commands.ml.PixelClassifierPane [Class]
Main user interface for interactively training a PixelClassifier.
C new Description -> Constructor // 
C new PixelClassifierPane(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M PixelClassifierPane.installDefaultFeatureClassificationBuilder(qupath.process.gui.commands.ml.ImageDataTransformerBuilder builder) -> static boolean // Add to the list of default feature calculator builders that will be available when this pane is opened.

## qupath.process.gui.commands.ml.PixelClassifierTraining.ClassifierTrainingData [Class]
Wrapper for training data.
M PixelClassifierTraining.ClassifierTrainingData.getLabelMap() -> Map<qupath.lib.objects.classes.PathClass, Integer> // Get the map of classifications to labels.
M PixelClassifierTraining.ClassifierTrainingData.getTrainData() -> TrainData // Get training data.

## qupath.process.gui.commands.ml.PixelClassifierTraining [Class]
Helper class for training a pixel classifier.
C new Description -> Constructor // 
C new PixelClassifierTraining(qupath.opencv.ops.ImageDataOp featureCalculator) // Create a new pixel classifier helper, to support generating training data.
M PixelClassifierTraining.createTrainingData(Collection<qupath.lib.images.ImageData<BufferedImage>> imageData) -> PixelClassifierTraining.ClassifierTrainingData // Create training data, using a label map automatically generated from the available classifications.
M PixelClassifierTraining.createTrainingData(qupath.lib.images.ImageData<BufferedImage> imageData) -> PixelClassifierTraining.ClassifierTrainingData // Create training data, using a label map automatically generated from the available classifications.
M PixelClassifierTraining.createTrainingDataForLabelMap(Collection<qupath.lib.images.ImageData<BufferedImage>> imageData, Map<qupath.lib.objects.classes.PathClass, Integer> labels) -> PixelClassifierTraining.ClassifierTrainingData // Get a classifier training map, using a predefined label map (which determines which classifications to use).
M PixelClassifierTraining.getBoundaryStrategy() -> BoundaryStrategy // Get the strategy for handling the boundaries of area annotations.
M PixelClassifierTraining.getFeatureOp() -> qupath.opencv.ops.ImageDataOp // Get an ImageDataOp used for feature calculation.
M PixelClassifierTraining.getResolution() -> qupath.lib.images.servers.PixelCalibration // Get the resolution at which the training should occur.
M PixelClassifierTraining.setBoundaryStrategy(BoundaryStrategy strategy) -> void // Set the strategy for handling the boundaries of area annotations.
M PixelClassifierTraining.setFeatureOp(qupath.opencv.ops.ImageDataOp featureOp) -> void // Set the ImageDataOp used to calculate features.
M PixelClassifierTraining.setResolution(qupath.lib.images.servers.PixelCalibration cal) -> void // Set the resolution at which the training should occur.

## qupath.process.gui.commands.ml.PixelClassifierUI [Class]
Helper class for generating standardized UI components for pixel classification.
C new Description -> Constructor // 
C new PixelClassifierUI() // 
M PixelClassifierUI.createPixelClassifierButtons(ObjectExpression<qupath.lib.images.ImageData<BufferedImage>> imageData, ObjectExpression<qupath.lib.classifiers.pixel.PixelClassifier> classifier, StringExpression classifierName) -> static Pane // Create a standard button pane for pixel classifiers, to create, measure and classify objects.
M PixelClassifierUI.createRegionFilterCombo(qupath.lib.gui.viewer.OverlayOptions options) -> static ComboBox<qupath.lib.gui.viewer.RegionFilter> // Create a ComboBox that can be used to select the pixel classification region filter.
M PixelClassifierUI.createSavePixelClassifierPane(ObjectExpression<qupath.lib.projects.Project<BufferedImage>> project, ObjectExpression<qupath.lib.classifiers.pixel.PixelClassifier> classifier, StringProperty savedName) -> static Pane // Create a pane that contains a text field and save button to allow a pixel classifier to be saved in a project.
M PixelClassifierUI.promptToCreateObjects(qupath.lib.images.ImageData<BufferedImage> imageData, qupath.lib.classifiers.pixel.PixelClassifier classifier, String classifierName) -> static boolean // Prompt the user to create objects directly from the pixels of an ImageServer.

## qupath.process.gui.commands.ml.ProjectClassifierBindings [Class]
Class to help with formatting text fields for entering pixel and object classifier names.
C new Description -> Constructor // 
C new ProjectClassifierBindings() // 
M ProjectClassifierBindings.bindObjectClassifierNameInput(TextField textField, ObjectExpression<qupath.lib.projects.Project<BufferedImage>> project) -> static void // Set styling for a text field to use object classifier names for the current project.
M ProjectClassifierBindings.bindPixelClassifierNameInput(TextField textField, ObjectExpression<qupath.lib.projects.Project<BufferedImage>> project) -> static void // Set styling for a text field to use pixel classifier names for the current project.

## qupath.process.gui.commands.ui.LoadResourceCommand [Class]
Create commands for displaying pixel classifiers and density maps.
M LoadResourceCommand.createLoadDensityMapCommand(qupath.lib.gui.QuPathGUI qupath) -> static LoadResourceCommand<qupath.lib.analysis.heatmaps.DensityMaps.DensityMapBuilder> // Create a Runnable to interactively load a density map and display it in all viewers.
M LoadResourceCommand.createLoadPixelClassifierCommand(qupath.lib.gui.QuPathGUI qupath) -> static LoadResourceCommand<qupath.lib.classifiers.pixel.PixelClassifier> // Create a Runnable to interactively load a pixel classifier and display it in all viewers.
M LoadResourceCommand.run() -> void // 

## qupath.process.gui.commands.ui.SaveResourcePaneBuilder [Class]
Small JavaFX pane to support saving object/pixel classifiers and density maps within a project in a standardized way.
C new Description -> Constructor // 
C new SaveResourcePaneBuilder(Class<T> cls, ObjectExpression<? extends T> resource) // Constructor.
M SaveResourcePaneBuilder.build() -> Pane // Build the pane
M SaveResourcePaneBuilder.labelText(String prompt) -> SaveResourcePaneBuilder<T> // Prompt to include beside the resource name text field
M SaveResourcePaneBuilder.project(ObjectExpression<qupath.lib.projects.Project<BufferedImage>> project) -> SaveResourcePaneBuilder<T> // Current project
M SaveResourcePaneBuilder.savedName(StringProperty savedName) -> SaveResourcePaneBuilder<T> // Property to store the saved name; this is useful if the name is required externally
M SaveResourcePaneBuilder.textFieldPrompt(String prompt) -> SaveResourcePaneBuilder<T> // Prompt to include beside the resource name text field
M SaveResourcePaneBuilder.title(String title) -> SaveResourcePaneBuilder<T> // Title to display in any dialogs
M SaveResourcePaneBuilder.tooltip(ObservableValue<String> tooltip) -> SaveResourcePaneBuilder<T> // Text to include in any tooltip.

## qupathj.QuPath_Send_Overlay_to_QuPath [Class]
ImageJ plugin for sending back all the ROIs on an ImageJ overlay to QuPath.
C new Description -> Constructor // 
C new QuPath_Send_Overlay_to_QuPath() // 
M QuPath_Send_Overlay_to_QuPath.createObjectsFromROIs(ImagePlus imp, Collection<? extends Roi> rois, double downsample, boolean asDetection, boolean includeMeasurements, qupath.lib.regions.ImagePlane plane) -> static List<qupath.lib.objects.PathObject> // Turn an array of ImageJ ROIs into a list of QuPath PathObjects, optionally adding measurements as well.
M QuPath_Send_Overlay_to_QuPath.createObjectsFromROIs(ImagePlus imp, Collection<? extends Roi> rois, double downsample, Function<qupath.lib.roi.interfaces.ROI, qupath.lib.objects.PathObject> creator, boolean includeMeasurements, qupath.lib.regions.ImagePlane plane) -> static List<qupath.lib.objects.PathObject> // Turn an array of ImageJ ROIs into a list of QuPath PathObjects, optionally adding measurements as well.
M QuPath_Send_Overlay_to_QuPath.run(String arg) -> void // 

## qupathj.QuPath_Send_ROI_to_QuPath [Class]
ImageJ plugin for sending back the active ROI from ImageJ to QuPath.
C new Description -> Constructor // 
C new QuPath_Send_ROI_to_QuPath() // 
M QuPath_Send_ROI_to_QuPath.run(String arg) -> void // 
