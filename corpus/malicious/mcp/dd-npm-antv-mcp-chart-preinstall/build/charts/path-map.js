"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.pathMap = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const schema = {
    title: base_1.MapTitleSchema,
    data: zod_1.z
        .array(zod_1.z.object({ data: base_1.POIsSchema }).describe("The route and places along it."))
        .nonempty("At least one route is required.")
        .describe('Routes, each group represents all POIs along a route. For example, [{ "data": ["西安钟楼", "西安大唐不夜城", "西安大雁塔"] }, { "data": ["西安曲江池公园", "西安回民街"] }]'),
    width: base_1.MapWidthSchema,
    height: base_1.MapHeightSchema,
};
// https://modelcontextprotocol.io/specification/2025-03-26/server/tools#listing-tools
const tool = {
    name: "generate_path_map",
    description: "Generate a route map to display the user's planned route, such as travel guide routes.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Path Map",
        readOnlyHint: true,
    },
};
exports.pathMap = {
    schema,
    tool,
};
