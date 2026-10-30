"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.bar = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Bar chart data schema
const data = zod_1.z.object({
    category: zod_1.z.string(),
    value: zod_1.z.number(),
    group: zod_1.z.string().optional(),
});
// Bar chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for bar chart, such as, [{ category: '分类一', value: 10 }, { category: '分类二', value: 20 }], when grouping or stacking is needed for bar, the data should contain a `group` field, such as, when [{ category: '北京', value: 825, group: '油车' }, { category: '北京', value: 1000, group: '电车' }].")
        .nonempty({ message: "Bar chart data cannot be empty." }),
    group: zod_1.z
        .boolean()
        .optional()
        .default(false)
        .describe("Whether grouping is enabled. When enabled, bar charts require a 'group' field in the data. When `group` is true, `stack` should be false."),
    stack: zod_1.z
        .boolean()
        .optional()
        .default(true)
        .describe("Whether stacking is enabled. When enabled, bar charts require a 'group' field in the data. When `stack` is true, `group` should be false."),
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
// Bar chart tool descriptor
const tool = {
    name: "generate_bar_chart",
    description: "Generate a horizontal bar chart to show data for numerical comparisons among different categories, such as, comparing categorical data and for horizontal comparisons.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Bar Chart",
        readOnlyHint: true,
    },
};
exports.bar = {
    schema,
    tool,
};
