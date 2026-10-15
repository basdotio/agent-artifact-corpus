# qupath-extension-bioformats-0.7.0

## qupath.lib.images.servers.bioformats.BioFormatsImageServer [Class]
QuPath ImageServer that uses the Bio-Formats library to read image data.
C new Description -> Constructor // 
C new BioFormatsImageServer(URI uri, String... args) // Create an ImageServer using the Bio-Formats library.
M BioFormatsImageServer.close() -> void // 
M BioFormatsImageServer.createID() -> String // 
M BioFormatsImageServer.dumpMetadata() -> String // Retrieve a string representation of the metadata OME-XML.
M BioFormatsImageServer.getAssociatedImage(String name) -> BufferedImage // 
M BioFormatsImageServer.getAssociatedImageList() -> List<String> // 
M BioFormatsImageServer.getFile() -> File // Get the underlying file.
M BioFormatsImageServer.getFormat() -> String // Get the format String, as returned by Bio-Formats IFormatReader.getFormat().
M BioFormatsImageServer.getMetadataStore() -> OMEPyramidStore // Get the MetadataStore, as used by Bio-Formats.
M BioFormatsImageServer.getOriginalMetadata() -> qupath.lib.images.servers.ImageServerMetadata // 
M BioFormatsImageServer.getSeries() -> int // Get the series index, as used by Bio-Formats.
M BioFormatsImageServer.getServerType() -> String // 
M BioFormatsImageServer.getURIs() -> Collection<URI> // 
M BioFormatsImageServer.readPathObjects() -> Collection<qupath.lib.objects.PathObject> // 
M BioFormatsImageServer.readTile(qupath.lib.images.servers.TileRequest tileRequest) -> BufferedImage // 
M BioFormatsImageServer.setMetadata(qupath.lib.images.servers.ImageServerMetadata metadata) -> void // 

## qupath.lib.images.servers.bioformats.BioFormatsOptionsExtension.BioFormatsPreferences [Class]

F BioFormatsOptionsExtension.BioFormatsPreferences.enableBioformats -> final BooleanProperty // 
F BioFormatsOptionsExtension.BioFormatsPreferences.filesOnly -> final BooleanProperty // 
F BioFormatsOptionsExtension.BioFormatsPreferences.memoizationTimeMillis -> final IntegerProperty // 
F BioFormatsOptionsExtension.BioFormatsPreferences.pathMemoization -> final StringProperty // 
F BioFormatsOptionsExtension.BioFormatsPreferences.skipExtensions -> final StringProperty // 
F BioFormatsOptionsExtension.BioFormatsPreferences.useExtensions -> final StringProperty // 
F BioFormatsOptionsExtension.BioFormatsPreferences.useParallelization -> final BooleanProperty // 

## qupath.lib.images.servers.bioformats.BioFormatsOptionsExtension.OmeTiffWriterAction [Class]

F BioFormatsOptionsExtension.OmeTiffWriterAction.actionWriter -> final org.controlsfx.control.action.Action // 

## qupath.lib.images.servers.bioformats.BioFormatsOptionsExtension.OmeZarrWriterAction [Class]

F BioFormatsOptionsExtension.OmeZarrWriterAction.actionWriter -> final org.controlsfx.control.action.Action // 
C new Description -> Constructor // 
C new OmeZarrWriterAction(qupath.lib.gui.QuPathGUI qupath) // 

## qupath.lib.images.servers.bioformats.BioFormatsOptionsExtension [Class]
A QuPath extension that adds options relating to the BioFormatsImageServer to the main QuPath preference pane.
C new Description -> Constructor // 
C new BioFormatsOptionsExtension() // 
M BioFormatsOptionsExtension.getDescription() -> String // 
M BioFormatsOptionsExtension.getName() -> String // 
M BioFormatsOptionsExtension.getQuPathVersion() -> qupath.lib.common.Version // Returns the version stored within this jar, because it is matched to the QuPath version.
M BioFormatsOptionsExtension.installExtension(qupath.lib.gui.QuPathGUI qupath) -> void // 

## qupath.lib.images.servers.bioformats.BioFormatsServerBuilder [Class]
Builder for ImageServers that make use of the Bio-Formats library.
C new Description -> Constructor // 
C new BioFormatsServerBuilder() // 
M BioFormatsServerBuilder.buildServer(URI uri, String... args) -> qupath.lib.images.servers.ImageServer<BufferedImage> // 
M BioFormatsServerBuilder.checkImageSupport(URI uri, String... args) -> qupath.lib.images.servers.ImageServerBuilder.UriImageSupport<BufferedImage> // 
M BioFormatsServerBuilder.getDescription() -> String // 
M BioFormatsServerBuilder.getImageType() -> Class<BufferedImage> // 
M BioFormatsServerBuilder.getName() -> String // 
M BioFormatsServerBuilder.matchClassName(String... classNames) -> boolean // 

## qupath.lib.images.servers.bioformats.BioFormatsServerOptions [Class]
Container for various options that can customize the behavior of the BioFormatsImageServer.
F BioFormatsServerOptions.ALLOW_MEMOIZATION_PROPERTY -> static String // System property controlling whether memoization is allowed or not.
M BioFormatsServerOptions.allowMemoization() -> static boolean // Check whether memoization should be allowed or not.
M BioFormatsServerOptions.bioformatsEnabled() -> boolean // Returns true if Bio-Formats is enabled and may be used to read images.
M BioFormatsServerOptions.clearReaderOptions() -> void // Clear all reader options, returning these to their defaults.
M BioFormatsServerOptions.getFilesOnly() -> boolean // Returns true if Bio-Formats is restricted to support only local files, not other URLs.
M BioFormatsServerOptions.getInstance() -> static BioFormatsServerOptions // Get the static instance of BioFormatsServerOptions, available to servers being constructed.
M BioFormatsServerOptions.getMemoizationTimeMillis() -> int // Returns the number of milliseconds that must elapse when opening an image before a memoization file is generated.
M BioFormatsServerOptions.getPathMemoization() -> String // Get the path to the directory where memoization files should be written, or null if no path is set.
M BioFormatsServerOptions.getReaderOptions() -> Map<String,String> // Get a map representing additional arguments that should be passed to readers.
M BioFormatsServerOptions.getSkipAlwaysExtensions() -> Set<String> // Query the set of file extensions for which Bio-Formats should not be used.
M BioFormatsServerOptions.getUseAlwaysExtensions() -> Set<String> // Query the set of file extensions for which Bio-Formats should always be used.
M BioFormatsServerOptions.requestParallelization() -> boolean // Returns true if multiple readers may be created for different threads, to enable parallel image reading.
M BioFormatsServerOptions.setBioformatsEnabled(boolean bioformatsEnabled) -> void // Set whether Bio-Formats should be enabled or disabled (in favor of other readers).
M BioFormatsServerOptions.setFilesOnly(boolean filesOnly) -> void // Set whether Bio-Formats should support only local files (rather than any URL).
M BioFormatsServerOptions.setMemoizationTimeMillis(int memoizationTimeMillis) -> void // Set the number of milliseconds that must elapse when opening an image before a memoization file is generated.
M BioFormatsServerOptions.setPathMemoization(String pathMemoization) -> void // Set the directory where memoization files should be written.
M BioFormatsServerOptions.setReaderOptions(Map<String,String> options) -> void // Set additional arguments that should be passed to readers.
M BioFormatsServerOptions.setRequestParallelization(boolean requestParallelization) -> void // Optionally enable or disable parallelization when reading images.

## qupath.lib.images.servers.bioformats.OMEPixelParser.Builder [Class]
Builder for instances of OMEPixelParser.
C new Description -> Constructor // 
C new Builder() // 
M OMEPixelParser.Builder.build() -> OMEPixelParser // Creates a new OMEPixelParser instance.
M OMEPixelParser.Builder.byteOrder(ByteOrder byteOrder) -> OMEPixelParser.Builder // 
M OMEPixelParser.Builder.effectiveNChannels(int effectiveNChannels) -> OMEPixelParser.Builder // 
M OMEPixelParser.Builder.isInterleaved(boolean isInterleaved) -> OMEPixelParser.Builder // 
M OMEPixelParser.Builder.normalizeFloats(boolean normalizeFloats) -> OMEPixelParser.Builder // 
M OMEPixelParser.Builder.pixelType(qupath.lib.images.servers.PixelType pixelType) -> OMEPixelParser.Builder // 
M OMEPixelParser.Builder.samplesPerPixel(int[] samplesPerPixel) -> OMEPixelParser.Builder // 

## qupath.lib.images.servers.bioformats.OMEPixelParser [Class]
This class can parse raw bytes into a BufferedImage.
M OMEPixelParser.parse(byte[][] pixels, int width, int height, int nChannels, ColorModel colorModel) -> BufferedImage // Creates a BufferedImage from a 2-dimensional byte array.

## qupath.lib.images.writers.ome.ConvertCommand [Class]
Allows command line option to convert an input image to OME-TIFF or OME-Zarr.
C new Description -> Constructor // 
C new ConvertCommand() // 
M ConvertCommand.run() -> void // 

## qupath.lib.images.writers.ome.OMEPyramidWriter.Builder [Class]
Builder class to define parameters when exporting an image region as OME-TIFF, possibly as an image pyramid.
C new Description -> Constructor // 
C new Builder(qupath.lib.images.servers.ImageServer<BufferedImage> server) // Constructor.
M OMEPyramidWriter.Builder.allTimePoints() -> OMEPyramidWriter.Builder // Request that all timepoints of a time series will be written.
M OMEPyramidWriter.Builder.allZSlices() -> OMEPyramidWriter.Builder // Request that all z-slices are exported.
M OMEPyramidWriter.Builder.bigTiff() -> OMEPyramidWriter.Builder // Request that the image is written in BigTIFF format.
M OMEPyramidWriter.Builder.bigTiff(boolean doBigTiff) -> OMEPyramidWriter.Builder // Specify whether the image should be written in BigTIFF format.
M OMEPyramidWriter.Builder.build() -> OMEPyramidWriter.OMEPyramidSeries // Create an OMEPyramidWriter.OMEPyramidSeries to write the OME-TIFF.
M OMEPyramidWriter.Builder.channels(int... channels) -> OMEPyramidWriter.Builder // Override default of writing all channels in their original order to be able to specify which channels are output, and in which order.
M OMEPyramidWriter.Builder.channelsImages() -> OMEPyramidWriter.Builder // Request that channels are written as separate images.
M OMEPyramidWriter.Builder.channelsInterleaved() -> OMEPyramidWriter.Builder // Request that channels are written interleaved within a single image plane.
M OMEPyramidWriter.Builder.channelsPlanar() -> OMEPyramidWriter.Builder // Request that channels are written as separate image planes.
M OMEPyramidWriter.Builder.codecOptions(CodecOptions codecOptions) -> OMEPyramidWriter.Builder // Set options for compressing data.
M OMEPyramidWriter.Builder.compression(OMEPyramidWriter.CompressionType compression) -> OMEPyramidWriter.Builder // Request the output compression type.
M OMEPyramidWriter.Builder.downsamples(double... downsamples) -> OMEPyramidWriter.Builder // Specify downsample factors to use in the final pyramid.
M OMEPyramidWriter.Builder.dyadicDownsampling() -> OMEPyramidWriter.Builder // Downsample by factors of 2.
M OMEPyramidWriter.Builder.losslessCompression() -> OMEPyramidWriter.Builder // Request the default lossless compression method.
M OMEPyramidWriter.Builder.lossyCompression() -> OMEPyramidWriter.Builder // Request the default lossy compression method.
M OMEPyramidWriter.Builder.name(String name) -> OMEPyramidWriter.Builder // Specify a series name
M OMEPyramidWriter.Builder.parallelize() -> OMEPyramidWriter.Builder // Parallelize tile export, if possible.
M OMEPyramidWriter.Builder.parallelize(boolean doParallel) -> OMEPyramidWriter.Builder // Specify if tile export should be parallelized if possible, with the default number of threads (current 4).
M OMEPyramidWriter.Builder.parallelize(int nThreads) -> OMEPyramidWriter.Builder // Specify if tile export should be parallelized if possible, with the requested number of threads.
M OMEPyramidWriter.Builder.pixelType(String exportPixelType) -> OMEPyramidWriter.Builder // Specify the output PixelType as a String, e.g.
M OMEPyramidWriter.Builder.pixelType(qupath.lib.images.servers.PixelType exportPixelType) -> OMEPyramidWriter.Builder // Specify the output PixelType.
M OMEPyramidWriter.Builder.region(int x, int y, int width, int height) -> OMEPyramidWriter.Builder // Define the region to export based on a bounding box.
M OMEPyramidWriter.Builder.region(qupath.lib.regions.ImageRegion region) -> OMEPyramidWriter.Builder // Define the region to export, including the z-slice and time point.
M OMEPyramidWriter.Builder.scaledDownsampling(double scale) -> OMEPyramidWriter.Builder // Downsample by specific increasing factor each time (e.g.
M OMEPyramidWriter.Builder.scaledDownsampling(double minDownsample, double scale) -> OMEPyramidWriter.Builder // Downsample by specific increasing factor each time, with a specified initial downsample value (e.g.
M OMEPyramidWriter.Builder.tileSize(int tileSize) -> OMEPyramidWriter.Builder // Define the requested tile size (width == height).
M OMEPyramidWriter.Builder.tileSize(int tileWidth, int tileHeight) -> OMEPyramidWriter.Builder // Define the requested tile width and height.
M OMEPyramidWriter.Builder.timePoint(int t) -> OMEPyramidWriter.Builder // Specify a single timepoint to be written from a time series.
M OMEPyramidWriter.Builder.timePoints(int tStart, int tEnd) -> OMEPyramidWriter.Builder // Specify a range of timepoints to be written from a time series.
M OMEPyramidWriter.Builder.uncompressed() -> OMEPyramidWriter.Builder // Request no compression.
M OMEPyramidWriter.Builder.zSlice(int z) -> OMEPyramidWriter.Builder // Specify the z-slice to export.
M OMEPyramidWriter.Builder.zSlices(int zStart, int zEnd) -> OMEPyramidWriter.Builder // Specify the start (inclusive) and end (exclusive) z-slices.

## qupath.lib.images.writers.ome.OMEPyramidWriter.ChannelExportType [Enum]
Enum representing different ways in which channels may be written to a file.
E OMEPyramidWriter.ChannelExportType.DEFAULT // Leave it up to the writer to choose the appropriate method.
E OMEPyramidWriter.ChannelExportType.IMAGES // Channels are stored as separate images (this is not yet supported!).
E OMEPyramidWriter.ChannelExportType.INTERLEAVED // Channels are interleaved ('PLANARCONFIG_CONTIG').
E OMEPyramidWriter.ChannelExportType.PLANAR // Channels are stored as separate image planes ('PLANARCONFIG_SEPARATE').
M OMEPyramidWriter.ChannelExportType.valueOf(String name) -> static OMEPyramidWriter.ChannelExportType // Returns the enum constant of this class with the specified name.
M OMEPyramidWriter.ChannelExportType.values() -> static OMEPyramidWriter.ChannelExportType[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.lib.images.writers.ome.OMEPyramidWriter.CompressionType [Enum]
Preferred compression type when using Bio-Formats.
E OMEPyramidWriter.CompressionType.DEFAULT // Default (QuPath will select compression option based on image size and type, may be lossless or lossy).
E OMEPyramidWriter.CompressionType.J2K // Lossless JPEG-2000 compression.
E OMEPyramidWriter.CompressionType.J2K_LOSSY // Lossy JPEG-2000 compression.
E OMEPyramidWriter.CompressionType.JPEG // JPEG compression (only for single channel or RGB 8-bit images).
E OMEPyramidWriter.CompressionType.LZW // LZW compression.
E OMEPyramidWriter.CompressionType.UNCOMPRESSED // No compression (faster to write, no loss of information, but large file sizes).
E OMEPyramidWriter.CompressionType.ZLIB // ZLIB compression.
M OMEPyramidWriter.CompressionType.fromFriendlyString(String friendlyCompression) -> static OMEPyramidWriter.CompressionType // Get the CompressionType corresponding to the given input
M OMEPyramidWriter.CompressionType.getOMEString(qupath.lib.images.servers.ImageServer<?> server) -> String // Get the String representation understood by OMETiffWriter.
M OMEPyramidWriter.CompressionType.supportsImage(qupath.lib.images.servers.ImageServer<?> server) -> boolean // Returns true if the compression type supports a specific image server, or false if it is incompatible.
M OMEPyramidWriter.CompressionType.supportsImage(qupath.lib.images.servers.PixelType pixelType, int nChannels, boolean isRGB) -> boolean // Returns true if the compression type supports a specific PixelType output with the given number of channels - and (optionally) RGB status.
M OMEPyramidWriter.CompressionType.toFriendlyString() -> String // Get a friendlier string representation
M OMEPyramidWriter.CompressionType.valueOf(String name) -> static OMEPyramidWriter.CompressionType // Returns the enum constant of this class with the specified name.
M OMEPyramidWriter.CompressionType.values() -> static OMEPyramidWriter.CompressionType[] // Returns an array containing the constants of this enum class, in the order they are declared.

## qupath.lib.images.writers.ome.OMEPyramidWriter.OMEPyramidSeries [Class]
Class representing a single series to write to an OME-TIFF.
M OMEPyramidWriter.OMEPyramidSeries.writePyramid(String path) -> void // Deprecated.
M OMEPyramidWriter.OMEPyramidSeries.writePyramid(PyramidOMETiffWriter writer, IMetadata meta, int series) -> void // Deprecated.
M OMEPyramidWriter.OMEPyramidSeries.writeSeries(String path) -> void // Write an image to the given file.
M OMEPyramidWriter.OMEPyramidSeries.writeSeries(IFormatWriter writer, IMetadata meta, int series) -> void // Append an image as a specific series.

## qupath.lib.images.writers.ome.OMEPyramidWriter [Class]
Write OME-TIFF files based on QuPath ImageServers.
M OMEPyramidWriter.createWriter(Collection<OMEPyramidWriter.OMEPyramidSeries> series) -> static OMEPyramidWriter // Create a writer capable of writing an image with a collection of series.
M OMEPyramidWriter.createWriter(OMEPyramidWriter.OMEPyramidSeries... series) -> static OMEPyramidWriter // Create a writer capable of writing an image with one or more series.
M OMEPyramidWriter.writeImage(String path) -> void // Write an image consisting of one or more series to the specified path.
M OMEPyramidWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, String path) -> static void // Static helper method to write an image using Bio-Formats.
M OMEPyramidWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, String path, OMEPyramidWriter.CompressionType compression) -> static void // Static helper method to write an image using Bio-Formats with the specified compression.
M OMEPyramidWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, String path, OMEPyramidWriter.CompressionType compression, qupath.lib.regions.ImageRegion region) -> static void // Static helper method to write an image region using Bio-Formats with the specified compression.
M OMEPyramidWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, String path, OMEPyramidWriter.CompressionType compression, qupath.lib.regions.ImageRegion region, boolean allZ, boolean allT) -> static void // Static helper method to write an image using Bio-Formats for a defined region with the specified compression, optionally including all z-slices or timepoints.

## qupath.lib.images.writers.ome.OMEPyramidWriterCommand [Class]
OME TIFF writer command capable of exporting image pyramids based on QuPath ImageServers.
C new Description -> Constructor // 
C new OMEPyramidWriterCommand(qupath.lib.gui.QuPathGUI qupath) // Constructor.
M OMEPyramidWriterCommand.getDefaultPyramidCompression() -> static OMEPyramidWriter.CompressionType // Query the default compression type when writing OME-TIFF images.
M OMEPyramidWriterCommand.getDefaultTileSize() -> static int // Query the default tile size when writing OME-TIFF images.
M OMEPyramidWriterCommand.getMinSizeForTiling() -> static int // Query the default minimum image size when writing OME-TIFF images.
M OMEPyramidWriterCommand.run() -> void // 

## qupath.lib.images.writers.ome.OMETiffWriter [Class]
ImageWriter for writing OME-TIFF images.
C new Description -> Constructor // 
C new OMETiffWriter() // 
M OMETiffWriter.getDetails() -> String // 
M OMETiffWriter.getExtensions() -> Collection<String> // 
M OMETiffWriter.getImageClass() -> Class<BufferedImage> // 
M OMETiffWriter.getName() -> String // 
M OMETiffWriter.supportsImageType(qupath.lib.images.servers.ImageServer<BufferedImage> server) -> boolean // 
M OMETiffWriter.supportsPixelSize() -> boolean // 
M OMETiffWriter.supportsPyramidal() -> boolean // 
M OMETiffWriter.supportsRGB() -> boolean // 
M OMETiffWriter.supportsT() -> boolean // 
M OMETiffWriter.supportsZ() -> boolean // 
M OMETiffWriter.writeImage(BufferedImage img, OutputStream stream) -> void // 
M OMETiffWriter.writeImage(BufferedImage img, String pathOutput) -> void // 
M OMETiffWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, OutputStream stream) -> void // Write OME-TIFF image to an output stream.
M OMETiffWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, String pathOutput) -> void // 
M OMETiffWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.regions.RegionRequest region, OutputStream stream) -> void // Write OME-TIFF image to an output stream.
M OMETiffWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.regions.RegionRequest region, String pathOutput) -> void // 

## qupath.lib.images.writers.ome.zarr.OMEZarrImageWriter [Class]
An ImageWriter for writing OME-zarr files.
C new Description -> Constructor // 
C new OMEZarrImageWriter() // 
M OMEZarrImageWriter.getDetails() -> String // 
M OMEZarrImageWriter.getExtensions() -> Collection<String> // 
M OMEZarrImageWriter.getImageClass() -> Class<BufferedImage> // 
M OMEZarrImageWriter.getName() -> String // 
M OMEZarrImageWriter.supportsImageType(qupath.lib.images.servers.ImageServer<BufferedImage> server) -> boolean // 
M OMEZarrImageWriter.supportsPixelSize() -> boolean // 
M OMEZarrImageWriter.supportsPyramidal() -> boolean // 
M OMEZarrImageWriter.supportsRGB() -> boolean // 
M OMEZarrImageWriter.supportsT() -> boolean // 
M OMEZarrImageWriter.supportsZ() -> boolean // 
M OMEZarrImageWriter.writeImage(BufferedImage img, OutputStream stream) -> void // 
M OMEZarrImageWriter.writeImage(BufferedImage img, String pathOutput) -> void // 
M OMEZarrImageWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, OutputStream stream) -> void // 
M OMEZarrImageWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, String pathOutput) -> void // 
M OMEZarrImageWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.regions.RegionRequest region, OutputStream stream) -> void // 
M OMEZarrImageWriter.writeImage(qupath.lib.images.servers.ImageServer<BufferedImage> server, qupath.lib.regions.RegionRequest region, String pathOutput) -> void // 

## qupath.lib.images.writers.ome.zarr.OMEZarrWriter.Builder [Class]
Builder to create an instance of a OMEZarrWriter.
C new Description -> Constructor // 
C new Builder(qupath.lib.images.servers.ImageServer<BufferedImage> server) // Create the builder.
M OMEZarrWriter.Builder.build(String path) -> OMEZarrWriter // Create a new instance of OMEZarrWriter.
M OMEZarrWriter.Builder.compression(com.bc.zarr.Compressor compressor) -> OMEZarrWriter.Builder // Set the compressor to use when writing tiles.
M OMEZarrWriter.Builder.downsamples(double... downsamples) -> OMEZarrWriter.Builder // Enable the creation of a pyramidal image with the provided downsamples.
M OMEZarrWriter.Builder.onTileWritten(Consumer<qupath.lib.images.servers.TileRequest> onTileWritten) -> OMEZarrWriter.Builder // Set a function that will be called each time a TileRequest is successfully or unsuccessfully written.
M OMEZarrWriter.Builder.parallelize(int numberOfThreads) -> OMEZarrWriter.Builder // Tiles will be written from a pool of thread.
M OMEZarrWriter.Builder.region(qupath.lib.regions.ImageRegion boundingBox) -> OMEZarrWriter.Builder // Define a region (on the x-axis and y-axis) of the input image to consider.
M OMEZarrWriter.Builder.setMaxNumberOfChunksOnEachSpatialDimension(int maxNumberOfChunks) -> OMEZarrWriter.Builder // In Zarr images, data is stored in chunks.
M OMEZarrWriter.Builder.tileSize(int tileSize) -> OMEZarrWriter.Builder // In Zarr images, data is stored in chunks.
M OMEZarrWriter.Builder.tileSize(int tileWidth, int tileHeight) -> OMEZarrWriter.Builder // In Zarr images, data is stored in chunks.
M OMEZarrWriter.Builder.timePoints(int tStart, int tEnd) -> OMEZarrWriter.Builder // Define the timepoints of the input image to consider.
M OMEZarrWriter.Builder.zSlices(int zStart, int zEnd) -> OMEZarrWriter.Builder // Define the z-slices of the input image to consider.

## qupath.lib.images.writers.ome.zarr.OMEZarrWriter [Class]
An OME-Zarr file writer as described by version 0.4 of the specifications of the Next-generation file formats (NGFF).
M OMEZarrWriter.getReaderServer() -> qupath.lib.images.servers.ImageServer<BufferedImage> // Get the image server used internally by this writer to read the tiles.
M OMEZarrWriter.writeImage() -> void // Write the entire image.
M OMEZarrWriter.writeTile(qupath.lib.images.servers.TileRequest tileRequest) -> void // Write the provided tile.

## qupath.lib.images.writers.ome.zarr.OMEZarrWriterCommand [Class]
A GUI command to export the current ImageServer to an OME Zarr directory.
C new Description -> Constructor // 
C new OMEZarrWriterCommand(qupath.lib.gui.QuPathGUI qupath) // Create the command
M OMEZarrWriterCommand.run() -> void // 

## qupath.lib.images.writers.ome.zarr.PyramidalOMEZarrWriter.Builder [Class]
Builder to create an instance of a PyramidalOMEZarrWriter.
C new Description -> Constructor // 
C new Builder(qupath.lib.images.servers.ImageServer<BufferedImage> server) // Create the builder.
M PyramidalOMEZarrWriter.Builder.build(String path) -> PyramidalOMEZarrWriter // Create a new instance of PyramidalOMEZarrWriter.
M PyramidalOMEZarrWriter.Builder.compression(com.bc.zarr.Compressor compressor) -> PyramidalOMEZarrWriter.Builder // Set the compressor to use when writing the image.
M PyramidalOMEZarrWriter.Builder.downsamples(double... downsamples) -> PyramidalOMEZarrWriter.Builder // Enable the creation of a pyramidal image with the provided downsamples.
M PyramidalOMEZarrWriter.Builder.onProgress(DoubleConsumer onProgress) -> PyramidalOMEZarrWriter.Builder // Set a function that will be called at different steps when the writing occurs.
M PyramidalOMEZarrWriter.Builder.parallelize(int numberOfThreads) -> PyramidalOMEZarrWriter.Builder // Tiles will be written from a pool of thread.
M PyramidalOMEZarrWriter.Builder.region(qupath.lib.regions.ImageRegion boundingBox) -> PyramidalOMEZarrWriter.Builder // Define a region (on the x-axis and y-axis) of the input image to consider.
M PyramidalOMEZarrWriter.Builder.setMaxNumberOfChunksOnEachSpatialDimension(int maxNumberOfChunks) -> PyramidalOMEZarrWriter.Builder // In Zarr images, data is stored in chunks.
M PyramidalOMEZarrWriter.Builder.tileSize(int tileSize) -> PyramidalOMEZarrWriter.Builder // In Zarr images, data is stored in chunks.
M PyramidalOMEZarrWriter.Builder.tileSize(int tileWidth, int tileHeight) -> PyramidalOMEZarrWriter.Builder // In Zarr images, data is stored in chunks.
M PyramidalOMEZarrWriter.Builder.timePoints(int tStart, int tEnd) -> PyramidalOMEZarrWriter.Builder // Define the timepoints of the input image to consider.
M PyramidalOMEZarrWriter.Builder.zSlices(int zStart, int zEnd) -> PyramidalOMEZarrWriter.Builder // Define the z-slices of the input image to consider.

## qupath.lib.images.writers.ome.zarr.PyramidalOMEZarrWriter [Class]
An OME-Zarr file writer as described by version 0.4 of the specifications of the Next-generation file formats (NGFF).
M PyramidalOMEZarrWriter.writeImage() -> void // Write the image level by level as described in PyramidalOMEZarrWriter.
