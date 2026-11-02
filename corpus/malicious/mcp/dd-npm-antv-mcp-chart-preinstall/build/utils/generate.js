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
exports.generateChartUrl = generateChartUrl;
exports.generateMap = generateMap;
const node_http_1 = __importDefault(require("node:http"));
const node_https_1 = __importDefault(require("node:https"));
const axios_1 = __importDefault(require("axios"));
const env_1 = require("./env.js");
/**
 * Persistent axios instance with HTTP keep-alive to reuse TCP connections
 * across requests, reducing overhead under high concurrency.
 */
const httpClient = axios_1.default.create({
    httpAgent: new node_http_1.default.Agent({ keepAlive: true }),
    httpsAgent: new node_https_1.default.Agent({ keepAlive: true }),
    headers: {
        "Content-Type": "application/json",
    },
});
/**
 * Generate a chart URL using the provided configuration.
 * @param type The type of chart to generate
 * @param options Chart options
 * @returns {Promise<string>} The generated chart URL.
 * @throws {Error} If the chart generation fails.
 */
function generateChartUrl(type, 
// biome-ignore lint/suspicious/noExplicitAny: <explanation>
options) {
    return __awaiter(this, void 0, void 0, function* () {
        const url = (0, env_1.getVisRequestServer)();
        const response = yield httpClient.post(url, Object.assign(Object.assign({ type }, options), { source: "mcp-server-chart" }));
        const { success, errorMessage, resultObj } = response.data;
        if (!success) {
            throw new Error(errorMessage);
        }
        return resultObj;
    });
}
/**
 * Generate a map
 * @param tool - The tool name
 * @param input - The input
 * @returns
 */
function generateMap(tool, input) {
    return __awaiter(this, void 0, void 0, function* () {
        const url = (0, env_1.getVisRequestServer)();
        const response = yield httpClient.post(url, {
            serviceId: (0, env_1.getServiceIdentifier)(),
            tool,
            input,
            source: "mcp-server-chart",
        });
        const { success, errorMessage, resultObj } = response.data;
        if (!success) {
            throw new Error(errorMessage);
        }
        return resultObj;
    });
}
