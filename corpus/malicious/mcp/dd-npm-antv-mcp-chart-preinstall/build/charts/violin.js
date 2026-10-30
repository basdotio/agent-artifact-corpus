"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.violin = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const data = zod_1.z.object({
    category: zod_1.z
        .string()
        .describe("Category of the data point, such as '分类一'."),
    value: zod_1.z.number().describe("Value of the data point, such as 10."),
    group: zod_1.z
        .string()
        .optional()
        .describe("Optional group for the data point, used for grouping in the violin chart."),
});
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for violin chart, such as, [{ category: 'Category A', value: 10 }], when the data is grouped, the 'group' field is required, such as, [{ category: 'Category B', value: 20, group: 'Group A' }].")
        .nonempty({ message: "Violin chart data cannot be empty." }),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        palette: base_1.PaletteSchema,
        startAtZero: base_1.StartAtZeroSchema,
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
const tool = {
    name: "generate_violin_chart",
    description: "Generate a violin chart to show data for statistical summaries among different categories, such as, comparing the distribution of data points across categories.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Violin Chart",
        readOnlyHint: true,
    },
};
exports.violin = {
    schema,
    tool,
};
