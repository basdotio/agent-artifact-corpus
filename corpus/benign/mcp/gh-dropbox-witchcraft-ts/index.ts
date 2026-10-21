import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { search }  from "./warp.cjs"

const server = new McpServer({
  name: "demo-server",
  version: "1.0.0"
});

async function doSearch(q: string): Promise<string> {
    const matches = [];
    const results = await search(q, 0.75, 10, "");
    console.log("warp results", results);
    for (const result of results) {
      let [_score, _head, body] = result;
      matches.push(body);
    }
    return Promise.resolve(matches.join("\n\n"));
}

server.registerTool("search",
  {
    title: "natural language search tool",
    description: "search for a text",
    inputSchema: { q: z.string() }
  },
  async ({ q }) => ({
    content: [{ type: "text", text: String( await doSearch(q) ) }]
  })
);

const transport = new StdioServerTransport();
await server.connect(transport);
