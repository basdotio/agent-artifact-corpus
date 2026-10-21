import { McpServer} from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { sendAnalyticsPing } from "./analytics.js";

// Create an MCP server
const server = new McpServer({
  name: "demo-server",
  version: "1.0.0"
});

// Add an addition tool
server.registerTool("add",
  {
    title: "Addition Tool",
    description: "Add two numbers",
    inputSchema: { a: z.number(), b: z.number() }
  },
  async ({ a, b }) => {
    // Send analytics ping
    await sendAnalyticsPing("add_tool_used");
    return {
    content: [{ type: "text", text: String(a + b) }]
  }
});

server.registerTool("get_city_weather_forecast",
  {
    title: "Get City Weather Forcast",
    description: "Get the weather forecast for a given city",
    inputSchema: { city: z.string() }
  },
  async ({ city }) => {
    // Send analytics ping
    await sendAnalyticsPing("get_city_weather_forecast_tool_used");
    return {
    content: [{ type: "text", text: `Current weather in ${city}: 25°C, Sunny`}]
  }}
);

// Start receiving messages on stdin and sending messages on stdout
const transport = new StdioServerTransport();
await server.connect(transport);