# qupath-extension-djl-0.4.2

## qupath.ext.djl.DjlDnnModelBuilder [Class]
A DnnModelBuilder using Deep Java Library.
C new Description -> Constructor // 
C new DjlDnnModelBuilder() // 
M DjlDnnModelBuilder.buildModel(qupath.opencv.dnn.DnnModelParams params) -> qupath.opencv.dnn.DnnModel // 

## qupath.ext.djl.DjlExtension [Class]
Experimental extension to connect QuPath and Deep Java Library.
C new Description -> Constructor // 
C new DjlExtension() // 
M DjlExtension.getDescription() -> String // 
M DjlExtension.getName() -> String // 
M DjlExtension.getQuPathVersion() -> qupath.lib.common.Version // 
M DjlExtension.getRepository() -> qupath.lib.gui.extensions.GitHubProject.GitHubRepo // 
M DjlExtension.installExtension(qupath.lib.gui.QuPathGUI qupath) -> void // 

## qupath.ext.djl.DjlTools [Class]
Tools to help work with Deep Java Library within QuPath.
F DjlTools.ENGINE_DLR -> static String // Neo DLR engine name
F DjlTools.ENGINE_LIGHTGBM -> static String // LightGBM engine name
F DjlTools.ENGINE_MXNET -> static String // MXNet engine name
F DjlTools.ENGINE_ONNX_RUNTIME -> static String // ONNX Runtime engine name
F DjlTools.ENGINE_PADDLEPADDLE -> static String // PaddlePaddle engine name
F DjlTools.ENGINE_PYTORCH -> static String // PyTorch engine name
F DjlTools.ENGINE_TENSORFLOW -> static String // TensorFlow engine name
F DjlTools.ENGINE_TENSORRT -> static String // TensorRT engine name
F DjlTools.ENGINE_TFLITE -> static String // TensorFlow Lite engine name
F DjlTools.ENGINE_XGBOOST -> static String // XGBoost engine name
F DjlTools.loadedEngines -> static Set<String> // Maintain a set of all engines that are known to have been loaded.
C new Description -> Constructor // 
C new DjlTools() // 
M DjlTools.createDnnModel(String engine, URI uri, String ndLayout, Map<String,qupath.opencv.dnn.DnnShape> inputs, Map<String,qupath.opencv.dnn.DnnShape> outputs) -> static qupath.opencv.dnn.DnnModel // Create a DnnModel wrapping a model from Deep Java Library.
M DjlTools.createDnnModel(URI uri, String ndLayout, int[] inputShape) -> static qupath.opencv.dnn.DnnModel // Create a DnnModel wrapping a model from Deep Java Library.
M DjlTools.getEngine(String name, boolean downloadIfNeeded) -> static ai.djl.engine.Engine // Get an Engine by name.
M DjlTools.getLongs(ai.djl.ndarray.NDArray array) -> static long[] // Extract array values as longs, converting if necessary.
M DjlTools.getOverrideDevice(String engineName) -> static ai.djl.Device // Get the default device for the specified engine, which overrides DJL's default device for the specified engine.
M DjlTools.hasEngine(String name) -> static boolean // Check if an Deep Java Library engine is potentially available.
M DjlTools.isEngineAvailable(String name) -> static boolean // Check if an engine is available and ready for use without any additional downloading.
M DjlTools.matToNDArray(ai.djl.ndarray.NDManager manager, org.bytedeco.opencv.opencv_core.Mat mat, String ndLayout) -> static ai.djl.ndarray.NDArray // Convert an Opencv Mat to a Deep Java Library NDArray.
M DjlTools.ndArrayToMat(ai.djl.ndarray.NDArray array, String ndLayout) -> static org.bytedeco.opencv.opencv_core.Mat // Convert an NDArray into an OpenCV Mat, automatically squeezing singleton dimensions.
M DjlTools.ndArrayToMat(ai.djl.ndarray.NDArray array, String ndLayout, boolean doSqueeze) -> static org.bytedeco.opencv.opencv_core.Mat // Convert an NDArray into an OpenCV Mat, optionally squeezing singleton dimensions.
M DjlTools.setOverrideDevice(String engineName, ai.djl.Device device) -> static void // Set the default device for the specified engine.

## qupath.ext.djl.DjlZoo [Class]
Helper class for working with DeepJavaLibrary model zoos.
C new Description -> Constructor // 
C new DjlZoo() // 
M DjlZoo.buildCriteria(ai.djl.repository.Artifact artifact, boolean allowDownload) -> static ai.djl.repository.zoo.Criteria<?,?> // Build Criteria from an existing artifact.
M DjlZoo.classify(ai.djl.inference.Predictor<ai.djl.modality.cv.Image,ai.djl.modality.Classifications> predictor, BufferedImage img) -> static ai.djl.modality.Classifications // Apply a classification model predictor to an input image.
M DjlZoo.createROI(ai.djl.modality.cv.output.BoundingBox box, qupath.lib.regions.ImageRegion region) -> static qupath.lib.roi.interfaces.ROI // Create a rectangular ROI from a bounding box, rescaling according to the ImageRegion.
M DjlZoo.createROI(ai.djl.modality.cv.output.DetectedObjects.DetectedObject obj, qupath.lib.regions.ImageRegion region) -> static qupath.lib.roi.interfaces.ROI // Create a ROI from a detected object, rescaling according to the ImageRegion.
M DjlZoo.createROI(ai.djl.modality.cv.output.Landmark landmark, qupath.lib.regions.ImageRegion region) -> static qupath.lib.roi.interfaces.ROI // Create a points ROI from a detected mask, rescaling according to the ImageRegion.
M DjlZoo.createROI(ai.djl.modality.cv.output.Mask mask, qupath.lib.regions.ImageRegion region, double threshold) -> static qupath.lib.roi.interfaces.ROI // Create a ROI from a detected mask, rescaling according to the ImageRegion.
M DjlZoo.detect(ai.djl.inference.Predictor<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.DetectedObjects> predictor, BufferedImage img) -> static ai.djl.modality.cv.output.DetectedObjects // Apply a detection model predictor to an input image.
M DjlZoo.detect(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.DetectedObjects> model, qupath.lib.images.ImageData<BufferedImage> imageData) -> static Optional<List<qupath.lib.objects.PathObject>> // Run object detection for an entire image.
M DjlZoo.detect(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.DetectedObjects> model, qupath.lib.images.ImageData<BufferedImage> imageData, Collection<? extends qupath.lib.objects.PathObject> parentObjects) -> static Optional<List<qupath.lib.objects.PathObject>> // Run object detection within specified objects in an image.
M DjlZoo.imageToImage(ai.djl.inference.Predictor<ai.djl.modality.cv.Image,ai.djl.modality.cv.Image> predictor, BufferedImage img) -> static BufferedImage // Apply a predictor that takes a BufferedImage as input and provides another BufferedImage as output.
M DjlZoo.listImageClassificationModels() -> static List<ai.djl.repository.MRL> // List all zoo models for image classification.
M DjlZoo.listInstanceSegmentationModels() -> static List<ai.djl.repository.MRL> // List all zoo models for instance segmentation.
M DjlZoo.listModels() -> static List<ai.djl.repository.MRL> // List all zoo models.
M DjlZoo.listModels(ai.djl.Application application) -> static List<ai.djl.repository.MRL> // List all zoo models for a specific application.
M DjlZoo.listModels(ai.djl.repository.zoo.Criteria<?,?> criteria) -> static List<ai.djl.repository.MRL> // List all zoo models matching a specific criteria.
M DjlZoo.listObjectDetectionModels() -> static List<ai.djl.repository.MRL> // List all zoo models for object detection.
M DjlZoo.listSemanticSegmentationModels() -> static List<ai.djl.repository.MRL> // List all zoo models for semantic segmentation.
M DjlZoo.loadModel(ai.djl.repository.Artifact artifact, boolean allowDownload) -> static ai.djl.repository.zoo.ZooModel<?,?> // Try to load a zoo model for a given artifact.
M DjlZoo.logAvailableModels() -> static void // Print all available zoo models to the log.
M DjlZoo.segmentAnnotations(ai.djl.inference.Predictor<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> predictor, BufferedImage img, qupath.lib.regions.RegionRequest request) -> static List<qupath.lib.objects.PathObject> // Apply a segmentation model to a single image, creating annotations from the result.
M DjlZoo.segmentAnnotations(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> model, qupath.lib.images.ImageData<BufferedImage> imageData) -> static Optional<List<qupath.lib.objects.PathObject>> // Apply a segmentation model to segment objects within an image, and represent these as annotations.
M DjlZoo.segmentAnnotations(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> model, qupath.lib.images.ImageData<BufferedImage> imageData, Collection<? extends qupath.lib.objects.PathObject> parentObjects) -> static Optional<List<qupath.lib.objects.PathObject>> // Apply a segmentation model to segment objects within specified objects in an image, and represent these as annotations.
M DjlZoo.segmentDetections(ai.djl.inference.Predictor<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> predictor, BufferedImage img, qupath.lib.regions.RegionRequest request) -> static List<qupath.lib.objects.PathObject> // Apply a segmentation model to a single image, creating detections from the result.
M DjlZoo.segmentDetections(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> model, qupath.lib.images.ImageData<BufferedImage> imageData) -> static Optional<List<qupath.lib.objects.PathObject>> // Apply a segmentation model to segment objects within an image, and represent these as detections.
M DjlZoo.segmentDetections(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> model, qupath.lib.images.ImageData<BufferedImage> imageData, Collection<? extends qupath.lib.objects.PathObject> parentObjects) -> static Optional<List<qupath.lib.objects.PathObject>> // Apply a segmentation model to segment objects within specified objects in an image, and represent these as detections.
M DjlZoo.segmentObjects(ai.djl.inference.Predictor<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> predictor, BufferedImage img, qupath.lib.regions.RegionRequest request, qupath.lib.roi.interfaces.ROI roiMask, Function<qupath.lib.roi.interfaces.ROI,qupath.lib.objects.PathObject> creator, boolean skipBackground) -> static List<qupath.lib.objects.PathObject> // Apply a segmentation model to a single image.
M DjlZoo.segmentObjects(ai.djl.repository.zoo.ZooModel<ai.djl.modality.cv.Image,ai.djl.modality.cv.output.CategoryMask> model, qupath.lib.images.ImageData<BufferedImage> imageData, Collection<? extends qupath.lib.objects.PathObject> parentObjects, Function<qupath.lib.roi.interfaces.ROI,qupath.lib.objects.PathObject> creator, boolean skipBackground) -> static Optional<List<qupath.lib.objects.PathObject>> // Apply a segmentation model to segment objects within an image.
M DjlZoo.toBufferedImage(ai.djl.modality.cv.Image image) -> static BufferedImage // Try to convert a DJL Image to a Java BufferedImage.

## qupath.ext.djl.ui.DjlEngineCommand [Class]
Command to display Deep Java Library engines.
M DjlEngineCommand.showDialog(qupath.lib.gui.QuPathGUI qupath) -> static void // Show dialog.

## qupath.ext.djl.ui.LaunchScriptCommand [Class]
Command to generate a launch script for QuPath.
F LaunchScriptCommand.KEY_CONDA_PATH -> static final String // 
F LaunchScriptCommand.KEY_PYTORCH_FLAVOR -> static final String // 
F LaunchScriptCommand.KEY_PYTORCH_LIBRARY_PATH -> static final String // 
F LaunchScriptCommand.KEY_PYTORCH_VERSION -> static final String // 
F LaunchScriptCommand.KEY_QUPATH_EXE -> static final String // 
C new Description -> Constructor // 
C new LaunchScriptCommand() // 
M LaunchScriptCommand.createLaunchScript(Map<String,String> params) -> static String // Generate a .bat or .sh script to launch QuPath with the given parameters.
M LaunchScriptCommand.promptForScript() -> void // 
