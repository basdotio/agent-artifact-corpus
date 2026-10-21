import { McpError } from '@modelcontextprotocol/sdk/types.js'
import { PromptsService } from '../services/prompts.service.js'
import { handleServiceError } from '../utils/error-handler.js'

export class ToolsHandler {
  private readonly promptsService: PromptsService

  constructor() {
    this.promptsService = new PromptsService()
  }

  listTools() {
    return {
      tools: [
        {
          name: 'add_prompt',
          description: 'Adds a new prompt to the system (single content format)',
          inputSchema: {
            type: 'object',
            properties: {
              name: {
                type: 'string',
                description: 'Name of the prompt'
              },
              content: {
                type: 'string',
                description: 'Content of the prompt with variables in {{variable}} format'
              },
              description: {
                type: 'string',
                description: 'Description of the prompt'
              }
            },
            required: ['name', 'content']
          }
        },
        {
          name: 'update_prompt',
          description: 'Updates an existing prompt (supports both single content and multi-message formats)',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'ID of the prompt to update'
              },
              name: {
                type: 'string',
                description: 'New name for the prompt'
              },
              description: {
                type: 'string',
                description: 'New description for the prompt'
              },
              messages: {
                type: 'array',
                description: 'New messages (converts single content to multi-message format)',
                items: {
                  type: 'object',
                  properties: {
                    role: {
                      type: 'string',
                      enum: ['user', 'assistant'],
                      description: 'Role of the message sender'
                    },
                    content: {
                      type: 'object',
                      properties: {
                        type: {
                          type: 'string',
                          enum: ['text', 'image'],
                          description: 'Type of content'
                        },
                        text: {
                          type: 'string',
                          description: 'Text content (required for text type)'
                        },
                        image: {
                          type: 'string',
                          description: 'Image data (required for image type)'
                        }
                      },
                      required: ['type']
                    }
                  },
                  required: ['role', 'content']
                }
              }
            },
            required: ['id']
          }
        },
        {
          name: 'get_prompt',
          description: 'Gets a prompt by its ID',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'ID of the prompt to retrieve'
              }
            },
            required: ['id']
          }
        },
        {
          name: 'list_prompts',
          description: 'Lists all available prompts',
          inputSchema: {
            type: 'object',
            properties: {}
          }
        },
        {
          name: 'delete_prompt',
          description: 'Deletes a prompt by its ID',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'ID of the prompt to delete'
              }
            },
            required: ['id']
          }
        },
        {
          name: 'apply_prompt',
          description: 'Applies variables to a template prompt and returns the result',
          inputSchema: {
            type: 'object',
            properties: {
              id: {
                type: 'string',
                description: 'ID of the prompt to apply'
              },
              variables: {
                type: 'object',
                description: 'Object containing variable names and their values'
              }
            },
            required: ['id', 'variables']
          }
        },
        {
          name: 'add_multi_message_prompt',
          description: 'Adds a new multi-message prompt with role-based messages',
          inputSchema: {
            type: 'object',
            properties: {
              name: {
                type: 'string',
                description: 'Name of the prompt'
              },
              description: {
                type: 'string',
                description: 'Description of the prompt'
              },
              messages: {
                type: 'array',
                description: 'Array of messages with roles',
                items: {
                  type: 'object',
                  properties: {
                    role: {
                      type: 'string',
                      enum: ['user', 'assistant'],
                      description: 'Role of the message sender'
                    },
                    content: {
                      type: 'object',
                      properties: {
                        type: {
                          type: 'string',
                          enum: ['text', 'image'],
                          description: 'Type of content'
                        },
                        text: {
                          type: 'string',
                          description: 'Text content (required for text type)'
                        },
                        image: {
                          type: 'string',
                          description: 'Image data (required for image type)'
                        }
                      },
                      required: ['type']
                    }
                  },
                  required: ['role', 'content']
                }
              }
            },
            required: ['name', 'messages']
          }
        }
      ]
    }
  }

  async callTool(name: string, args: any) {
    try {
      switch (name) {
        case 'add_prompt': {
          const { name, content, description } = args
          const result = await this.promptsService.addPrompt({ name, content, description })
          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }]
          }
        }

        case 'update_prompt': {
          const { id, name, description, messages } = args
          const result = await this.promptsService.updatePrompt({ id, name, description, messages })
          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }]
          }
        }

        case 'get_prompt': {
          const { id } = args
          const result = await this.promptsService.getPrompt(id)
          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }]
          }
        }

        case 'list_prompts': {
          const prompts = await this.promptsService.listPrompts()
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({ prompts }, null, 2)
            }]
          }
        }

        case 'delete_prompt': {
          const { id } = args
          const result = await this.promptsService.deletePrompt(id)
          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }]
          }
        }

        case 'apply_prompt': {
          const { id, variables } = args
          const result = await this.promptsService.applyPrompt({ id, variables })
          return {
            content: [{
              type: 'text',
              text: typeof result.result === 'string'
                ? result.result
                : JSON.stringify(result, null, 2)
            }]
          }
        }

        case 'add_multi_message_prompt': {
          const { name, description, messages } = args
          const result = await this.promptsService.addMultiMessagePrompt({
            name,
            description,
            messages
          })
          return {
            content: [{
              type: 'text',
              text: JSON.stringify(result, null, 2)
            }]
          }
        }

        default:
          throw new McpError(
            404,
            `Unknown tool: ${name}`
          )
      }
    } catch (error) {
      // Transform errors into appropriate MCP responses
      const mcpError = handleServiceError(error)
      throw mcpError
    }
  }
}
