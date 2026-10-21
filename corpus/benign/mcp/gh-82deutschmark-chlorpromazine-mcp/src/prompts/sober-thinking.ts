/**
 * Sober Thinking prompt implementation
 */

import type { GetPromptResult } from '../types/mcp-types.js';
import { z } from 'zod';

// No arguments are needed for this prompt anymore.
const SoberThinkingArgsSchema = z.object({});

export const soberThinkingPrompt = {
  name: 'sober_thinking',
  description: 'Provides a senior developer analysis of the project based on OS, Git history, and project files.',
  arguments: [] as Array<{ name: string; description: string; required: boolean }>,

  async render(args: unknown): Promise<GetPromptResult> {
    // No arguments to validate
    SoberThinkingArgsSchema.parse(args);

    const promptText = `You are a senior software developer tasked with analyzing a project.

**Instructions:**
1. Use the 'sober_thinking' tool to gather context. This will provide you with OS information, recent git history, and the contents of README.md, .env, and CHANGELOG.md.
2. Review all the information provided by the tool.
3. Provide a concise analysis of the project's current state, potential issues, and your overall thoughts as a senior developer.
4. Structure your analysis clearly with headings.

**Important:** Base your entire analysis on the information provided by the tool. Do not hallucinate or make assumptions.`;

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
} as const;