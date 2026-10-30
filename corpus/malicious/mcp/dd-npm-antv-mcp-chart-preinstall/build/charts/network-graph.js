"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.networkGraph = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const validator_1 = require("../utils/validator.js");
const base_1 = require("./base.js");
// Network graph input schema
const schema = {
    data: zod_1.z
        .object({
        nodes: zod_1.z
            .array(base_1.NodeSchema)
            .nonempty({ message: "At least one node is required." }),
        edges: zod_1.z.array(base_1.EdgeSchema),
    })
        .describe("Data for network graph chart, such as, { nodes: [{ name: 'node1' }, { name: 'node2' }], edges: [{ source: 'node1', target: 'node2', name: 'edge1' }] }")
        .refine(validator_1.validatedNodeEdgeDataSchema, {
        message: "Invalid parameters",
        path: ["data", "edges"],
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
// Network graph tool descriptor
const tool = {
    name: "generate_network_graph",
    description: "Generate a network graph chart to show relationships (edges) between entities (nodes), such as, relationships between people in social networks.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Network Graph",
        readOnlyHint: true,
    },
};
exports.networkGraph = {
    schema,
    tool,
};
