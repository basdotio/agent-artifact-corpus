"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.liquid = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const schema = {
    percent: zod_1.z
        .number()
        .describe("The percentage value to display in the liquid chart, should be a number between 0 and 1, where 1 represents 100%. For example, 0.75 represents 75%.")
        .min(0, { message: "Value must be at least 0." })
        .max(1, { message: "Value must be at most 1." }),
    shape: zod_1.z
        .enum(["circle", "rect", "pin", "triangle"])
        .optional()
        .default("circle")
        .describe("The shape of the liquid chart, can be 'circle', 'rect', 'pin', or 'triangle'. Default is 'circle'."),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        texture: base_1.TextureSchema,
        color: zod_1.z
            .string()
            .optional()
            .describe("Custom color for the liquid chart, if not specified, defaults to the theme color."),
    })
        .optional()
        .describe("Style configuration for the chart with a JSON object, optional."),
    theme: base_1.ThemeSchema,
    width: base_1.WidthSchema,
    height: base_1.HeightSchema,
    title: base_1.TitleSchema,
};
const tool = {
    name: "generate_liquid_chart",
    description: "Generate a liquid chart to visualize a single value as a percentage, such as, the current occupancy rate of a reservoir or the completion percentage of a project.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Liquid Chart",
        readOnlyHint: true,
    },
};
exports.liquid = {
    schema,
    tool,
};
