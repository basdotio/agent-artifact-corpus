"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.column = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Column chart data schema
const data = zod_1.z.object({
    category: zod_1.z.string(),
    value: zod_1.z.number(),
    group: zod_1.z.string().optional(),
});
// Column chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for column chart, such as, [{ category: 'Category A', value: 10 }, { category: 'Category B', value: 20 }], when grouping or stacking is needed for column, the data should contain a 'group' field, such as, [{ category: 'Beijing', value: 825, group: 'Gas Car' }, { category: 'Beijing', value: 1000, group: 'Electric Car' }].")
        .nonempty({ message: "Column chart data cannot be empty." }),
    group: zod_1.z
        .boolean()
        .optional()
        .default(true)
        .describe("Whether grouping is enabled. When enabled, column charts require a 'group' field in the data. When `group` is true, `stack` should be false."),
    stack: zod_1.z
        .boolean()
        .optional()
        .default(false)
        .describe("Whether stacking is enabled. When enabled, column charts require a 'group' field in the data. When `stack` is true, `group` should be false."),
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
// Column chart tool descriptor
const tool = {
    name: "generate_column_chart",
    description: "Generate a column chart, which are best for comparing categorical data, such as, when values are close, column charts are preferable because our eyes are better at judging height than other visual elements like area or angles.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Column Chart",
        readOnlyHint: true,
    },
};
exports.column = {
    schema,
    tool,
};
