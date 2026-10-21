/**
 * Strategic Plan tool implementation
 * Invokes PlanExe MCP Server for comprehensive strategic planning
 */

import { strategicPlanArgsValidator } from './schema.js';
import type { ToolCallParams, ToolCallResult } from '../../types/mcp-types.js';
import { logger } from '../../utils/logger.js';
import { validateToolInput, sanitizeErrorMessage } from '../../utils/security.js';
import { config } from '../../config/environment.js';

const PLANEXE_BASE_URL = process.env.PLANEXE_MCP_URL || 'http://127.0.0.1:8001';
const PLANEXE_API_KEY = process.env.PLANEXE_MCP_API_KEY;

interface PlanExeTaskCreateResponse {
  content: Array<{ type: string; text?: string }>;
  error?: { message: string };
}

async function callPlanExe(prompt: string): Promise<PlanExeTaskCreateResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (PLANEXE_API_KEY) {
    headers['Authorization'] = `Bearer ${PLANEXE_API_KEY}`;
  }
  
  const response = await fetch(`${PLANEXE_BASE_URL}/mcp/tools/call`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      tool: 'task_create',
      arguments: { prompt }
    }),
    signal: AbortSignal.timeout(5000),
  });
  
  if (!response.ok) {
    throw new Error(`PlanExe API returned ${response.status}: ${await response.text()}`);
  }
  
  return await response.json() as PlanExeTaskCreateResponse;
}

export async function executeStrategicPlan(
  params: ToolCallParams, 
  context: { rateLimitId: string }
): Promise<ToolCallResult> {
  const startTime = Date.now();
  
  try {
    const args = validateToolInput(strategicPlanArgsValidator, params.arguments) as { prompt: string };
    
    logger.info('Strategic plan tool execution started', { 
      promptSnippet: args.prompt.substring(0, 50),
      rateLimitId: context.rateLimitId
    });
    
    // Call PlanExe MCP Server
    const planexeResponse = await callPlanExe(args.prompt);
    
    if (planexeResponse.error) {
      throw new Error(`PlanExe error: ${planexeResponse.error.message}`);
    }
    
    const duration = Date.now() - startTime;
    logger.info('Strategic plan tool execution completed', {
      durationMs: duration,
      hasContent: planexeResponse.content.length > 0
    });
    
    return {
      isError: false,
      content: planexeResponse.content.map(c => ({ 
        type: 'text' as const, 
        text: c.text || '' 
      })),
    };
    
  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = sanitizeErrorMessage(error, config.isProduction);
    
    logger.error('Strategic plan tool execution failed', {
      error: errorMessage,
      durationMs: duration
    });
    
    return {
      isError: true,
      content: [{ 
        type: 'text', 
        text: `Failed to generate strategic plan: ${errorMessage}\n\nNote: PlanExe MCP Server must be running at ${PLANEXE_BASE_URL}` 
      }],
    };
  }
}
