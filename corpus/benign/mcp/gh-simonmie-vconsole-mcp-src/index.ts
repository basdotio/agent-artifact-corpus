#!/usr/bin/env node

import { serveStdio } from '@modelcontextprotocol/server/stdio';
import { VConsoleBridge } from './bridge.js';
import { createMCPServer } from './mcp.js';

function getArgument(name: string): string | undefined {
  const index = process.argv.indexOf(name);
  return index > -1 ? process.argv[index + 1] : undefined;
}

const host = getArgument('--host') || process.env.VCONSOLE_MCP_HOST || '0.0.0.0';
const port = Number(getArgument('--port') || process.env.VCONSOLE_MCP_PORT || 8765);
const token = getArgument('--token') || process.env.VCONSOLE_MCP_TOKEN || '';

if (!Number.isInteger(port) || port < 0 || port > 65535) {
  console.error(`Invalid WebSocket port: ${port}`);
  process.exit(1);
}

const bridge = new VConsoleBridge(host, port, token);
await bridge.waitUntilListening();
const stdio = serveStdio(() => createMCPServer(bridge));

console.error(`vConsole MCP WebSocket server listening on ws://${host}:${bridge.port}`);
if (!token) {
  console.error('Warning: no pairing token is configured; use only on a trusted development network.');
}

let shuttingDown = false;
async function shutdown() {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  await Promise.allSettled([stdio.close(), bridge.close()]);
}

process.once('SIGINT', () => void shutdown());
process.once('SIGTERM', () => void shutdown());
process.stdin.once('end', () => void shutdown());
