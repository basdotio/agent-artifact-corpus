"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.mindMap = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const validator_1 = require("../utils/validator.js");
const base_1 = require("./base.js");
const fishbone_diagram_1 = require("./fishbone-diagram.js");
// Mind map node schema
// The recursive schema is not supported by gemini, and other clients, so we use a non-recursive schema which can represent a tree structure with a fixed depth.
// Ref: https://github.com/antvis/mcp-server-chart/issues/155
// Ref: https://github.com/antvis/mcp-server-chart/issues/132
const MindMapNodeSchema = fishbone_diagram_1.FishboneNodeSchema;
// Mind map chart input schema
const schema = {
    data: MindMapNodeSchema.describe("Data for mind map chart which is a hierarchical structure, such as, { name: 'main topic', children: [{ name: 'topic 1', children: [{ name:'subtopic 1-1' }] }, and the maximum depth is 3.").refine(validator_1.validatedTreeDataSchema, {
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
// Mind map chart tool descriptor
const tool = {
    name: "generate_mind_map",
    description: "Generate a mind map chart to organizes and presents information in a hierarchical structure with branches radiating from a central topic, such as, a diagram showing the relationship between a main topic and its subtopics.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Mind Map",
        readOnlyHint: true,
    },
};
exports.mindMap = {
    schema,
    tool,
};
