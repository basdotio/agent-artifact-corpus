"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.pinMap = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const schema = {
    title: base_1.MapTitleSchema,
    data: base_1.POIsSchema,
    markerPopup: zod_1.z
        .object({
        type: zod_1.z.string().default("image").describe('Must be "image".'),
        width: zod_1.z.number().default(40).describe("Width of the photo."),
        height: zod_1.z.number().default(40).describe("Height of the photo."),
        borderRadius: zod_1.z
            .number()
            .default(8)
            .describe("Border radius of the photo."),
    })
        .optional()
        .describe("Marker type, one is simple mode, which is just an icon and does not require `markerPopup` configuration; the other is image mode, which displays location photos and requires `markerPopup` configuration. Among them, `width`/`height`/`borderRadius` can be combined to realize rectangular photos and square photos. In addition, when `borderRadius` is half of the width and height, it can also be a circular photo."),
    width: base_1.MapWidthSchema,
    height: base_1.MapHeightSchema,
};
// https://modelcontextprotocol.io/specification/2025-03-26/server/tools#listing-tools
const tool = {
    name: "generate_pin_map",
    description: "Generate a point map to display the location and distribution of point data on the map, such as the location distribution of attractions, hospitals, supermarkets, etc.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Pin Map",
        readOnlyHint: true,
    },
};
exports.pinMap = {
    schema,
    tool,
};
