/**
 * Environment variable validation and configuration
 */

import { z } from 'zod';
import { DEFAULT_SITES } from './constants.js';

const EnvironmentSchema = z.object({
  SERPAPI_KEY: z.string().min(1, 'SERPAPI_KEY is required'),
  BRAVE_SEARCH_API_KEY: z.string().optional(),
  PORT: z.string().regex(/^\d+$/, 'PORT must be a number').optional(),
  API_KEY: z.string().optional(),
  SITE_FILTER: z.string().optional(),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development')
});

type Environment = z.infer<typeof EnvironmentSchema>;

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Environment variable ${key} is required`);
  }
  return value;
}

function parseCommaSeparated(value: string | undefined): string[] {
  if (!value) return [];
  return value.split(',').map(s => s.trim()).filter(Boolean);
}

function validateEnvironment(): Environment {
  const result = EnvironmentSchema.safeParse(process.env);
  
  if (!result.success) {
    const errors = result.error.issues.map(issue => 
      `${issue.path.join('.')}: ${issue.message}`
    ).join(', ');
    throw new Error(`Environment validation failed: ${errors}`);
  }
  
  return result.data;
}

// Validate environment on import
const env = validateEnvironment();

export const config = {
  serpApiKey: env.SERPAPI_KEY,
  braveSearchApiKey: env.BRAVE_SEARCH_API_KEY || null,
  port: parseInt(env.PORT || '3000'),
  apiKey: env.API_KEY || null,
  siteFilter: parseCommaSeparated(env.SITE_FILTER),
  nodeEnv: env.NODE_ENV,
  
  // Computed values
  get searchSites() {
    return this.siteFilter.length > 0 ? this.siteFilter : DEFAULT_SITES;
  },
  
  get isDevelopment() {
    return this.nodeEnv === 'development';
  },
  
  get isProduction() {
    return this.nodeEnv === 'production';
  },
  
  get isTest() {
    return this.nodeEnv === 'test';
  }
} as const;

export type Config = typeof config;