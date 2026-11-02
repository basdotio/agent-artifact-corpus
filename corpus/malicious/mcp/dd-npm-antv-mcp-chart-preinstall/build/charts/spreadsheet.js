"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.spreadsheet = void 0;
const zod_1 = require("zod");
const utils_1 = require("../utils/index.js");
const base_1 = require("./base.js");
// Spreadsheet data schema - flexible record type
const data = zod_1.z.record(zod_1.z.string(), zod_1.z.union([zod_1.z.string(), zod_1.z.number(), zod_1.z.null()]));
// Spreadsheet theme schema
const SpreadsheetThemeSchema = zod_1.z
    .enum(["default", "dark"])
    .optional()
    .default("default")
    .describe("Set the theme for the spreadsheet, optional, default is 'default'.");
// Spreadsheet input schema
const schema = {
    data: zod_1.z
        .array(data)
        .describe("Data for spreadsheet, an array of objects where each object represents a row. Keys are column names and values can be string, number, or null. Such as, [{ name: 'John', age: 30 }, { name: 'Jane', age: 25 }].")
        .nonempty({ message: "Spreadsheet data cannot be empty." }),
    rows: zod_1.z
        .array(zod_1.z.string())
        .optional()
        .describe("Row header fields for pivot table. When 'rows' or 'values' is provided, the spreadsheet will be rendered as a pivot table."),
    columns: zod_1.z
        .array(zod_1.z.string())
        .optional()
        .describe("Column header fields, used to specify the order of columns. For regular tables, this determines column order; for pivot tables, this is used for column grouping."),
    values: zod_1.z
        .array(zod_1.z.string())
        .optional()
        .describe("Value fields for pivot table. When 'rows' or 'values' is provided, the spreadsheet will be rendered as a pivot table."),
    theme: SpreadsheetThemeSchema,
    width: base_1.WidthSchema,
    height: base_1.HeightSchema,
};
// Spreadsheet tool descriptor
const tool = {
    name: "generate_spreadsheet",
    description: "Generate a spreadsheet or pivot table for displaying tabular data. When 'rows' or 'values' fields are provided, it renders as a pivot table (cross-tabulation); otherwise, it renders as a regular table. Useful for displaying structured data, comparing values across categories, and creating data summaries.",
    inputSchema: (0, utils_1.zodToJsonSchema)(schema),
    annotations: {
        title: "Generate Spreadsheet",
        readOnlyHint: true,
    },
};
exports.spreadsheet = {
    schema,
    tool,
};
