"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.scatter = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Scatter chart data schema
const data = zod_1.z.object({
    x: zod_1.z.number(),
    y: zod_1.z.number(),
    group: zod_1.z.string().optional().describe("Group name for the data point."),
});
// Scatter chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for scatter chart, such as, [{ x: 10, y: 15 }], when the data is grouped, the group name can be specified in the `group` field, such as, [{ x: 10, y: 15, group: 'Group A' }].")
        .nonempty({ message: "Scatter chart data cannot be empty." }),
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
// Scatter chart tool descriptor
const tool = {
    name: "generate_scatter_chart",
    description: "Generate a scatter chart to show the relationship between two variables, helps discover their relationship or trends, such as, the strength of correlation, data distribution patterns.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Scatter Chart",
        readOnlyHint: true,
    },
};
exports.scatter = {
    schema,
    tool,
};
