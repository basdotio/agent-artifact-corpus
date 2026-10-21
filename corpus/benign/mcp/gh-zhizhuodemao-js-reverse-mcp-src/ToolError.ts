/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

export const TOOL_ERROR_CODES = [
  'CANCELLED',
  'TIMEOUT',
  'INVALID_ARGUMENT',
  'NOT_FOUND',
  'PRECONDITION_FAILED',
  'CONFIRMATION_REQUIRED',
  'PERMISSION_DENIED',
  'CONFLICT',
  'CDP_ERROR',
  'IO_ERROR',
  'INTERNAL',
] as const;

export type ToolErrorCode = (typeof TOOL_ERROR_CODES)[number];

export class ToolError extends Error {
  readonly code: ToolErrorCode;
  readonly retryable: boolean;

  constructor(
    code: ToolErrorCode,
    message: string,
    options: {cause?: unknown; retryable?: boolean} = {},
  ) {
    super(message, {cause: options.cause});
    this.name = 'ToolError';
    this.code = code;
    this.retryable = options.retryable ?? false;
  }
}

export function normalizeToolError(error: unknown): ToolError {
  if (error instanceof ToolError) {
    return error;
  }
  const message = error instanceof Error ? error.message : String(error);
  const lower = message.toLowerCase();
  if (lower.includes('cancel') || lower.includes('abort')) {
    return new ToolError('CANCELLED', message, {cause: error, retryable: true});
  }
  if (lower.includes('timed out') || lower.includes('timeout')) {
    return new ToolError('TIMEOUT', message, {cause: error, retryable: true});
  }
  if (lower.includes('not found') || lower.includes('no page')) {
    return new ToolError('NOT_FOUND', message, {cause: error});
  }
  if (
    lower.includes('not enabled') ||
    lower.includes('not paused') ||
    lower.includes('is paused')
  ) {
    return new ToolError('PRECONDITION_FAILED', message, {cause: error});
  }
  if (
    lower.includes('invalid') ||
    lower.includes('out of range') ||
    lower.includes('must be provided') ||
    lower.includes('is required')
  ) {
    return new ToolError('INVALID_ARGUMENT', message, {cause: error});
  }
  return new ToolError('INTERNAL', message, {cause: error});
}
