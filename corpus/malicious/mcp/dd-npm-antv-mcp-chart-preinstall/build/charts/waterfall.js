"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.waterfall = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const data = zod_1.z
    .object({
    category: zod_1.z.string(),
    value: zod_1.z.number().optional(),
    isIntermediateTotal: zod_1.z.boolean().optional(),
    isTotal: zod_1.z.boolean().optional(),
})
    .superRefine((item, ctx) => {
    if (!item.isIntermediateTotal &&
        !item.isTotal &&
        item.value === undefined) {
        ctx.addIssue({
            code: zod_1.z.ZodIssueCode.custom,
            message: "The 'value' field is required for data points that are not totals.",
            path: ["value"],
        });
    }
});
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for waterfall chart, it should be an array of objects. Each object must contain a `category` field. For regular items, a `value` field is also required. The `isIntermediateTotal` field marks intermediate subtotals, and the `isTotal` field marks the final total. For example, [{ category: 'Initial', value: 100 }, { category: 'Increase', value: 50 }, { category: 'Subtotal', isIntermediateTotal: true }, { category: 'Decrease', value: -30 }, { category: 'Total', isTotal: true }].")
        .nonempty({ message: "Waterfall chart data cannot be empty." }),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        texture: base_1.TextureSchema,
        palette: zod_1.z
            .object({
            positiveColor: zod_1.z
                .string()
                .optional()
                .describe("Color for positive values (increases). Default is '#FF4D4F'."),
            negativeColor: zod_1.z
                .string()
                .optional()
                .describe("Color for negative values (decreases). Default is '#2EBB59'."),
            totalColor: zod_1.z
                .string()
                .optional()
                .describe("Color for total and intermediate total bars. Default is '#1783FF'."),
        })
            .optional(),
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
// Waterfall chart tool descriptor
const tool = {
    name: "generate_waterfall_chart",
    description: "Generate a waterfall chart to visualize the cumulative effect of sequentially introduced positive or negative values, such as showing how an initial value is affected by a series of intermediate positive or negative values leading to a final result. Waterfall charts are ideal for financial analysis, budget tracking, profit and loss statements, and understanding the composition of changes over time or categories.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Waterfall Chart",
        readOnlyHint: true,
    },
};
exports.waterfall = {
    schema,
    tool,
};
