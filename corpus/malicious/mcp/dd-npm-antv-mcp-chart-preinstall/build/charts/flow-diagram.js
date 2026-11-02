"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.flowDiagram = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const validator_1 = require("../utils/validator.js");
const base_1 = require("./base.js");
// Flow diagram input schema
const schema = {
    data: zod_1.z
        .object({
        nodes: zod_1.z
            .array(base_1.NodeSchema)
            .nonempty({ message: "At least one node is required." }),
        edges: zod_1.z.array(base_1.EdgeSchema),
    })
        .describe("Data for flow diagram chart, such as, { nodes: [{ name: 'node1' }, { name: 'node2' }], edges: [{ source: 'node1', target: 'node2', name: 'edge1' }] }.")
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
// Flow diagram tool descriptor
const tool = {
    name: "generate_flow_diagram",
    description: "Generate a flow diagram chart to show the steps and decision points of a process or system, such as, scenarios requiring linear process presentation.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Flow Diagram",
        readOnlyHint: true,
    },
};
exports.flowDiagram = {
    schema,
    tool,
};
