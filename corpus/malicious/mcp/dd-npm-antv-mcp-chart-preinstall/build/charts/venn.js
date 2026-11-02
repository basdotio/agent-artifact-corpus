"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.venn = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const data = zod_1.z.object({
    label: zod_1.z
        .string()
        .optional()
        .describe("Label for the venn chart segment, such as 'A', 'B', or 'C'."),
    value: zod_1.z
        .number()
        .describe("Value for the venn chart segment, such as 10, 20, or 30."),
    sets: zod_1.z
        .array(zod_1.z.string())
        .describe("Array of set names that this segment belongs to, such as ['A', 'B'] for an intersection between sets A and B."),
});
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for venn chart, such as, [{ label: 'A', value: 10, sets: ['A'] }, { label: 'B', value: 20, sets: ['B'] }, { label: 'C', value: 30, sets: ['C'] }, { label: 'AB', value: 5, sets: ['A', 'B'] }].")
        .nonempty({ message: "Venn chart data cannot be empty." }),
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
const tool = {
    name: "generate_venn_chart",
    description: "Generate a Venn diagram to visualize the relationships between different sets, showing how they intersect and overlap, such as the commonalities and differences between various groups.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Venn Chart",
        readOnlyHint: true,
    },
};
exports.venn = {
    schema,
    tool,
};
