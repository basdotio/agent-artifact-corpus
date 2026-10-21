/**
 * Buzzkill prompt implementation - for systematic debugging
 */

import type { GetPromptResult } from '../types/mcp-types.js';
import type { BuzzkillPromptArgs } from '../types/app-types.js';
import { z } from 'zod';

const BuzzkillArgsSchema = z.object({
  ISSUE_DESCRIPTION: z.string().min(1, 'ISSUE_DESCRIPTION cannot be empty.'),
  RECENT_CHANGES: z.string().optional(),
  EXPECTED_BEHAVIOR: z.string().optional(),
  ACTUAL_BEHAVIOR: z.string().optional(),
});

export const buzzkillPrompt = {
  name: 'buzzkill',
  description: 'Debug systematic issues with structured analysis and reality-checking',
  arguments: [
    { 
      name: 'ISSUE_DESCRIPTION', 
      description: 'Description of the issue or problem', 
      required: true 
    },
    { 
      name: 'RECENT_CHANGES', 
      description: 'Any recent changes that might be related', 
      required: false 
    },
    { 
      name: 'EXPECTED_BEHAVIOR', 
      description: 'What should happen', 
      required: false 
    },
    { 
      name: 'ACTUAL_BEHAVIOR', 
      description: 'What actually happens', 
      required: false 
    }
  ] as Array<{ name: string; description: string; required: boolean }>,
  
  async render(args: unknown): Promise<GetPromptResult> {
    // Validate arguments
    const validatedArgs = BuzzkillArgsSchema.parse(args) as BuzzkillPromptArgs;
    
    let promptText = `You need to systematically debug this issue: "${validatedArgs.ISSUE_DESCRIPTION}"

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

    if (validatedArgs.RECENT_CHANGES) {
      promptText += `\n- **Recent changes:** ${validatedArgs.RECENT_CHANGES}`;
    }
    
    if (validatedArgs.EXPECTED_BEHAVIOR) {
      promptText += `\n- **Expected behavior:** ${validatedArgs.EXPECTED_BEHAVIOR}`;
    }
    
    if (validatedArgs.ACTUAL_BEHAVIOR) {
      promptText += `\n- **Actual behavior:** ${validatedArgs.ACTUAL_BEHAVIOR}`;
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
} as const;