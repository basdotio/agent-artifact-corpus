"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __rest = (this && this.__rest) || function (s, e) {
    var t = {};
    for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
        t[p] = s[p];
    if (s != null && typeof Object.getOwnPropertySymbols === "function")
        for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
            if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                t[p[i]] = s[p[i]];
        }
    return t;
};
var _a;
Object.defineProperty(exports, "__esModule", { value: true });
exports.callTool = callTool;
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const zod_1 = require("zod");
const Charts = __importStar(require("../charts/index.js"));
const generate_1 = require("./generate.js");
const logger_1 = require("./logger.js");
const validator_1 = require("./validator.js");
// Chart type mapping
const CHART_TYPE_MAP = {
    generate_area_chart: "area",
    generate_bar_chart: "bar",
    generate_boxplot_chart: "boxplot",
    generate_column_chart: "column",
    generate_district_map: "district-map",
    generate_dual_axes_chart: "dual-axes",
    generate_fishbone_diagram: "fishbone-diagram",
    generate_flow_diagram: "flow-diagram",
    generate_funnel_chart: "funnel",
    generate_histogram_chart: "histogram",
    generate_line_chart: "line",
    generate_liquid_chart: "liquid",
    generate_mind_map: "mind-map",
    generate_network_graph: "network-graph",
    generate_organization_chart: "organization-chart",
    generate_path_map: "path-map",
    generate_pie_chart: "pie",
    generate_pin_map: "pin-map",
    generate_radar_chart: "radar",
    generate_sankey_chart: "sankey",
    generate_scatter_chart: "scatter",
    generate_treemap_chart: "treemap",
    generate_venn_chart: "venn",
    generate_violin_chart: "violin",
    generate_waterfall_chart: "waterfall",
    generate_word_cloud_chart: "word-cloud",
    generate_spreadsheet: "spreadsheet",
};
// Pre-compile Zod schemas at module load time to avoid recompiling on every request.
// biome-ignore lint/suspicious/noExplicitAny: schema types vary per chart
const COMPILED_SCHEMA_CACHE = new Map();
for (const chartType of Object.values(CHART_TYPE_MAP)) {
    const schema = (_a = Charts[chartType]) === null || _a === void 0 ? void 0 : _a.schema;
    if (schema) {
        COMPILED_SCHEMA_CACHE.set(chartType, zod_1.z.object(schema));
    }
}
/**
 * Call a tool to generate a chart based on the provided name and arguments.
 * @param tool The name of the tool to call, e.g., "generate_area_chart".
 * @param args The arguments for the tool, which should match the expected schema for the chart type.
 * @returns
 */
function callTool(tool_1) {
    return __awaiter(this, arguments, void 0, function* (tool, args = {}) {
        logger_1.logger.info(`Calling tool: ${tool}`);
        const chartType = CHART_TYPE_MAP[tool];
        if (!chartType) {
            logger_1.logger.error(`Unknown tool: ${tool}`);
            throw new types_js_1.McpError(types_js_1.ErrorCode.MethodNotFound, `Unknown tool: ${tool}.`);
        }
        try {
            // Validate input using Zod before sending to API.
            // Use pre-compiled schema from cache to avoid recompiling on every call.
            const compiledSchema = COMPILED_SCHEMA_CACHE.get(chartType);
            if (compiledSchema) {
                // Use safeParse instead of parse and try-catch.
                const result = compiledSchema.safeParse(args);
                if (!result.success) {
                    logger_1.logger.error(`Invalid parameters: ${result.error.message}`);
                    throw new types_js_1.McpError(types_js_1.ErrorCode.InvalidParams, `Invalid parameters: ${result.error.message}`);
                }
            }
            const isMapChartTool = [
                "generate_district_map",
                "generate_path_map",
                "generate_pin_map",
            ].includes(tool);
            if (isMapChartTool) {
                // For map charts, we use the generateMap function, and return the mcp result.
                const _a = yield (0, generate_1.generateMap)(tool, args), { metadata } = _a, result = __rest(_a, ["metadata"]);
                return result;
            }
            const url = yield (0, generate_1.generateChartUrl)(chartType, args);
            logger_1.logger.info(`Generated chart URL: ${url}`);
            return {
                content: [
                    {
                        type: "text",
                        text: url,
                    },
                ],
                _meta: {
                    description: "The content returned by MCP is the remote image URL of the visualization chart, which can be rendered using Markdown or HTML image tags. The _meta.spec content corresponds to the chart's configuration and spec, which can be rendered using AntV GPT-Vis chart components.",
                    spec: Object.assign({ type: chartType }, args),
                },
            };
            // biome-ignore lint/suspicious/noExplicitAny: <explanation>
        }
        catch (error) {
            logger_1.logger.error(`Failed to generate chart: ${error.message || "Unknown error"}.`);
            if (error instanceof types_js_1.McpError)
                throw error;
            if (error instanceof validator_1.ValidateError)
                throw new types_js_1.McpError(types_js_1.ErrorCode.InvalidParams, error.message);
            throw new types_js_1.McpError(types_js_1.ErrorCode.InternalError, `Failed to generate chart: ${(error === null || error === void 0 ? void 0 : error.message) || "Unknown error."}`);
        }
    });
}
