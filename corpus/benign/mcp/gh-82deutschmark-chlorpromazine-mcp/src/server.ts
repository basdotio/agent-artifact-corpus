/**
 * Chlorpromazine MCP Server - Modern Implementation (v0.4.0)
 * 
 * A secure, high-level Model Context Protocol server using registerTool/registerPrompt.
 */

import 'dotenv/config';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import express from 'express';
import type { Request, Response } from 'express';
import { z } from 'zod';

// Application imports
import { config } from './config/environment.js';
import { SERVER_INFO } from './config/constants.js';
import { logger } from './utils/logger.js';
import { serpApiClient } from './services/serpapi.js';

// Tool executors
import { executeKillTrip } from './tools/kill-trip/index.js';
import { executeSoberThinking } from './tools/sober-thinking/index.js';
import { executeBraveSearch } from './tools/brave-search/index.js';
import { executeStrategicPlan } from './tools/strategic-plan/index.js';

// Argument Schemas
import { 
  KillTripArgsSchema, 
  SoberThinkingArgsSchema, 
  BraveSearchArgsSchema,
  StrategicPlanArgsSchema
} from './types/tool-types.js';

/**
 * Main server startup function
 */
async function main(): Promise<void> {
  try {
    logger.info('Chlorpromazine MCP Server starting (Modern API)...', {
      version: SERVER_INFO.version,
      nodeEnv: config.nodeEnv,
      port: config.port
    });

    // Create high-level MCP server
    const server = new McpServer({
      name: SERVER_INFO.name,
      version: SERVER_INFO.version,
    });

    // --- Tool Registration ---
    
    // kill_trip
    server.tool(
      'kill_trip',
      'Search official documentation via SerpAPI to verify facts and avoid hallucinations',
      KillTripArgsSchema.shape,
      async (args) => {
        logger.info('Executing tool: kill_trip', { query: args.query });
        const result = await executeKillTrip(
          { name: 'kill_trip', arguments: args } as any, 
          { rateLimitId: 'default' }
        );
        return {
          content: result.content
        };
      }
    );

    // sober_thinking
    server.tool(
      'sober_thinking',
      'Analyze current project files to ground responses in actual project state',
      SoberThinkingArgsSchema.shape,
      async (args) => {
        logger.info('Executing tool: sober_thinking');
        const result = await executeSoberThinking(
          { name: 'sober_thinking', arguments: args } as any, 
          { rateLimitId: 'default' }
        );
        return {
          content: result.content
        };
      }
    );

    // brave_search
    server.tool(
      'brave_search',
      'Search the web using Brave Search API for up-to-date information',
      BraveSearchArgsSchema.shape,
      async (args) => {
        logger.info('Executing tool: brave_search', { query: args.query });
        const result = await executeBraveSearch(
          { name: 'brave_search', arguments: args } as any, 
          { rateLimitId: 'default' }
        );
        return {
          content: result.content
        };
      }
    );

    // strategic_plan
    server.tool(
      'strategic_plan',
      'Generate comprehensive strategic plans using PlanExe MCP Server. Use for business planning, project roadmaps, workflow optimization, or any complex multi-step planning task.',
      StrategicPlanArgsSchema.shape,
      async (args) => {
        logger.info('Executing tool: strategic_plan', { promptSnippet: args.prompt.substring(0, 50) });
        const result = await executeStrategicPlan(
          { name: 'strategic_plan', arguments: args } as any, 
          { rateLimitId: 'default' }
        );
        return {
          content: result.content
        };
      }
    );

    // --- Prompt Registration ---

    // sober_thinking
    server.prompt(
      'sober_thinking',
      'Provides a senior developer analysis of the project based on OS, Git history, and project files.',
      {},
      async () => ({
        messages: [{
          role: 'user',
          content: {
            type: 'text',
            text: `You are a senior software developer tasked with analyzing a project.

**Instructions:**
1. Use the 'sober_thinking' tool to gather context. This will provide you with OS information, recent git history, and the contents of README.md, .env, and CHANGELOG.md.
2. Review all the information provided by the tool.
3. Provide a concise analysis of the project's current state, potential issues, and your overall thoughts as a senior developer.
4. Structure your analysis clearly with headings.

**Important:** Base your entire analysis on the information provided by the tool. Do not hallucinate or make assumptions.`
          }
        }]
      })
    );

    // buzzkill
    server.prompt(
      'buzzkill',
      'Debug systematic issues with structured analysis and reality-checking',
      {
        ISSUE_DESCRIPTION: z.string().describe('Description of the issue or problem'),
        RECENT_CHANGES: z.string().optional().describe('Any recent changes that might be related'),
        EXPECTED_BEHAVIOR: z.string().optional().describe('What should happen'),
        ACTUAL_BEHAVIOR: z.string().optional().describe('What actually happens')
      },
      async (args) => {
        let promptText = `You need to systematically debug this issue: "${args.ISSUE_DESCRIPTION}"

**Debugging methodology:**
1. **Ground yourself in reality first**
   - Use the sober_thinking tool to read current project files
   - Understand the actual codebase state, not assumptions

2. **Gather additional facts**
   - Use kill_trip tool to search for similar issues in documentation
   - Look for known solutions or common pitfalls

3. **Systematic analysis**
   - Break down the problem into components
   - Identify what's working vs. what's broken
   - Look for patterns or correlations

4. **Generate hypotheses**
   - Based on facts, not speculation
   - Prioritize most likely causes
   - Consider recent changes as potential triggers

**Issue details:**`;

        if (args.RECENT_CHANGES) {
          promptText += `\n- **Recent changes:** ${args.RECENT_CHANGES}`;
        }
        
        if (args.EXPECTED_BEHAVIOR) {
          promptText += `\n- **Expected behavior:** ${args.EXPECTED_BEHAVIOR}`;
        }
        
        if (args.ACTUAL_BEHAVIOR) {
          promptText += `\n- **Actual behavior:** ${args.ACTUAL_BEHAVIOR}`;
        }

        promptText += `

**Your response should include:**
1. Summary of current project state (from sober_thinking)
2. Relevant documentation findings (from kill_trip searches)
3. Step-by-step diagnostic approach
4. Specific actionable recommendations
5. Potential risks and how to mitigate them

**Remember:** Be methodical, fact-based, and avoid speculation. If you need more information, ask specific questions.`;

        return {
          messages: [{
            role: 'user',
            content: {
              type: 'text',
              text: promptText
            }
          }]
        };
      }
    );

    // --- Web Server Setup ---

    const app = express();
    let transport: SSEServerTransport | null = null;

    app.get('/sse', async (req: Request, res: Response) => {
      logger.info('New SSE connection attempt');
      transport = new SSEServerTransport('/messages', res);
      await server.connect(transport);
    });

    app.post('/messages', async (req: Request, res: Response) => {
      if (!transport) {
        res.status(400).send('No active SSE session');
        return;
      }
      await transport.handlePostMessage(req, res);
    });

    app.get('/healthz', (req: Request, res: Response) => {
      res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        version: SERVER_INFO.version,
        checks: {
          serpApi: serpApiClient.isConfigured()
        }
      });
    });

    app.listen(config.port, () => {
      logger.info('Chlorpromazine MCP Server ready (SSE)', {
        port: config.port,
        env: config.nodeEnv
      });
    });

  } catch (error) {
    logger.error('Failed to start server', {
      error: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined
    });
    process.exit(1);
  }
}

main();