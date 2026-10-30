"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.POIsSchema = exports.MapHeightSchema = exports.MapWidthSchema = exports.MapTitleSchema = exports.EdgeSchema = exports.NodeSchema = exports.AxisYTitleSchema = exports.AxisXTitleSchema = exports.TitleSchema = exports.HeightSchema = exports.WidthSchema = exports.StartAtZeroSchema = exports.TextureSchema = exports.PaletteSchema = exports.BackgroundColorSchema = exports.ThemeSchema = void 0;
const zod_1 = require("zod");
// Define Zod schemas for base configuration properties
exports.ThemeSchema = zod_1.z
    .enum(["default", "academy", "dark"])
    .optional()
    .default("default")
    .describe("Set the theme for the chart, optional, default is 'default'.");
exports.BackgroundColorSchema = zod_1.z
    .string()
    .optional()
    .describe("Background color of the chart, such as, '#fff'.");
exports.PaletteSchema = zod_1.z
    .array(zod_1.z.string())
    .optional()
    .describe("Color palette for the chart, it is a collection of colors.");
exports.TextureSchema = zod_1.z
    .enum(["default", "rough"])
    .optional()
    .default("default")
    .describe("Set the texture for the chart, optional, default is 'default'. 'rough' refers to hand-drawn style.");
exports.StartAtZeroSchema = zod_1.z
    .boolean()
    .optional()
    .default(false)
    .describe("Whether to start the axis at zero, optional, default is false.");
exports.WidthSchema = zod_1.z
    .number()
    .optional()
    .default(600)
    .describe("Set the width of chart, default is 600.");
exports.HeightSchema = zod_1.z
    .number()
    .optional()
    .default(400)
    .describe("Set the height of chart, default is 400.");
exports.TitleSchema = zod_1.z
    .string()
    .optional()
    .default("")
    .describe("Set the title of chart.");
exports.AxisXTitleSchema = zod_1.z
    .string()
    .optional()
    .default("")
    .describe("Set the x-axis title of chart.");
exports.AxisYTitleSchema = zod_1.z
    .string()
    .optional()
    .default("")
    .describe("Set the y-axis title of chart.");
exports.NodeSchema = zod_1.z.object({
    name: zod_1.z.string(),
});
exports.EdgeSchema = zod_1.z.object({
    source: zod_1.z.string(),
    target: zod_1.z.string(),
    name: zod_1.z.string().optional().default(""),
});
// --- The following are only available for Map charts ---
exports.MapTitleSchema = zod_1.z
    .string()
    .describe("The map title should not exceed 16 characters. The content should be consistent with the information the map wants to convey and should be accurate, rich, creative, and attractive.");
exports.MapWidthSchema = zod_1.z
    .number()
    .optional()
    .default(1600)
    .describe("Set the width of map, default is 1600.");
exports.MapHeightSchema = zod_1.z
    .number()
    .optional()
    .default(1000)
    .describe("Set the height of map, default is 1000.");
exports.POIsSchema = zod_1.z
    .array(zod_1.z.string())
    .nonempty("At least one POI name is required.")
    .describe('A list of keywords for the names of points of interest (POIs) in Chinese. These POIs usually contain a group of places with similar locations, so the names should be more descriptive, must adding attributives to indicate that they are different places in the same area, such as "北京市" is better than "北京", "杭州西湖" is better than "西湖"; in addition, if you can determine that a location may appear in multiple areas, you can be more specific, such as "杭州西湖的苏堤春晓" is better than "苏堤春晓". The tool will use these keywords to search for specific POIs and query their detailed data, such as latitude and longitude, location photos, etc. For example, ["西安钟楼", "西安大唐不夜城", "西安大雁塔"].');
