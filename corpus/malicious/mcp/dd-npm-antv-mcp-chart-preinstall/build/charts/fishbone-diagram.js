"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.fishboneDiagram = exports.FishboneNodeSchema = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const validator_1 = require("../utils/validator.js");
const base_1 = require("./base.js");
// Fishbone node schema
// The recursive schema is not supported by gemini, and other clients, so we use a non-recursive schema which can represent a tree structure with a fixed depth.
// Ref: https://github.com/antvis/mcp-server-chart/issues/155
// Ref: https://github.com/antvis/mcp-server-chart/issues/132
exports.FishboneNodeSchema = zod_1.z.object({
    name: zod_1.z.string(),
    children: zod_1.z
        .array(zod_1.z.object({
        name: zod_1.z.string(),
        children: zod_1.z
            .array(zod_1.z.object({
            name: zod_1.z.string(),
            children: zod_1.z
                .array(zod_1.z.object({
                name: zod_1.z.string(),
            }))
                .optional(),
        }))
            .optional(),
    }))
        .optional(),
});
// Fishbone diagram input schema
const schema = {
    data: exports.FishboneNodeSchema.describe("Data for fishbone diagram chart which is a hierarchical structure, such as, { name: 'main topic', children: [{ name: 'topic 1', children: [{ name: 'subtopic 1-1' }] }] }, and the maximum depth is 3.").refine(validator_1.validatedTreeDataSchema, {
        message: "Invalid parameters: node name is not unique.",
        path: ["data"],
    }),
    style: zod_1.z
        .object({
        texture: base_1.TextureSchema,
    })
        .optional()
        .describe("Style configuration for the chart with a JSON object, optional."),
    theme: base_1.ThemeSchema,
    width: base_1.WidthSchema,
    height: base_1.HeightSchema,
};
// Fishbone diagram tool descriptor
const tool = {
    name: "generate_fishbone_diagram",
    description: "Generate a fishbone diagram chart to uses a fish skeleton, like structure to display the causes or effects of a core problem, with the problem as the fish head and the causes/effects as the fish bones. It suits problems that can be split into multiple related factors.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Fishbone Diagram",
        readOnlyHint: true,
    },
};
exports.fishboneDiagram = {
    schema,
    tool,
};
