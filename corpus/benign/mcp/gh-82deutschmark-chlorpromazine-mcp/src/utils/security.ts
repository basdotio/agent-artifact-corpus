/**
 * Security utilities for input validation and sanitization
 */

import { z } from 'zod';
import { SECURITY } from '../config/constants.js';

export class SecurityError extends Error {
  constructor(message: string, public readonly details?: unknown) {
    super(message);
    this.name = 'SecurityError';
  }
}

/**
 * Sanitizes search query input to prevent injection attacks
 */
export function sanitizeSearchQuery(query: string): string {
  if (typeof query !== 'string') {
    throw new SecurityError('Query must be a string');
  }
  
  // Remove potentially dangerous characters, keep only alphanumeric, spaces, hyphens, underscores, dots
  const sanitized = query
    .replace(/[^\w\s\-_.]/g, '')
    .slice(0, SECURITY.MAX_QUERY_LENGTH)
    .trim();
    
  if (sanitized.length === 0) {
    throw new SecurityError('Query cannot be empty after sanitization');
  }
  
  return sanitized;
}

/**
 * Validates tool input against a Zod schema with security checks
 */
export function validateToolInput<T>(schema: z.ZodSchema<T>, input: unknown): T {
  try {
    const result = schema.safeParse(input);
    if (!result.success) {
      throw new SecurityError('Invalid input', result.error.issues);
    }
    return result.data;
  } catch (error) {
    if (error instanceof SecurityError) {
      throw error;
    }
    throw new SecurityError('Input validation failed', error);
  }
}

/**
 * Sanitizes environment file content to hide sensitive values
 */
export function maskEnvValue(line: string): string {
  if (typeof line !== 'string') {
    return '(Invalid line)';
  }
  
  const trimmed = line.trim();
  
  // Skip comments and empty lines
  if (trimmed.length === 0 || trimmed.startsWith('#')) {
    return line;
  }
  
  // Check for sensitive keys
  const sensitiveKeys = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'AUTH'];
  const [key, ...rest] = trimmed.split('=');
  
  if (sensitiveKeys.some(sensitive => key.toUpperCase().includes(sensitive))) {
    return `${key}=***`;
  }
  
  // For non-sensitive values, still limit length to prevent info disclosure
  if (rest.length > 0 && rest.join('=').length > 50) {
    return `${key}=${rest.join('=').slice(0, 50)}...`;
  }
  
  return line;
}

/**
 * Validates file path to prevent directory traversal attacks
 */
export function validateFilePath(filePath: string): string {
  if (typeof filePath !== 'string') {
    throw new SecurityError('File path must be a string');
  }
  
  // Prevent directory traversal
  if (filePath.includes('..') || filePath.includes('~')) {
    throw new SecurityError('Directory traversal not allowed');
  }
  
  // Ensure path is relative to current directory
  const allowedFiles = [
    'README.md',
    '.env',
    'CHANGELOG',
    'CHANGELOG.md',
    'package.json',
    'tsconfig.json'
  ];
  
  const fileName = filePath.split(/[\\/]/).pop() || '';
  if (!allowedFiles.includes(fileName)) {
    throw new SecurityError(`File ${fileName} not allowed`);
  }
  
  return filePath;
}

/**
 * Rate limiting identifier generation
 */
export function generateRateLimitId(req: { headers?: { [key: string]: string | string[] } }): string {
  // In production, use IP address. For development, use a static identifier
  const forwarded = req.headers?.['x-forwarded-for'];
  const ip = req.headers?.['x-real-ip'] || 
             (Array.isArray(forwarded) ? forwarded[0] : forwarded) ||
             'unknown';
  
  return typeof ip === 'string' ? ip : 'unknown';
}

/**
 * Sanitizes error messages for client responses (removes stack traces in production)
 */
export function sanitizeErrorMessage(error: unknown, isProduction: boolean): string {
  if (error instanceof Error) {
    if (isProduction) {
      // In production, return generic message for security
      return error.message || 'An error occurred';
    } else {
      // In development, include stack trace for debugging
      return error.stack || error.message || 'An error occurred';
    }
  }
  
  return 'An unknown error occurred';
}