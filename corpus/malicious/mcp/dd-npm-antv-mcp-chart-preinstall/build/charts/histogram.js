"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.histogram = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Histogram chart input schema
const schema = {
    data: zod_1.z
        .array(zod_1.z.number())
        .describe("Data for histogram chart, it should be an array of numbers, such as, [78, 88, 60, 100, 95].")
        .nonempty({ message: "Histogram chart data cannot be empty." }),
    binNumber: zod_1.z
        .number()
        .optional()
        .describe("Number of intervals to define the number of intervals in a histogram, when not specified, a built-in value will be used."),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        palette: base_1.PaletteSchema,
        texture: base_1.TextureSchema,
    })
        .optional()
        .describe("Style configuration for the chart with a JSON object, optional."),
    theme: base_1.ThemeSchema,
    width: base_1.WidthSchema,
    height: base_1.HeightSchema,
    title: base_1.TitleSchema,
    axisXTitle: base_1.AxisXTitleSchema,
    axisYTitle: base_1.AxisYTitleSchema,
};
// Histogram chart tool descriptor
const tool = {
    name: "generate_histogram_chart",
    description: "Generate a histogram chart to show the frequency of data points within a certain range. It can observe data distribution, such as, normal and skewed distributions, and identify data concentration areas and extreme points.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Histogram Chart",
        readOnlyHint: true,
    },
};
exports.histogram = {
    schema,
    tool,
};
