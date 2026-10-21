/**
 * @file index
 * @description Process entry point: assembles the runtime and dispatches the
 *   CLI (including MCP stdio serve mode).
 *
 * Responsibilities:
 * - Load .env and assemble the runtime (config + adapters + usable fallback chain)
 * - Bind MCP's list/call handlers to the tool layer
 * - Hand argv to the CLI dispatch; with no arguments, start the stdio server
 *   (MCP-client compatible)
 */

// Entry wiring layer. All substantive logic lives in config / providers /
// tools / orchestrator / cli; this file only connects them to the MCP SDK
// and the process.

import { pathToFileURL } from 'node:url';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema, ListToolsRequestSchema, type CallToolResult,
} from '@modelcontextprotocol/sdk/types.js';
import loadDotEnv from './dotenv.js';
import { defaultWarn } from './config.js';
import { createRuntime } from './runtime.js';
import { createGatewayTools } from './tools.js';
import { runCli, type CliRunDeps } from './cli/index.js';
import { SERVER_NAME, SERVER_VERSION } from './server-info.js';

// The .env warning channel is passed explicitly rather than left to the loader's
// default, so every diagnostic this program emits — a skipped .env name, a bad
// config value, a corrupt config file — leaves through one named outlet instead
// of whichever default each layer happened to carry.
loadDotEnv(process.cwd(), process.env, defaultWarn);
const runtime = createRuntime();
const tools = createGatewayTools({ config: runtime.config, chain: runtime.chain });

export const server = new Server(
  { name: SERVER_NAME, version: SERVER_VERSION },
  { capabilities: { tools: {} } },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: tools.list() }));

// ToolOutput is a structural subset of CallToolResult; the SDK handler's
// type is a wide union of result shapes, so this narrowing cast is safe.
// extra.signal fires when the client cancels the request or the connection
// drops; it is forwarded so the search stops instead of running on.
server.setRequestHandler(
  CallToolRequestSchema,
  (request, extra) => tools.call(
    request.params.name,
    (request.params.arguments ?? {}),
    extra.signal,
  ) as Promise<CallToolResult>,
);

/**
 * MCP stdio server: connecting the transport completes startup (driven by the
 * MCP client afterwards).
 */
export async function main(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `[${SERVER_NAME}] v${SERVER_VERSION} ready; strategy: ${runtime.config.strategy}; chain: ${
      runtime.chain.map((p) => p.name).join(' -> ') || '(none configured)'
    }`,
  );
}

/** CLI dependencies: real process streams + the stdio serve implementation. */
function cliDeps(): CliRunDeps {
  return {
    runtime,
    serve: main,
    input: process.stdin,
    output: process.stdout,
    error: process.stderr,
  };
}

/**
 * Parse argv and execute; non-zero exit codes become the process exit code
 * (for shell/CI branching).
 */
export async function start(): Promise<void> {
  try {
    const code = await runCli(process.argv.slice(2), cliDeps());
    if (code !== 0) process.exit(code);
  } catch (err) {
    console.error(`[${SERVER_NAME}] fatal:`, err);
    process.exit(1);
  }
}

// Auto-start only when executed directly as the bin entry; importing this
// module in tests does not trigger the stdio loop.
const isMain = process.argv[1] !== undefined
  && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) void start();
