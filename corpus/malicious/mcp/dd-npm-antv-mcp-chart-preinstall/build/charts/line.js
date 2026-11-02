"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.line = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Line chart data schema
const data = zod_1.z.object({
    time: zod_1.z.string(),
    value: zod_1.z.number(),
    group: zod_1.z.string().optional(),
});
// Line chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for line chart, it should be an array of objects, each object contains a `time` field and a `value` field, such as, [{ time: '2015', value: 23 }, { time: '2016', value: 32 }], when the data is grouped by time, the `group` field should be used to specify the group, such as, [{ time: '2015', value: 23, group: 'A' }, { time: '2015', value: 32, group: 'B' }].")
        .nonempty({ message: "Line chart data cannot be empty." }),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        palette: base_1.PaletteSchema,
        texture: base_1.TextureSchema,
        startAtZero: base_1.StartAtZeroSchema,
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
    axisXTitle: base_1.AxisXTitleSchema,
    axisYTitle: base_1.AxisYTitleSchema,
};
// Line chart tool descriptor
const tool = {
    name: "generate_line_chart",
    description: "Generate a line chart to show trends over time, such as, the ratio of Apple computer sales to Apple's profits changed from 2000 to 2016.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Line Chart",
        readOnlyHint: true,
    },
};
exports.line = {
    schema,
    tool,
};
