#!/usr/bin/env node

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'

function main() {
  const server = new McpServer(
    {
      name: 'v-rapper-mcp',
      version: '0.0.1',
    },
    {
      capabilities: {
        tools: {},
      },
    }
  )

  process.on('SIGINT', async () => {
    await server.close()
    process.exit(0)
  })

  server.tool(
    'v-rapper',
    `Get Evan You's v-rapper video URL
Applicable scenarios:
1. User asks about v-rapper
2. User asks about VueConf 2025 Evan You rap video
`,
    {},
    async () => {
      return {
        content: [
          {
            type: 'text',
            text: 'https://www.bilibili.com/video/BV1U9MXzvEHR/?vd_source=d36c0f862962bd8f8a7256fb2ddb5bbf',
          },
        ],
      }
    }
  )

  const transport = new StdioServerTransport()
  server.connect(transport)
}

main()
