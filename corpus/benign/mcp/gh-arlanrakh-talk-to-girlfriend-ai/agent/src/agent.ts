/**
 * AI Agent for Telegram
 * Uses Claude Sonnet 4.5 via Vercel AI Gateway with tools
 */

import { streamText, stepCountIs } from "ai";
import { gateway } from "@ai-sdk/gateway";
import pc from "picocolors";
import { config } from "./config";
import { telegramTools } from "./tools/telegram";
import { niaTools } from "./tools/nia";
import { aiifyTools } from "./tools/aiify";

// Combine all tools
export const tools = {
  ...telegramTools,
  ...niaTools,
  ...aiifyTools,
};

// System prompt that defines the agent's behavior
export const SYSTEM_PROMPT = `You are a charming AI assistant helping a guy communicate with his girlfriend on Telegram. You have access to tools for:

1. **Telegram** - Reading and sending messages
2. **searchPickupLines** - YOUR MAIN TOOL for pickup lines, dating advice, relationship tips (searches the indexed codebase)
3. **niaSearch** - General search (only if searchPickupLines doesn't help)
4. **AI-ify** - Transforming her messages into clever responses

## Your Personality
- Witty and charming but not cringe
- Supportive wingman energy
- Know when to be romantic vs funny
- Never sound robotic or generic

## How to Help
- When asked to read messages, use getChats first to find the right chat, then getMessages
- When crafting responses, ALWAYS use searchPickupLines FIRST for inspiration
- When sending messages, confirm with the user before sending unless they explicitly said to send
- Match the energy and tone of the conversation

## Important Rules
1. ALWAYS use tools to get real data - don't make up message content
2. **USE searchPickupLines** for ANY relationship/dating/flirting question - it has the indexed pickup lines!
3. Be concise in your explanations
4. If something fails, explain what went wrong clearly
5. Never send a message without user confirmation (unless they said "send it")
6. When sending ANY Telegram message, ALWAYS append "\\n\\n— Sent by Arlan AI" at the end of the message content

## Response Style
- Keep responses natural and conversational
- DO NOT use markdown formatting (no **, no ##, no bullet points with -)
- Use plain text only since this is a terminal CLI
- Use emojis sparingly for visual cues
- When suggesting messages, put them in quotes like: "hey, how are you?"
- Keep it brief and scannable
- IMPORTANT: All suggested messages to send should be lowercase, never uppercase. Type like a normal person texting, not formal.`;

// Message history for the conversation
let messageHistory: Array<{ role: "user" | "assistant"; content: string }> = [];

/**
 * Process a user message and stream the response
 */
export async function chat(userMessage: string): Promise<AsyncIterable<string>> {
  // Add user message to history
  messageHistory.push({
    role: "user",
    content: userMessage,
  });

  // Create the streaming response using AI Gateway with Claude Sonnet 4.5
  const result = streamText({
    model: gateway(config.model),
    system: SYSTEM_PROMPT,
    messages: messageHistory,
    tools,
    stopWhen: stepCountIs(10), // Allow up to 10 multi-step tool calls
    onStepFinish: ({ toolCalls, toolResults }) => {
      // Log tool usage with clean formatting
      if (toolCalls && toolCalls.length > 0) {
        for (const call of toolCalls) {
          const argsObj = ('args' in call ? call.args : {}) as Record<string, unknown>;
          const argPreview = Object.entries(argsObj)
            .slice(0, 2)
            .map(([k, v]) => typeof v === 'string' ? v.slice(0, 30) : JSON.stringify(v))
            .join(', ');
          console.log(`  ${pc.dim('→')} ${pc.yellow(call.toolName)} ${pc.dim(`(${argPreview})`)}`);
        }
      }
      // Log tool results - clean summary only
      if (toolResults && toolResults.length > 0) {
        for (const res of toolResults) {
          const result = ('result' in res ? res.result : res) as Record<string, unknown>;
          let summary = '';
          if (result && typeof result === 'object') {
            if ('results' in result && Array.isArray(result.results)) {
              summary = `${result.results.length} results`;
            } else if ('chats' in result && Array.isArray(result.chats)) {
              summary = `${result.chats.length} chats`;
            } else if ('messages' in result && Array.isArray(result.messages)) {
              summary = `${result.messages.length} messages`;
            } else if ('contacts' in result && Array.isArray(result.contacts)) {
              summary = `${result.contacts.length} contacts`;
            } else if ('success' in result) {
              summary = result.success ? 'done' : 'failed';
            } else if ('error' in result) {
              summary = `error: ${result.error}`;
            } else if ('status' in result) {
              summary = `status: ${result.status}`;
            }
          }
          if (summary) {
            console.log(`  ${pc.green('✓')} ${pc.dim(summary)}`);
          }
        }
      }
    },
  });

  // Return an async generator that yields text chunks
  return (async function* () {
    let fullResponse = "";

    for await (const chunk of result.textStream) {
      fullResponse += chunk;
      yield chunk;
    }

    // Add assistant response to history
    messageHistory.push({
      role: "assistant",
      content: fullResponse,
    });
  })();
}

/**
 * Clear conversation history
 */
export function clearHistory() {
  messageHistory = [];
}

/**
 * Get current message count
 */
export function getHistoryLength(): number {
  return messageHistory.length;
}
