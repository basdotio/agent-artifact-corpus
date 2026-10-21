#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
    Tool,
    McpError,
    ErrorCode,
    TextContent,
} from "@modelcontextprotocol/sdk/types.js";
import OpenAI from "openai";
import type { ChatCompletionMessageParam } from "openai/resources/chat/completions";

// Initialize OpenAI client
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
if (!OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY environment variable is required");
}

// Initialize OpenAI client
const openai = new OpenAI({
    apiKey: OPENAI_API_KEY
});

// Define supported models
const SUPPORTED_MODELS = ["gpt-4o", "gpt-4o-mini", "o1-preview", "o1-mini"] as const;
const DEFAULT_MODEL = "gpt-4o" as const;
type SupportedModel = typeof SUPPORTED_MODELS[number];

// Define available tools
const TOOLS: Tool[] = [
    {
        name: "openai_chat",
        description: `Use this tool when a user specifically requests to use one of OpenAI's models (${SUPPORTED_MODELS.join(", ")}). This tool sends messages to OpenAI's chat completion API using the specified model.`,
        inputSchema: {
            type: "object",
            properties: {
                messages: {
                    type: "array",
                    description: "Array of messages to send to the API",
                    items: {
                        type: "object",
                        properties: {
                            role: {
                                type: "string",
                                enum: ["system", "user", "assistant"],
                                description: "Role of the message sender"
                            },
                            content: {
                                type: "string",
                                description: "Content of the message"
                            }
                        },
                        required: ["role", "content"]
                    }
                },
                model: {
                    type: "string",
                    enum: SUPPORTED_MODELS,
                    description: `Model to use for completion (${SUPPORTED_MODELS.join(", ")})`,
                    default: DEFAULT_MODEL
                }
            },
            required: ["messages"]
        }
    }
];

// Initialize MCP server
const server = new Server(
    {
        name: "mcp-openai",
        version: "0.1.1",
    },
    {
        capabilities: {
            tools: {}
        }
    }
);

// Register handler for tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: TOOLS
}));

// Register handler for tool execution
server.setRequestHandler(CallToolRequestSchema, async (request): Promise<{
    content: TextContent[];
    isError?: boolean;
}> => {
    switch (request.params.name) {
        case "openai_chat": {
            try {
                // Parse request arguments
                const { messages: rawMessages, model } = request.params.arguments as {
                    messages: Array<{ role: string; content: string }>;
                    model?: SupportedModel;
                };

                // Validate model
                if (!SUPPORTED_MODELS.includes(model!)) {
                    throw new Error(`Unsupported model: ${model}. Must be one of: ${SUPPORTED_MODELS.join(", ")}`);
                }

                // Convert messages to OpenAI's expected format
                const messages: ChatCompletionMessageParam[] = rawMessages.map(msg => ({
                    role: msg.role as "system" | "user" | "assistant",
                    content: msg.content
                }));

                // Call OpenAI API with fixed temperature
                const completion = await openai.chat.completions.create({
                    messages,
                    model: model!
                });

                // Return the response
                return {
                    content: [{
                        type: "text",
                        text: completion.choices[0]?.message?.content || "No response received"
                    }]
                };
            } catch (error) {
                return {
                    content: [{
                        type: "text",
                        text: `OpenAI API error: ${(error as Error).message}`
                    }],
                    isError: true
                };
            }
        }
        default:
            throw new McpError(
                ErrorCode.MethodNotFound,
                `Unknown tool: ${request.params.name}`
            );
    }
});

// Initialize MCP server connection using stdio transport
const transport = new StdioServerTransport();
server.connect(transport).catch((error) => {
    console.error("Failed to start server:", error);
    process.exit(1);
});