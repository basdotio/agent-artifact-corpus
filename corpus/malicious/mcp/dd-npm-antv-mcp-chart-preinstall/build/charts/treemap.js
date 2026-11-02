"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.treemap = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Define recursive schema for hierarchical data.
// The recursive schema is not supported by gemini, and other clients, so we use a non-recursive schema which can represent a tree structure with a fixed depth.
// Ref: https://github.com/antvis/mcp-server-chart/issues/155
// Ref: https://github.com/antvis/mcp-server-chart/issues/132
const TreeNodeSchema = zod_1.z.object({
    name: zod_1.z.string(),
    value: zod_1.z.number(),
    children: zod_1.z
        .array(zod_1.z.object({
        name: zod_1.z.string(),
        value: zod_1.z.number(),
        children: zod_1.z
            .array(zod_1.z.object({
            name: zod_1.z.string(),
            value: zod_1.z.number(),
        }))
            .optional(),
    }))
        .optional(),
});
// Treemap chart input schema
const schema = {
    data: zod_1.z
        .array(TreeNodeSchema)
        .describe("Data for treemap chart which is a hierarchical structure, such as, [{ name: 'Design', value: 70, children: [{ name: 'Tech', value: 20 }] }], and the maximum depth is 3.")
        .nonempty({ message: "Treemap chart data cannot be empty." }),
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
// Treemap chart tool descriptor
const tool = {
    name: "generate_treemap_chart",
    description: "Generate a treemap chart to display hierarchical data and can intuitively show comparisons between items at the same level, such as, show disk space usage with treemap.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Treemap Chart",
        readOnlyHint: true,
    },
};
exports.treemap = {
    schema,
    tool,
};
