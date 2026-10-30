"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.wordCloud = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Word cloud data schema
const data = zod_1.z.object({
    text: zod_1.z.string(),
    value: zod_1.z.number(),
});
// Word cloud input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for word cloud chart, it should be an array of objects, each object contains a `text` field and a `value` field, such as, [{ value: 4.272, text: '形成' }].")
        .nonempty({ message: "Word cloud chart data cannot be empty." }),
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
// Word cloud tool descriptor
const tool = {
    name: "generate_word_cloud_chart",
    description: "Generate a word cloud chart to show word frequency or weight through text size variation, such as, analyzing common words in social media, reviews, or feedback.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Word Cloud Chart",
        readOnlyHint: true,
    },
};
exports.wordCloud = {
    schema,
    tool,
};
