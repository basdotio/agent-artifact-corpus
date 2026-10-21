import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'

import { createMcpServer, type ToolMap } from './mcp.js'

export async function startStdioServer<TContext>(options: {
  name: string
  version: string
  tools: ToolMap<TContext>
  getContext: () => TContext | Promise<TContext>
}) {
  const server = createMcpServer(options)
  const transport = new StdioServerTransport()

  await server.connect(transport)

  return { server, transport }
}
