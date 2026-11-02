"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.funnel = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const data = zod_1.z.object({
    category: zod_1.z.string(),
    value: zod_1.z.number(),
});
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for funnel chart, such as, [{ category: '浏览网站', value: 50000 }, { category: '放入购物车', value: 35000 }, { category: '生成订单', value: 25000 }, { category: '支付订单', value: 15000 }, { category: '完成交易', value: 8000 }].")
        .nonempty({ message: "Funnel chart data cannot be empty." }),
    style: zod_1.z
        .object({
        backgroundColor: base_1.BackgroundColorSchema,
        palette: base_1.PaletteSchema,
        texture: base_1.TextureSchema,
    })
        .optional()
        .describe("Style configuration for the chart with a JSON object, optional."),
    theme: base_1.ThemeSchema,
    width: base_1.WidthSchema,
    height: base_1.HeightSchema,
    title: base_1.TitleSchema,
};
const tool = {
    name: "generate_funnel_chart",
    description: "Generate a funnel chart to visualize the progressive reduction of data as it passes through stages, such as, the conversion rates of users from visiting a website to completing a purchase.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Funnel Chart",
        readOnlyHint: true,
    },
};
exports.funnel = {
    schema,
    tool,
};
