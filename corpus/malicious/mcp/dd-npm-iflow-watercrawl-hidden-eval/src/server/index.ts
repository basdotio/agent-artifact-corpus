import { FastMCP } from 'fastmcp';
import { tools } from '@tools/index';

export const setupServer = () => {
  const server = new FastMCP({
    name: 'WaterCrawl MCP Server',
    version: '1.0.0',
  });

  // Register tools
  for (const tool of tools) {
    server.addTool(tool);
  }

  return server;
};