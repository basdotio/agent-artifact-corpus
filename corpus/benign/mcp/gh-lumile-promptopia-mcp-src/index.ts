#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js'
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema
} from '@modelcontextprotocol/sdk/types.js'

import { SERVER_CONFIG } from './config/index.js'
import { ToolsHandler } from './handlers/tools.handler.js'
import { PromptsHandler } from './handlers/prompts.handler.js'
import { PromptsService } from './services/prompts.service.js'

class PromptopiaServer {
  private readonly server: Server
  private readonly toolsHandler: ToolsHandler
  private readonly promptsService: PromptsService
  private promptsHandler: PromptsHandler | null = null
  private transport: StdioServerTransport | null = null

  constructor () {
    // Initialize the MCP server with the base configuration
    this.server = new Server(
      {
        name: SERVER_CONFIG.name,
        version: SERVER_CONFIG.version
      },
      {
        capabilities: SERVER_CONFIG.capabilities
      }
    )

    // Initialize the tools handler
    this.toolsHandler = new ToolsHandler()

    // Initialize the prompts service
    this.promptsService = new PromptsService()

    // Initialize the prompts handler
    this.promptsHandler = new PromptsHandler(this.server, this.promptsService)

    // Setup handlers and error handling
    this.setupHandlers()
    this.setupErrorHandling()

    // Setup file watcher for prompts
    this.setupPromptsWatcher()
  }

  private setupHandlers (): void {
    // Setup handlers to list tools
    this.server.setRequestHandler(
      ListToolsRequestSchema,
      async () => this.toolsHandler.listTools()
    )

    // Setup handlers to call tools
    this.server.setRequestHandler(
      CallToolRequestSchema,
      async (request) => await this.toolsHandler.callTool(request.params.name, request.params.arguments)
    )

    // Setup handlers for prompts
    if (this.promptsHandler) {
      // List all prompts
      this.server.setRequestHandler(
        ListPromptsRequestSchema,
        async () => {
          const result = await this.promptsHandler!.listPrompts()
          return { ...result, _meta: {} }
        }
      )

      // Get a specific prompt
      this.server.setRequestHandler(
        GetPromptRequestSchema,
        async (request) => {
          const result = await this.promptsHandler!.getPrompt(
            request.params.name,
            request.params.arguments
          )
          return { ...result, _meta: {} }
        }
      )
    }
  }

  private async cleanup(): Promise<void> {
    try {
      if (this.promptsHandler) {
        await this.promptsHandler.dispose()
      }
      if (this.transport) {
        await this.transport.close()
      }
      await this.server.close()
    } catch (error) {
      console.error('Error during cleanup:', error)
    }
  }

  private setupErrorHandling (): void {
    // Handle server errors
    this.server.onerror = (error: Error) => {
      console.error(`[${SERVER_CONFIG.name} MCP Error]`, error)
    }

    // Handle interrupt signal (Ctrl+C)
    process.on('SIGINT', async () => {
      await this.cleanup()
      process.exit(0)
    })

    // Handle uncaught exceptions
    process.on('uncaughtException', (error: Error) => {
      console.error('[Uncaught Exception]', error)
      process.exit(1)
    })

    // Handle unhandled promise rejections
    process.on('unhandledRejection', async (reason: any) => {
      console.error('[Unhandled Rejection]', reason)
      await this.cleanup()
      process.exit(1)
    })
  }

  private async setupPromptsWatcher(): Promise<void> {
    if (this.promptsHandler) {
      try {
        await this.promptsHandler.setupFileWatcher()
      } catch (error) {
        console.error('Failed to set up prompts file watcher:', error)
      }
    }
  }

  async run (): Promise<void> {
    try {
      // Create and initialize the stdio transport
      this.transport = new StdioServerTransport()
      await this.server.connect(this.transport)

      console.error(`${SERVER_CONFIG.name} MCP server running (v${SERVER_CONFIG.version})`)
    } catch (error) {
      console.error('Failed to start server:', error)
      process.exit(1)
    }
  }
}

// Start the server
const server = new PromptopiaServer()
server.run().catch((error) => {
  console.error('Fatal error:', error)
  process.exit(1)
})
