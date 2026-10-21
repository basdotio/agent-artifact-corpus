// Preload shim: route the embedded reasoning MCP servers' console output to stderr.
//
// Both npm servers (`server-shannon-thinking`, `@mettamatt/code-reasoning`) print
// informational lines — banners, "Using config directory: ...", "PromptManager
// initialized ..." — through `console.log` / `console.info`, i.e. on **stdout**.
// stdout is the stream the MCP stdio protocol owns, so every such line makes the
// Python client log an ERROR ("Failed to parse JSONRPC message from server") and
// drop the line. The protocol itself is unaffected: the official SDK writes frames
// with `process.stdout.write`, never through `console`.
//
// Preloaded via `NODE_OPTIONS=--require <this file>` (see
// src/reasoning/client.py::_subprocess_env); when REASONING_QUIET_STDERR is set the
// child's stderr is already routed to os.devnull, so this only moves noise out of
// the protocol stream.

"use strict";

const util = require("node:util");

const toStderr = (...args) => {
  process.stderr.write(util.format(...args) + "\n");
};

for (const method of ["log", "info", "debug", "warn", "error", "trace"]) {
  console[method] = toStderr;
}
