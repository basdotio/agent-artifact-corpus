"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.radar = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Radar chart data schema
const data = zod_1.z.object({
    name: zod_1.z.string(),
    value: zod_1.z.number(),
    group: zod_1.z.string().optional(),
});
// Radar chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for radar chart, it should be an array of objects, each object contains a `name` field and a `value` field, such as, [{ name: 'Design', value: 70 }], when the data is grouped by `group`, the `group` field is required, such as, [{ name: 'Design', value: 70, group: 'Huawei' }].")
        .nonempty({ message: "Radar chart data cannot be empty." }),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        palette: base_1.PaletteSchema,
        texture: base_1.TextureSchema,
        lineWidth: zod_1.z
            .number()
            .optional()
            .describe("Line width for the lines of chart, such as 4."),
    })
        .optional()
        .describe("Style configuration for the chart with a JSON object, optional."),
    theme: base_1.ThemeSchema,
    width: base_1.WidthSchema,
    height: base_1.HeightSchema,
    title: base_1.TitleSchema,
};
// Radar chart tool descriptor
const tool = {
    name: "generate_radar_chart",
    description: "Generate a radar chart to display multidimensional data (four dimensions or more), such as, evaluate Huawei and Apple phones in terms of five dimensions: ease of use, functionality, camera, benchmark scores, and battery life.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Radar Chart",
        readOnlyHint: true,
    },
};
exports.radar = {
    schema,
    tool,
};
