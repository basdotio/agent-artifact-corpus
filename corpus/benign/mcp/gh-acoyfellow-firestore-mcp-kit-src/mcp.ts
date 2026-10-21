import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolResult,
} from '@modelcontextprotocol/sdk/types.js'
import { z } from 'zod'

import { FirestoreMcpError } from './errors.js'
import { executeTool, type ToolDefinition } from './tools.js'

export type ToolMap<TContext> = Record<
  string,
  ToolDefinition<TContext, z.ZodType, z.ZodType>
>

export function createMcpServer<TContext>(options: {
  name: string
  version: string
  tools: ToolMap<TContext>
  getContext: () => TContext | Promise<TContext>
}) {
  const server = new Server(
    {
      name: options.name,
      version: options.version,
    },
    {
      capabilities: {
        tools: {},
      },
    }
  )

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: Object.values(options.tools).map((tool) => ({
        name: tool.name,
        description: tool.description,
        inputSchema: z.toJSONSchema(tool.inputSchema),
      })),
    }
  })

  server.setRequestHandler(
    CallToolRequestSchema,
    async (request): Promise<CallToolResult> => {
      const tool =
        options.tools[request.params.name] ??
        Object.values(options.tools).find(
          (candidate) => candidate.name === request.params.name
        )

      if (!tool) {
        return {
          isError: true,
          content: [
            {
              type: 'text',
              text: `Unknown tool: ${request.params.name}`,
            },
          ],
        }
      }

      try {
        const context = await options.getContext()
        const result = await executeTool(tool, {
          context,
          input: request.params.arguments ?? {},
        })

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(result, null, 2),
            },
          ],
          structuredContent: result as Record<string, unknown>,
        }
      } catch (error) {
        const normalized = normalizeMcpError(error)

        return {
          isError: true,
          content: [
            {
              type: 'text',
              text: normalized.message,
            },
          ],
          structuredContent: {
            code: normalized.code,
            statusCode: normalized.statusCode,
            details: normalized.details,
          } as Record<string, unknown>,
        }
      }
    }
  )

  return server
}

function normalizeMcpError(error: unknown) {
  if (error instanceof FirestoreMcpError) {
    return error
  }

  if (error instanceof Error) {
    return new FirestoreMcpError(error.message)
  }

  return new FirestoreMcpError('Unknown error', { details: error })
}
