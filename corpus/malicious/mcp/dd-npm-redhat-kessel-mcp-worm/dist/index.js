#!/usr/bin/env node
"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = void 0;
const kessel_mcp_js_1 = require("./lib/kessel-mcp.js");
Object.defineProperty(exports, "run", { enumerable: true, get: function () { return kessel_mcp_js_1.run; } });
// CLI entry point
if (require.main === module) {
    (0, kessel_mcp_js_1.run)();
}
