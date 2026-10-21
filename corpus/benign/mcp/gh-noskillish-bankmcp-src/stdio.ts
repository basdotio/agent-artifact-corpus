// Local entry point for Claude Desktop, Claude Code, Cursor and other stdio
// MCP clients. No OAuth: whoever can run this process can already read the
// data directory. Nothing may write to stdout except the transport.
process.env.BANKMCP_LOCAL ??= "1";
const { StdioServerTransport } = await import("@modelcontextprotocol/sdk/server/stdio.js");
const { createServer } = await import("./mcp.ts");
const { isConfigured } = await import("./config.ts");
const { ensureLocalServer } = await import("./local.ts");

// The browser-facing side (setup page, bank redirect) runs on localhost over
// https and starts with the process, so the redirect URL is always reachable.
ensureLocalServer().catch((err) => console.error("[bank] could not start the local server:", err.message));
if (!isConfigured()) console.error("[bank] not configured yet: ask your assistant anything and it will point you to the setup page");

const transport = new StdioServerTransport();
// Exit with the client: when stdin closes, the localhost listener must not keep the process alive.
transport.onclose = () => process.exit(0);
process.stdin.on("end", () => process.exit(0));
await createServer().connect(transport);
