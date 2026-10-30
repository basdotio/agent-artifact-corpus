"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.logger = void 0;
/**
 * Unified logger for consistent logging across the application
 */
const prefix = "[MCP-Server-Chart]";
/**
 * Indicates if the logger is in stdio mode.
 * When true, logs are directed to stderr for info, warn, and success messages, using console.error.
 * When false, logs are directed to stdout.
 */
let IS_STDIO = true;
function setIsStdio(isStdio) {
    IS_STDIO = isStdio;
}
function getPrefix() {
    const timestamp = new Date().toISOString();
    return `${prefix} ${timestamp}`;
}
/**
 * Log info message
 */
function info(message, ...args) {
    const fn = IS_STDIO ? console.error : console.log;
    fn(`${getPrefix()} ℹ️  ${message}`, ...args);
}
/**
 * Log warning message
 */
function warn(message, ...args) {
    const fn = IS_STDIO ? console.warn : console.log;
    fn(`${getPrefix()} ⚠️  ${message}`, ...args);
}
/**
 * Log error message
 */
function error(message, error) {
    console.error(`${getPrefix()} ❌ ${message}`, error || "");
}
/**
 * Log success message
 */
function success(message, ...args) {
    const fn = IS_STDIO ? console.error : console.log;
    fn(`${getPrefix()} ✅ ${message}`, ...args);
}
/**
 * Logger object for backward compatibility
 */
exports.logger = {
    info,
    warn,
    error,
    success,
    setIsStdio,
};
