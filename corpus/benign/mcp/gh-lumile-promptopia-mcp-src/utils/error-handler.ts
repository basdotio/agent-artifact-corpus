import { McpError } from '@modelcontextprotocol/sdk/types.js'

export class PromptNotFoundError extends Error {
  constructor(promptId: string) {
    super(`Prompt not found: ${promptId}`)
    this.name = 'PromptNotFoundError'
  }
}

export class ValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ValidationError'
  }
}

export function handleServiceError(error: unknown): McpError {
  if (error instanceof McpError) {
    return error
  }

  if (error instanceof PromptNotFoundError) {
    return new McpError(
      404,
      error.message
    )
  }

  if (error instanceof ValidationError) {
    return new McpError(
      400,
      error.message
    )
  }

  // Default case for unknown errors
  console.error('Unexpected error:', error)
  return new McpError(
    500,
    `An unexpected error occurred: ${error instanceof Error ? error.message : String(error)}`
  )
}
