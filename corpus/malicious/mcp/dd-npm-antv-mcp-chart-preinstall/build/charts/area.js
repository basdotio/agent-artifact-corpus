"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.area = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Area chart data schema
const data = zod_1.z.object({
    time: zod_1.z.string(),
    value: zod_1.z.number(),
    group: zod_1.z.string().optional(),
});
// Area chart input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for area chart, it should be an array of objects, each object contains a `time` field and a `value` field, such as, [{ time: '2015', value: 23 }, { time: '2016', value: 32 }], when stacking is needed for area, the data should contain a `group` field, such as, [{ time: '2015', value: 23, group: 'A' }, { time: '2015', value: 32, group: 'B' }].")
        .nonempty({ message: "Area chart data cannot be empty." }),
    stack: zod_1.z
        .boolean()
        .optional()
        .default(false)
        .describe("Whether stacking is enabled. When enabled, area charts require a 'group' field in the data."),
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
    axisXTitle: base_1.AxisXTitleSchema,
    axisYTitle: base_1.AxisYTitleSchema,
};
// Area chart tool descriptor
const tool = {
    name: "generate_area_chart",
    description: "Generate a area chart to show data trends under continuous independent variables and observe the overall data trend, such as, displacement = velocity (average or instantaneous) × time: s = v × t. If the x-axis is time (t) and the y-axis is velocity (v) at each moment, an area chart allows you to observe the trend of velocity over time and infer the distance traveled by the area's size.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Area Chart",
        readOnlyHint: true,
    },
};
exports.area = {
    schema,
    tool,
};
