#!/usr/bin/env node
import { runSetup } from "./setup.js";

const args = process.argv.slice(2);

if (args[0] === "setup" || (process.stdin.isTTY && args.length === 0)) {
  runSetup().catch(console.error);
} else {
  // If invoked via stdio pipe (IDE MCP integration), run the MCP server
  await import("../index.js");
}
