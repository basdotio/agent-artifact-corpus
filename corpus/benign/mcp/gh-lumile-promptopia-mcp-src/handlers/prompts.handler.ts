import { Server } from '@modelcontextprotocol/sdk/server/index.js'
import { PromptsService } from '../services/prompts.service.js'
import { Prompt, McpPrompt, McpGetPromptResult, isMultiMessagePrompt, isSingleContentPrompt } from '../types/index.js'
import path from 'path'
import { fileURLToPath } from 'url'
import { watch } from 'fs/promises'
import { handleServiceError } from '../utils/error-handler.js'
import { PROMPTS_CONFIG } from '../config/index.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export class PromptsHandler {
  private readonly promptsService: PromptsService
  private readonly server: Server
  private fileWatcher: AsyncIterable<unknown> | null = null
  private abortController: AbortController | null = null

  constructor(server: Server, promptsService: PromptsService) {
    this.server = server
    this.promptsService = promptsService
  }

  async listPrompts(): Promise<{ prompts: McpPrompt[] }> {
    try {
      const prompts = await this.promptsService.listPrompts()

      // Convert internal prompts to MCP prompt format
      const mcpPrompts = prompts.map(prompt => this.toMcpPrompt(prompt))

      return { prompts: mcpPrompts }
    } catch (error) {
      const mcpError = handleServiceError(error)
      throw mcpError
    }
  }

  async getPrompt(name: string, args?: Record<string, string>): Promise<McpGetPromptResult> {
    try {
      // For now, we'll use the first prompt that matches the name
      // In a real implementation, we might want to use IDs instead
      const prompts = await this.promptsService.listPrompts()
      const prompt = prompts.find(p => p.name === name)

      if (!prompt) {
        throw new Error(`Prompt not found: ${name}`)
      }

      // If arguments are provided, apply them to the prompt
      if (args) {
        const result = await this.promptsService.applyPrompt({
          id: prompt.id,
          variables: args
        })

        if (isMultiMessagePrompt(prompt) && result.messages) {
          // Return multi-message format
          return {
            messages: result.messages.map(message => ({
              role: message.role,
              content: {
                type: message.content.type,
                text: message.content.text || message.content.image
              }
            }))
          }
        } else {
          // Return single message format for single content prompts
          return {
            messages: [{
              role: 'user',
              content: {
                type: 'text',
                text: result.result
              }
            }]
          }
        }
      }

      // If no arguments, return the prompt content as is
      if (isMultiMessagePrompt(prompt)) {
        // Return multi-message format
        return {
          messages: prompt.messages.map(message => ({
            role: message.role,
            content: {
              type: message.content.type,
              text: message.content.text || message.content.image
            }
          }))
        }
      } else {
        // Return single content format
        return {
          messages: [{
            role: 'user',
            content: {
              type: 'text',
              text: prompt.content
            }
          }]
        }
      }
    } catch (error) {
      const mcpError = handleServiceError(error)
      throw mcpError
    }
  }

  async setupFileWatcher(): Promise<void> {
    if (this.abortController) {
      // Clean up existing watcher if any
      this.abortController.abort()
    }

    this.abortController = new AbortController()
    const { signal } = this.abortController

    try {
      const promptsDir = path.join(process.cwd(), PROMPTS_CONFIG.promptsDir)

      // Watch for changes in the prompts directory
      this.fileWatcher = watch(promptsDir, {
        recursive: true,  // Watch subdirectories as well
        signal
      })

      console.error(`Watching for changes in prompts directory: ${promptsDir}`)

      // Process file changes
      for await (const event of this.fileWatcher) {
        const fsEvent = event as { eventType: string; filename?: string }

        // Send notification for any file system event that might affect the prompts list
        if (fsEvent.eventType === 'change' || fsEvent.eventType === 'rename') {
          // Log the change for debugging
          console.error(`Prompts directory change detected: ${fsEvent.eventType} - ${fsEvent.filename || 'unknown file'}`)

          // Send the notification
          this.sendListChangedNotification()
        }
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('Error watching prompts directory:', error)
      }
    }
  }

  sendListChangedNotification(): void {
    try {
      // Send notification using the server's notification method
      // Format according to MCP specification
      this.server.notification({
        method: 'notifications/prompts/list_changed',
        params: {}  // Empty params object as per specification
      })

      console.error('Sent prompts/list_changed notification')
    } catch (error) {
      console.error('Failed to send prompts list changed notification:', error)
    }
  }

  // Convert internal Prompt to MCP Prompt format
  private toMcpPrompt(prompt: Prompt): McpPrompt {
    const description = isMultiMessagePrompt(prompt)
      ? prompt.description
      : prompt.description

    return {
      name: prompt.name,
      description: description || undefined,
      arguments: prompt.variables.map(varName => ({
        name: varName,
        required: true
      }))
    }
  }

  // Clean up resources
  async dispose(): Promise<void> {
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
    this.fileWatcher = null
  }
}
