#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
// Fixed chalk import for ESM
import chalk from 'chalk';

interface ActorCriticThoughtData {
  content: string;
  role: 'actor' | 'critic';
  nextRoundNeeded: boolean;
  thoughtNumber: number;
  totalThoughts: number;
}

class ActorCriticThinkingServer {
  private thoughtHistory: ActorCriticThoughtData[] = [];
  private currentRound: number = 1;

  private validateThoughtData(input: unknown): ActorCriticThoughtData {
    const data = input as Record<string, unknown>;

    if (!data.content || typeof data.content !== 'string') {
      throw new Error('Invalid content: must be a string');
    }
    if (!data.role || (data.role !== 'actor' && data.role !== 'critic')) {
      throw new Error('Invalid role: must be either "actor" or "critic"');
    }
    if (typeof data.nextRoundNeeded !== 'boolean') {
      throw new Error('Invalid nextRoundNeeded: must be a boolean');
    }
    if (!data.thoughtNumber || typeof data.thoughtNumber !== 'number') {
      throw new Error('Invalid thoughtNumber: must be a number');
    }
    if (!data.totalThoughts || typeof data.totalThoughts !== 'number') {
      throw new Error('Invalid totalThoughts: must be a number');
    }
    if (data.totalThoughts < 3) {
      throw new Error('Invalid totalThoughts: must be >= 3');
    }
    if (data.totalThoughts % 2 === 0) {
      throw new Error('Invalid totalThoughts: must be odd');
    }

    return {
      content: data.content,
      role: data.role as 'actor' | 'critic',
      nextRoundNeeded: data.nextRoundNeeded,
      thoughtNumber: data.thoughtNumber,
      totalThoughts: data.totalThoughts,
    };
  }

  private formatThought(thoughtData: ActorCriticThoughtData): string {
    const { thoughtNumber, content, role } = thoughtData;

    let prefix = '';
    let roleIcon = '';
    let roleColor = chalk.blue;

    if (role === 'actor') {
      prefix = '🎭 Actor';
      roleIcon = '🎭';
      roleColor = chalk.green;
    } else {
      prefix = '🔍 Critic';
      roleIcon = '🔍';
      roleColor = chalk.yellow;
    }

    const header = roleColor(`${prefix} - Round ${Math.ceil(thoughtNumber / 2)} (Thought ${thoughtNumber})`);
    const border = '─'.repeat(Math.max(header.length, content.length) + 4);

    return `
┌${border}┐
│ ${header} │
├${border}┤
│ ${content.padEnd(border.length - 2)} │
└${border}┘`;
  }

  public processThought(input: unknown): { content: Array<{ type: string; text: string }>; isError?: boolean } {
    try {
      const validatedInput = this.validateThoughtData(input);

      this.thoughtHistory.push(validatedInput);

      // 更新当前轮次
      this.currentRound = Math.ceil(validatedInput.thoughtNumber / 2);

      const formattedThought = this.formatThought(validatedInput);
      console.error(formattedThought);

      // 检查是否需要切换角色
      const nextRole = validatedInput.role === 'actor' ? 'critic' : 'actor';
      const isRoundComplete = validatedInput.thoughtNumber % 2 === 0;

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            thoughtNumber: validatedInput.thoughtNumber,
            totalThoughts: validatedInput.totalThoughts,
            currentRound: this.currentRound,
            currentRole: validatedInput.role,
            nextRole: nextRole,
            isRoundComplete: isRoundComplete,
            nextRoundNeeded: validatedInput.nextRoundNeeded,
            thoughtHistoryLength: this.thoughtHistory.length,
            actorThoughts: this.thoughtHistory.filter(t => t.role === 'actor').length,
            criticThoughts: this.thoughtHistory.filter(t => t.role === 'critic').length
          }, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: error instanceof Error ? error.message : String(error),
            status: 'failed'
          }, null, 2)
        }],
        isError: true
      };
    }
  }
}

const ACTOR_CRITIC_THINKING_TOOL: Tool = {
  name: "actor-critic-thinking",
  description: `A sophisticated tool for dual-perspective performance analysis through actor-critic methodology.
This tool enables comprehensive evaluation of performances, creative works, or decisions by embodying both the performer's mindset and the critic's analytical perspective.
Each thought alternates between actor (creative/experiential) and critic (analytical/evaluative) viewpoints, creating a balanced assessment.

When to use this tool:
- Evaluating artistic performances, creative works, or strategic decisions
- Analyzing the gap between intention and execution
- Providing constructive feedback that considers both creative vision and technical execution
- Reviewing complex scenarios that require both empathy and objectivity
- Situations requiring balanced assessment of subjective and objective criteria
- Performance reviews that need both self-reflection and external evaluation
- Creative processes that benefit from iterative refinement

Key features:
- Alternates between actor (performer) and critic (evaluator) perspectives
- Tracks rounds of dual-perspective analysis
- Allows for multiple rounds of actor-critic dialogue
- Balances empathetic understanding with objective analysis
- Generates nuanced, multi-dimensional assessments
- Provides actionable feedback for improvement

Parameters explained:
- content: Your current analysis content from the specified role perspective
- role: Either "actor" (empathetic/creative viewpoint) or "critic" (analytical/evaluative viewpoint)
- nextRoundNeeded: True if another round of actor-critic dialogue is needed
- thoughtNumber: Current thought number in the sequence (increments with each thought)
- totalThoughts: Total number of thoughts planned (must be odd and >= 3)

Actor perspective should include:
* Understanding intentions, creative choices, emotional context, challenges faced
* Self-reflection on performance and decision-making process
* Explanation of creative vision and goals

Critic perspective should include:
* Technical execution analysis, effectiveness evaluation
* Audience impact assessment, comparative analysis
* Objective feedback and improvement suggestions

You should:
1. Start with either actor or critic perspective
2. Alternate between perspectives to maintain balance
3. Continue rounds until comprehensive analysis is achieved
4. Focus on relevant performance aspects
5. Generate balanced assessments that honor both perspectives
6. Provide constructive, actionable feedback
7. Only set nextRoundNeeded to false when analysis is complete`,
  inputSchema: {
    type: "object",
    properties: {
      content: {
        type: "string",
        description: "Your current analysis content from the specified role perspective"
      },
      role: {
        type: "string",
        enum: ["actor", "critic"],
        description: "The perspective role: 'actor' for empathetic/creative viewpoint, 'critic' for analytical/evaluative viewpoint"
      },
      nextRoundNeeded: {
        type: "boolean",
        description: "Whether another round of actor-critic dialogue is needed"
      },
      thoughtNumber: {
        type: "integer",
        description: "Current thought number in the sequence",
        minimum: 1
      },
      totalThoughts: {
        type: "integer",
        description: "Total number of thoughts planned (must be odd and >= 3)",
        minimum: 3
      }
    },
    required: ["content", "role", "nextRoundNeeded", "thoughtNumber", "totalThoughts"]
  }
};

const server = new Server(
  {
    name: "actor-critic-thinking-server",
    version: "0.2.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

const thinkingServer = new ActorCriticThinkingServer();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [ACTOR_CRITIC_THINKING_TOOL],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "actor-critic-thinking") {
    return thinkingServer.processThought(request.params.arguments);
  }

  return {
    content: [{
      type: "text",
      text: `Unknown tool: ${request.params.name}`
    }],
    isError: true
  };
});

async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Actor-Critic Thinking MCP Server running on stdio");
}

runServer().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});
