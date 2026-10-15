/**
 * AI-ify tool - Transform messages into witty/romantic responses
 * Uses the agent's LLM to generate responses based on pickup lines context
 */

import { tool } from "ai";
import { z } from "zod";

export const aiifyMessage = tool({
  description: `Transform a message (usually her message) into a witty, romantic, or clever response. This tool helps you craft the perfect reply by:
1. Analyzing the incoming message's tone and context
2. Searching your pickup lines for relevant content
3. Generating a response that matches the vibe

Use this when you want to AI-ify your response to her message.`,
  inputSchema: z.object({
    her_message: z.string().describe("The message she sent that you want to respond to"),
    style: z
      .enum(["flirty", "romantic", "funny", "witty", "sweet", "playful", "caring"])
      .default("witty")
      .describe("The tone/style you want for the response"),
    context: z
      .string()
      .optional()
      .describe("Additional context about your relationship, inside jokes, or current situation"),
  }),
  execute: async ({ her_message, style, context }) => {
    // This tool doesn't actually generate the response directly
    // Instead, it structures the request for the LLM to handle
    // The LLM will use searchPickupLines and its own capabilities
    
    return {
      instruction: `Generate a ${style} response to: "${her_message}"`,
      style,
      originalMessage: her_message,
      context: context || "No additional context",
      suggestion: `Use searchPickupLines to find relevant content, then craft a ${style} response that:
- Matches the energy of her message
- Shows wit and personality
- Feels natural and not forced
- Could include a callback to something she said`,
    };
  },
});

export const aiifyTools = {
  aiifyMessage,
};
