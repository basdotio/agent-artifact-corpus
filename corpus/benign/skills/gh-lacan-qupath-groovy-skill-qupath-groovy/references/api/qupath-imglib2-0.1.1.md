# qupath-imglib2-0.1.1

## qupath.imglib.qupath.ext.imglib2.AccessibleScaler [Class]
A collection of static functions to scale RandomAccessibleInterval.
M AccessibleScaler.scale(net.imglib2.RandomAccessibleInterval<T> input, double scale, net.imglib2.interpolation.InterpolatorFactory<T,net.imglib2.RandomAccessible<T>> interpolatorFactory) -> static <T> net.imglib2.RandomAccessibleInterval<T> // Scale the two first dimensions of the provided RandomAccessibleInterval using the provided interpolation.
M AccessibleScaler.scaleWithLinearInterpolation(net.imglib2.RandomAccessibleInterval<T> input, double scale) -> static <T extends net.imglib2.type.numeric.NumericType<T>>net.imglib2.RandomAccessibleInterval<T> // Scale the two first dimensions of the provided RandomAccessibleInterval using a linear interpolation.
M AccessibleScaler.scaleWithNearestNeighborInterpolation(net.imglib2.RandomAccessibleInterval<T> input, double scale) -> static <T> net.imglib2.RandomAccessibleInterval<T> // Scale the two first dimensions of the provided RandomAccessibleInterval using the nearest neighbor interpolation.

## qupath.imglib.qupath.ext.imglib2.CellCache [Class]
A cache for Cell associated with TileRequest.
C new Description -> Constructor // 
C new CellCache(int cacheMaxSizeMiB) // Create a cache with the specified maximum size.
M CellCache.getCell(qupath.lib.images.servers.TileRequest tileRequest, Function<qupath.lib.images.servers.TileRequest,net.imglib2.img.cell.Cell<? extends SizableDataAccess>> cellGetter) -> net.imglib2.img.cell.Cell<? extends SizableDataAccess> // Get a cached cell corresponding to the provided tile request, or compute it if the cache doesn't contain such cell.

## qupath.imglib.qupath.ext.imglib2.ImgBuilder [Class]
A class to create Img or RandomAccessibleInterval from an ImageServer.
F ImgBuilder.AXIS_CHANNEL -> static final int // The index of the channel axis of accessibles returned by functions of this class
F ImgBuilder.AXIS_TIME -> static final int // The index of the time axis of accessibles returned by functions of this class
F ImgBuilder.AXIS_X -> static final int // The index of the X axis of accessibles returned by functions of this class
F ImgBuilder.AXIS_Y -> static final int // The index of the Y axis of accessibles returned by functions of this class
F ImgBuilder.AXIS_Z -> static final int // The index of the Z axis of accessibles returned by functions of this class
F ImgBuilder.NUMBER_OF_AXES -> static final int // The number of axes of accessibles returned by functions of this class
M ImgBuilder.buildForAllLevels() -> List<net.imglib2.RandomAccessibleInterval<T>> // Create a list of RandomAccessibleInterval corresponding to each level of the input image.
M ImgBuilder.buildForDownsample(double downsample) -> net.imglib2.RandomAccessibleInterval<T> // Create a RandomAccessibleInterval from the input image and the provided downsample.
M ImgBuilder.buildForDownsamples(List<? extends Number> downsamples) -> List<net.imglib2.RandomAccessibleInterval<T>> // Create a list of RandomAccessibleInterval from the input image and the provided downsamples.
M ImgBuilder.buildForLevel(int level) -> net.imglib2.RandomAccessibleInterval<T> // Create an Img from the input image and the provided level.
M ImgBuilder.cellCache(CellCache cellCache) -> ImgBuilder<T> // Accessibles returned by this class will be divided into cells, which will be cached to gain performance.
M ImgBuilder.createBuilder(qupath.lib.images.servers.ImageServer<BufferedImage> server) -> static <T extends net.imglib2.type.numeric.NumericType<T>>ImgBuilder<? extends net.imglib2.type.numeric.NumericType<?>> // Create a builder from an ImageServer.
M ImgBuilder.createBuilder(qupath.lib.images.servers.ImageServer<BufferedImage> server, T type) -> static <T extends net.imglib2.type.numeric.NumericType<T>>ImgBuilder<T> // Create a builder from an ImageServer.
M ImgBuilder.createRealBuilder(qupath.lib.images.servers.ImageServer<BufferedImage> server) -> static <T extends net.imglib2.type.numeric.RealType<T>>ImgBuilder<? extends net.imglib2.type.numeric.RealType<?>> // Create a builder from an ImageServer, where the type is known to be an instance of RealType.
M ImgBuilder.createRealBuilder(qupath.lib.images.servers.ImageServer<BufferedImage> server, T type) -> static <T extends net.imglib2.type.numeric.RealType<T>>ImgBuilder<T> // Create a builder from an ImageServer, where the type is specified and an instance of RealType.
M ImgBuilder.createRgbBuilder(qupath.lib.images.servers.ImageServer<BufferedImage> server) -> static ImgBuilder<net.imglib2.type.numeric.ARGBType> // Create a builder from an ImageServer representing an RGB image using ARGBType.
M ImgBuilder.getDefaultType(qupath.lib.images.servers.ImageServer<?> server) -> static net.imglib2.type.numeric.NumericType<?> // Create an instance of the default type for a server when using createBuilder(ImageServer).
M ImgBuilder.getRealType(qupath.lib.images.servers.ImageServer<?> server) -> static net.imglib2.type.numeric.RealType<?> // Create an instance of the default RealType for an image server.
M ImgBuilder.getRealType(qupath.lib.images.servers.PixelType pixelType) -> static <T extends net.imglib2.type.numeric.RealType<T>>T // Create the default RealType for a pixel type.
M ImgBuilder.getRgbType() -> static net.imglib2.type.numeric.ARGBType // Create an instance of the default type for an RGB image, using a packed int representation so that all RGB values can be contained in a single 'channel'.

## qupath.imglib.qupath.ext.imglib2.ImgLib2ImageServer.Builder [Class]
A builder to create an instance of ImgLib2ImageServer.
M ImgLib2ImageServer.Builder.build() -> ImgLib2ImageServer<T> // Create an ImgLib2ImageServer from this builder.
M ImgLib2ImageServer.Builder.channels(Collection<qupath.lib.images.servers.ImageChannel> channels) -> ImgLib2ImageServer.Builder<T> // Set the channels of the ImgLib2ImageServer to build.
M ImgLib2ImageServer.Builder.metadata(qupath.lib.images.servers.ImageServerMetadata metadata) -> ImgLib2ImageServer.Builder<T> // Set metadata parameters of the ImgLib2ImageServer to build.
M ImgLib2ImageServer.Builder.name(String name) -> ImgLib2ImageServer.Builder<T> // Set the name of the ImgLib2ImageServer to build.
M ImgLib2ImageServer.Builder.pixelCalibration(qupath.lib.images.servers.PixelCalibration pixelCalibration) -> ImgLib2ImageServer.Builder<T> // Set the pixel calibration of the ImgLib2ImageServer to build.
M ImgLib2ImageServer.Builder.preferredTileSize(int tileWidth, int tileHeight) -> ImgLib2ImageServer.Builder<T> // Set the tile size of the ImgLib2ImageServer to build.

## qupath.imglib.qupath.ext.imglib2.ImgLib2ImageServer [Class]
An ImageServer whose pixel values come from RandomAccessibleInterval.
M ImgLib2ImageServer.builder(List<? extends net.imglib2.RandomAccessibleInterval<T>> accessibles) -> static <T extends net.imglib2.type.NativeType<T> & net.imglib2.type.numeric.NumericType<T>>ImgLib2ImageServer.Builder<T> // Create a ImgLib2ImageServer builder.
M ImgLib2ImageServer.getOriginalMetadata() -> qupath.lib.images.servers.ImageServerMetadata // 
M ImgLib2ImageServer.getServerType() -> String // 
M ImgLib2ImageServer.getURIs() -> Collection<URI> // 

## qupath.imglib.qupath.ext.imglib2.SizableDataAccess [Interface]
A DataAccess whose size can be computed.
M SizableDataAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.

## qupath.imglib.qupath.ext.imglib2.accesses.ArgbBufferedImageAccess [Class]
An IntAccess whose elements are computed from an (A)RGB BufferedImage.
C new Description -> Constructor // 
C new ArgbBufferedImageAccess(BufferedImage image) // Create the buffered image access.
M ArgbBufferedImageAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M ArgbBufferedImageAccess.getValue(int index) -> int // 
M ArgbBufferedImageAccess.isValid() -> boolean // 
M ArgbBufferedImageAccess.setValue(int index, int value) -> void // 

## qupath.imglib.qupath.ext.imglib2.accesses.ByteBufferedImageAccess [Class]
An ByteAccess whose elements are computed from an RGB BufferedImage.
C new Description -> Constructor // 
C new ByteBufferedImageAccess(BufferedImage image) // Create the byte buffered image access.
M ByteBufferedImageAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M ByteBufferedImageAccess.getValue(int index) -> byte // 
M ByteBufferedImageAccess.isValid() -> boolean // 
M ByteBufferedImageAccess.setValue(int index, byte value) -> void // 

## qupath.imglib.qupath.ext.imglib2.accesses.ByteRasterAccess [Class]
A ByteAccess whose elements are computed from a Raster.
C new Description -> Constructor // 
C new ByteRasterAccess(Raster raster) // Create the byte raster access.
M ByteRasterAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M ByteRasterAccess.getValue(int index) -> byte // 
M ByteRasterAccess.isValid() -> boolean // 
M ByteRasterAccess.setValue(int index, byte value) -> void // 

## qupath.imglib.qupath.ext.imglib2.accesses.DoubleRasterAccess [Class]
A DoubleAccess whose elements are computed from a Raster.
C new Description -> Constructor // 
C new DoubleRasterAccess(Raster raster) // Create the double raster access.
M DoubleRasterAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M DoubleRasterAccess.getValue(int index) -> double // 
M DoubleRasterAccess.isValid() -> boolean // 
M DoubleRasterAccess.setValue(int index, double value) -> void // 

## qupath.imglib.qupath.ext.imglib2.accesses.FloatRasterAccess [Class]
A FloatAccess whose elements are computed from a Raster.
C new Description -> Constructor // 
C new FloatRasterAccess(Raster raster) // Create the float raster access.
M FloatRasterAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M FloatRasterAccess.getValue(int index) -> float // 
M FloatRasterAccess.isValid() -> boolean // 
M FloatRasterAccess.setValue(int index, float value) -> void // 

## qupath.imglib.qupath.ext.imglib2.accesses.IntRasterAccess [Class]
An IntAccess whose elements are computed from a Raster.
C new Description -> Constructor // 
C new IntRasterAccess(Raster raster) // Create the int raster access.
M IntRasterAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M IntRasterAccess.getValue(int index) -> int // 
M IntRasterAccess.isValid() -> boolean // 
M IntRasterAccess.setValue(int index, int value) -> void // 

## qupath.imglib.qupath.ext.imglib2.accesses.ShortRasterAccess [Class]
A ShortAccess whose elements are computed from a Raster.
C new Description -> Constructor // 
C new ShortRasterAccess(Raster raster) // Create the short raster access.
M ShortRasterAccess.getSizeBytes() -> int // Get the size of this DataAccess in bytes.
M ShortRasterAccess.getValue(int index) -> short // 
M ShortRasterAccess.isValid() -> boolean // 
M ShortRasterAccess.setValue(int index, short value) -> void // 

## qupath.imglib.qupath.ext.imglib2.interpolators.LinearInterpolationFactory [Class]
An InterpolatorFactory that implements a 2D linear interpolation.
C new Description -> Constructor // 
C new LinearInterpolationFactory() // 
M LinearInterpolationFactory.create(net.imglib2.RandomAccessible randomAccessible) -> net.imglib2.RealRandomAccess<T> // 
M LinearInterpolationFactory.create(net.imglib2.RandomAccessible<T> randomAccessible, net.imglib2.RealInterval interval) -> net.imglib2.RealRandomAccess<T> // 
