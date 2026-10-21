export class FirestoreMcpError extends Error {
  readonly code: string
  readonly statusCode: number
  readonly details?: unknown

  constructor(
    message: string,
    options?: { code?: string; statusCode?: number; details?: unknown }
  ) {
    super(message)
    this.name = 'FirestoreMcpError'
    this.code = options?.code ?? 'INTERNAL_ERROR'
    this.statusCode = options?.statusCode ?? 500
    this.details = options?.details
  }
}

export class AuthorizationError extends FirestoreMcpError {
  constructor(message = 'Forbidden', details?: unknown) {
    super(message, { code: 'FORBIDDEN', statusCode: 403, details })
    this.name = 'AuthorizationError'
  }
}

export class NotFoundError extends FirestoreMcpError {
  constructor(message = 'Not found', details?: unknown) {
    super(message, { code: 'NOT_FOUND', statusCode: 404, details })
    this.name = 'NotFoundError'
  }
}

export class ValidationError extends FirestoreMcpError {
  constructor(message = 'Validation failed', details?: unknown) {
    super(message, { code: 'VALIDATION_ERROR', statusCode: 400, details })
    this.name = 'ValidationError'
  }
}
