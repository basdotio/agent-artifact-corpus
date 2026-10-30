"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.pie = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Pie chart data schema
const data = zod_1.z.object({
    category: zod_1.z.string(),
    value: zod_1.z.number(),
});
// Pie chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for pie chart, it should be an array of objects, each object contains a `category` field and a `value` field, such as, [{ category: '分类一', value: 27 }].")
        .nonempty({ message: "Pie chart data cannot be empty." }),
    innerRadius: zod_1.z
        .number()
        .default(0)
        .describe("Set the innerRadius of pie chart, the value between 0 and 1. Set the pie chart as a donut chart. Set the value to 0.6 or number in [0 ,1] to enable it."),
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
};
// Pie chart tool descriptor
const tool = {
    name: "generate_pie_chart",
    description: "Generate a pie chart to show the proportion of parts, such as, market share and budget allocation.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Pie Chart",
        readOnlyHint: true,
    },
};
exports.pie = {
    schema,
    tool,
};
