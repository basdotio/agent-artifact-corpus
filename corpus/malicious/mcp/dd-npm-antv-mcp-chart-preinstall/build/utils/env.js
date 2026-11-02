"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getVisRequestServer = getVisRequestServer;
exports.getServiceIdentifier = getServiceIdentifier;
exports.getDisabledTools = getDisabledTools;
const node_process_1 = __importDefault(require("node:process"));
/**
 * Get the VIS_REQUEST_SERVER from environment variables.
 */
function getVisRequestServer() {
    return (node_process_1.default.env.VIS_REQUEST_SERVER ||
        "https://antv-studio.alipay.com/api/gpt-vis");
}
/**
 * Get the `SERVICE_ID` from environment variables.
 */
function getServiceIdentifier() {
    return node_process_1.default.env.SERVICE_ID;
}
/**
 * Get the list of disabled tools from environment variables.
 */
function getDisabledTools() {
    const disabledTools = node_process_1.default.env.DISABLED_TOOLS;
    if (!disabledTools || disabledTools === "undefined") {
        return [];
    }
    return disabledTools.split(",");
}
