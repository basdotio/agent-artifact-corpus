"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.startHTTPStreamableServer = void 0;
const streamableHttp_js_1 = require("@modelcontextprotocol/sdk/server/streamableHttp.js");
const cors_1 = __importDefault(require("cors"));
const express_1 = __importDefault(require("express"));
const logger_1 = require("../utils/logger.js");
const startHTTPStreamableServer = (createServer_1, ...args_1) => __awaiter(void 0, [createServer_1, ...args_1], void 0, function* (createServer, endpoint = "/mcp", port = 1122, host = "localhost") {
    const app = (0, express_1.default)();
    app.use(express_1.default.json());
    app.use((0, cors_1.default)({ origin: "*", exposedHeaders: ["Mcp-Session-Id"] }));
    app.post(endpoint, (req, res) => __awaiter(void 0, void 0, void 0, function* () {
        // In stateless mode, create a new transport for each request to prevent
        // request ID collisions. Different clients may use the same JSON-RPC request IDs,
        // which would cause responses to be routed to the wrong HTTP connections if
        // the transport state is shared.
        try {
            const server = createServer();
            const transport = new streamableHttp_js_1.StreamableHTTPServerTransport({
                sessionIdGenerator: undefined,
                enableJsonResponse: true,
            });
            res.on("close", () => {
                transport.close();
                logger_1.logger.info("HTTP Streamable Server response closed");
            });
            yield server.connect(transport);
            yield transport.handleRequest(req, res, req.body);
            logger_1.logger.info("HTTP Streamable Server response connected");
        }
        catch (e) {
            logger_1.logger.error("HTTP Streamable Server response error", e);
            if (!res.headersSent) {
                res.status(500).json({
                    jsonrpc: "2.0",
                    error: { code: -32603, message: "Internal server error" },
                    id: null,
                });
            }
        }
    }));
    app.listen(port, host, () => {
        logger_1.logger.success(`Streamable HTTP Server listening on http://${host}:${port}${endpoint}`);
    });
});
exports.startHTTPStreamableServer = startHTTPStreamableServer;
