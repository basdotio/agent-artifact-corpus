import { McpError } from '@modelcontextprotocol/sdk/types.js'

/**
 * Custom error class for not found resources
 */
export class NotFoundError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'NotFoundError'
  }
}

/**
 * Custom error class for validation errors
 */
export class ValidationError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ValidationError'
  }
}

/**
 * Handles service errors and converts them to appropriate MCP errors
 * @param error The error to handle
 * @returns McpError instance
 */
export function handleServiceError(error: unknown): McpError {
  // If it's already an MCP error, return it directly
  if (error instanceof McpError) {
    return error
  }

  const errorMessage = error instanceof Error ? error.message : String(error)

  // Map custom errors to appropriate MCP error codes
  if (error instanceof NotFoundError) {
    return new McpError(404, errorMessage)
  }

  if (error instanceof ValidationError) {
    return new McpError(400, errorMessage)
  }

  // Handle error messages that indicate specific types of errors
  if (errorMessage.includes('not found')) {
    return new McpError(404, errorMessage)
  }

  if (errorMessage.includes('invalid') || errorMessage.includes('required')) {
    return new McpError(400, errorMessage)
  }

  // For unknown errors, log and return a generic internal error
  console.error('Unexpected error:', error)
  return new McpError(500, `An unexpected error occurred: ${errorMessage}`)
}
