import { randomUUID } from 'node:crypto'
import {
  createServer,
  type IncomingMessage,
  type ServerResponse,
} from 'node:http'

import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js'

import { createMcpServer, type ToolMap } from './mcp.js'

export async function startHttpServer<TContext>(options: {
  name: string
  version: string
  tools: ToolMap<TContext>
  getContext: () => TContext | Promise<TContext>
  port: number
  path?: string
}) {
  const sessions = new Map<string, StreamableHTTPServerTransport>()
  const endpoint = options.path ?? '/mcp'

  const server = createServer(async (req, res) => {
    if (!req.url) {
      writeJson(res, 400, { error: 'Missing URL' })
      return
    }

    const url = new URL(req.url, 'http://localhost')

    if (req.method === 'GET' && url.pathname === '/health') {
      writeJson(res, 200, { ok: true })
      return
    }

    if (url.pathname !== endpoint) {
      writeJson(res, 404, { error: 'Not found' })
      return
    }

    const sessionId = req.headers['mcp-session-id']
    let transport =
      typeof sessionId === 'string' ? sessions.get(sessionId) : undefined

    if (!transport && req.method === 'POST') {
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (id) => {
          sessions.set(id, transport!)
        },
      })

      transport.onerror = () => {}
      transport.onmessage = async () => {}
      transport.onclose = () => {
        if (transport?.sessionId) {
          sessions.delete(transport.sessionId)
        }
      }

      const mcpServer = createMcpServer(options)
      await mcpServer.connect(transport as never)
    }

    if (!transport) {
      writeJson(res, 400, { error: 'Missing or unknown MCP session' })
      return
    }

    await transport.handleRequest(req, res, await readBody(req))
  })

  await new Promise<void>((resolve, reject) => {
    server.once('error', reject)
    server.listen(options.port, () => resolve())
  })

  return {
    server,
    endpoint,
    close: () =>
      new Promise<void>((resolve, reject) => {
        server.close((error) => {
          if (error) {
            reject(error)
            return
          }

          resolve()
        })
      }),
  }
}

async function readBody(req: IncomingMessage) {
  const chunks: Buffer[] = []

  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk))
  }

  if (chunks.length === 0) {
    return undefined
  }

  return JSON.parse(Buffer.concat(chunks).toString('utf8')) as unknown
}

function writeJson(res: ServerResponse, statusCode: number, body: unknown) {
  res.statusCode = statusCode
  res.setHeader('content-type', 'application/json')
  res.end(JSON.stringify(body))
}
