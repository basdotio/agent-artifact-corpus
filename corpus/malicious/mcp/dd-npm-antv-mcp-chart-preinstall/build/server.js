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
Object.defineProperty(exports, "__esModule", { value: true });
exports.createServer = createServer;
exports.runStdioServer = runStdioServer;
exports.runSSEServer = runSSEServer;
exports.runHTTPStreamableServer = runHTTPStreamableServer;
const index_js_1 = require("@modelcontextprotocol/sdk/server/index.js");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const Charts = __importStar(require("./charts/index.js"));
const services_1 = require("./services/index.js");
const callTool_1 = require("./utils/callTool.js");
const env_1 = require("./utils/env.js");
const logger_1 = require("./utils/logger.js");
/**
 * Creates and configures an MCP server for chart generation.
 */
function createServer() {
    const server = new index_js_1.Server({
        name: "mcp-server-chart",
        version: "0.8.x",
    }, {
        capabilities: {
            tools: {},
        },
    });
    setupToolHandlers(server);
    server.onerror = (e) => {
        logger_1.logger.error("Server encountered an error, shutting down", e);
    };
    process.on("SIGINT", () => __awaiter(this, void 0, void 0, function* () {
        logger_1.logger.info("SIGINT received, shutting down server...");
        yield server.close();
        process.exit(0);
    }));
    return server;
}
/**
 * Gets enabled tools based on environment variables.
 * The result is cached since the tool list does not change at runtime.
 */
let enabledToolsCache = null;
function getEnabledTools() {
    if (enabledToolsCache)
        return enabledToolsCache;
    const disabledTools = (0, env_1.getDisabledTools)();
    const allCharts = Object.values(Charts);
    enabledToolsCache =
        disabledTools.length === 0
            ? allCharts
            : allCharts.filter((chart) => !disabledTools.includes(chart.tool.name));
    return enabledToolsCache;
}
/**
 * Sets up tool handlers for the MCP server.
 */
function setupToolHandlers(server) {
    logger_1.logger.info("setting up tool handlers...");
    server.setRequestHandler(types_js_1.ListToolsRequestSchema, () => __awaiter(this, void 0, void 0, function* () {
        return ({
            tools: getEnabledTools().map((chart) => chart.tool),
        });
    }));
    // biome-ignore lint/suspicious/noExplicitAny: <explanation>
    server.setRequestHandler(types_js_1.CallToolRequestSchema, (request) => __awaiter(this, void 0, void 0, function* () {
        logger_1.logger.info("calling tool", request.params.name, request.params.arguments);
        return yield (0, callTool_1.callTool)(request.params.name, request.params.arguments);
    }));
    logger_1.logger.info("tool handlers set up");
}
/**
 * Runs the server with stdio transport.
 */
function runStdioServer() {
    return __awaiter(this, void 0, void 0, function* () {
        const server = createServer();
        yield (0, services_1.startStdioMcpServer)(server);
    });
}
/**
 * Runs the server with SSE transport.
 */
function runSSEServer() {
    return __awaiter(this, arguments, void 0, function* (host = "localhost", port = 1122, endpoint = "/sse") {
        yield (0, services_1.startSSEMcpServer)(createServer, endpoint, port, host);
    });
}
/**
 * Runs the server with HTTP streamable transport.
 */
function runHTTPStreamableServer() {
    return __awaiter(this, arguments, void 0, function* (host = "localhost", port = 1122, endpoint = "/mcp") {
        yield (0, services_1.startHTTPStreamableServer)(createServer, endpoint, port, host);
    });
}
