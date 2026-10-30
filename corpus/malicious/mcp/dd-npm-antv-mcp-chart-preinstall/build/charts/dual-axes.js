"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.dualAxes = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Dual axes series schema
const DualAxesSeriesSchema = zod_1.z.object({
    type: zod_1.z
        .enum(["column", "line"])
        .describe("The optional value can be 'column' or 'line'."),
    data: zod_1.z
        .array(zod_1.z.number())
        .describe("When type is column, the data represents quantities, such as [91.9, 99.1, 101.6, 114.4, 121]. When type is line, the data represents ratios and its values are recommended to be less than 1, such as [0.055, 0.06, 0.062, 0.07, 0.075]."),
    axisYTitle: zod_1.z
        .string()
        .default("")
        .describe("Set the y-axis title of the chart series, such as, axisYTitle: '销售额'.")
        .optional(),
});
// Dual axes chart input schema
const schema = {
    categories: zod_1.z
        .array(zod_1.z.string())
        .describe("Categories for dual axes chart, such as, ['2015', '2016', '2017'].")
        .nonempty({ message: "Dual axes chart categories cannot be empty." }),
    series: zod_1.z
        .array(DualAxesSeriesSchema)
        .describe("Series for dual axes chart, such as, [{ type: 'column', data: [91.9, 99.1, 101.6, 114.4, 121], axisYTitle: '销售额' }, { type: 'line', data: [0.055, 0.06, 0.062, 0.07, 0.075], 'axisYTitle': '利润率' }].")
        .nonempty({ message: "Dual axes chart series cannot be empty." }),
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
};
// Dual axes chart tool descriptor
const tool = {
    name: "generate_dual_axes_chart",
    description: "Generate a dual axes chart which is a combination chart that integrates two different chart types, typically combining a bar chart with a line chart to display both the trend and comparison of data, such as, the trend of sales and profit over time.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Dual Axes Chart",
        readOnlyHint: true,
    },
};
exports.dualAxes = {
    schema,
    tool,
};
