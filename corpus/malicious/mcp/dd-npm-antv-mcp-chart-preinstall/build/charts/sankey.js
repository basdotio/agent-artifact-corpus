"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.sankey = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
const data = zod_1.z.object({
    source: zod_1.z.string(),
    target: zod_1.z.string(),
    value: zod_1.z.number(),
});
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Date for sankey chart, such as, [{ source: 'Landing Page', target: 'Product Page', value: 50000 }, { source: 'Product Page', target: 'Add to Cart', value: 35000 }, { source: 'Add to Cart', target: 'Checkout', value: 25000 }, { source: 'Checkout', target: 'Payment', value: 15000 }, { source: 'Payment', target: 'Purchase Completed', value: 8000 }].")
        .nonempty({ message: "Sankey chart data cannot be empty." }),
    nodeAlign: zod_1.z
        .enum(["left", "right", "justify", "center"])
        .optional()
        .default("center")
        .describe("Alignment of nodes in the sankey chart, such as, 'left', 'right', 'justify', or 'center'."),
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
    name: "generate_sankey_chart",
    description: "Generate a sankey chart to visualize the flow of data between different stages or categories, such as, the user journey from landing on a page to completing a purchase.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Sankey Chart",
        readOnlyHint: true,
    },
};
exports.sankey = {
    schema,
    tool,
};
