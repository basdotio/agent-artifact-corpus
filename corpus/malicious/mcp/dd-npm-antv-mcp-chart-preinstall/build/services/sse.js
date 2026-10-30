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
exports.startSSEMcpServer = void 0;
const sse_js_1 = require("@modelcontextprotocol/sdk/server/sse.js");
const express_1 = __importDefault(require("express"));
const logger_1 = require("../utils/logger.js");
const startSSEMcpServer = (createServer_1, ...args_1) => __awaiter(void 0, [createServer_1, ...args_1], void 0, function* (createServer, endpoint = "/sse", port = 1122, host = "localhost") {
    const app = (0, express_1.default)();
    app.use(express_1.default.json());
    const connections = {};
    app.get(endpoint, (req, res) => __awaiter(void 0, void 0, void 0, function* () {
        const server = createServer();
        const transport = new sse_js_1.SSEServerTransport("/messages", res);
        connections[transport.sessionId] = transport;
        transport.onclose = () => {
            delete connections[transport.sessionId];
            logger_1.logger.info(`SSE Server disconnected: sessionId=${transport.sessionId}`);
        };
        yield server.connect(transport);
        logger_1.logger.info(`SSE Server connected: sessionId=${transport.sessionId}`);
    }));
    app.post("/messages", (req, res) => __awaiter(void 0, void 0, void 0, function* () {
        const sessionId = req.query.sessionId;
        if (!sessionId) {
            logger_1.logger.warn("SSE Server sessionId parameter is missing");
            return res.status(400).send("Missing sessionId parameter");
        }
        const transport = connections[sessionId];
        if (!transport) {
            logger_1.logger.warn(`SSE Server session not found: sessionId=${sessionId}`);
            return res.status(404).send("Session not found");
        }
        try {
            logger_1.logger.info(`SSE Server handling message: sessionId=${sessionId}`);
            yield transport.handlePostMessage(req, res, req.body);
        }
        catch (e) {
            logger_1.logger.error("SSE Server error handling message", e);
            if (!res.headersSent)
                res.status(500).send("Error handling request");
        }
    }));
    app.listen(port, host, () => {
        logger_1.logger.success(`SSE Server listening on http://${host}:${port}${endpoint}`);
    });
});
exports.startSSEMcpServer = startSSEMcpServer;
