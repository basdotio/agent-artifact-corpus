"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.organizationChart = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// The recursive schema is not supported by gemini, and other clients, so we use a non-recursive schema which can represent a tree structure with a fixed depth.
// Ref: https://github.com/antvis/mcp-server-chart/issues/155
// Ref: https://github.com/antvis/mcp-server-chart/issues/132
const OrganizationChartNodeSchema = zod_1.z.object({
    name: zod_1.z.string(),
    description: zod_1.z.string().optional(),
    children: zod_1.z
        .array(zod_1.z.object({
        name: zod_1.z.string(),
        description: zod_1.z.string().optional(),
        children: zod_1.z
            .array(zod_1.z.object({
            name: zod_1.z.string(),
            description: zod_1.z.string().optional(),
            children: zod_1.z
                .array(zod_1.z.object({
                name: zod_1.z.string(),
                description: zod_1.z.string().optional(),
            }))
                .optional(),
        }))
            .optional(),
    }))
        .optional(),
});
const schema = {
    data: OrganizationChartNodeSchema.describe("Data for organization chart which is a hierarchical structure, such as, { name: 'CEO', description: 'Chief Executive Officer', children: [{ name: 'CTO', description: 'Chief Technology Officer', children: [{ name: 'Dev Manager', description: 'Development Manager' }] }] }, and the maximum depth is 3."),
    orient: zod_1.z
        .enum(["horizontal", "vertical"])
        .default("vertical")
        .describe("Orientation of the organization chart, either horizontal or vertical. Default is vertical, when the level of the chart is more than 3, it is recommended to use horizontal orientation."),
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
const tool = {
    name: "generate_organization_chart",
    description: "Generate an organization chart to visualize the hierarchical structure of an organization, such as, a diagram showing the relationship between a CEO and their direct reports.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Organization Chart",
        readOnlyHint: true,
    },
};
exports.organizationChart = {
    schema,
    tool,
};
