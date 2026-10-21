// Type definitions

import { z } from "zod";
import { ToolSchema } from "@modelcontextprotocol/sdk/types.js";

// LSP message handling
export interface LSPMessage {
  jsonrpc: string;
  id?: number | string;
  method?: string;
  params?: any;
  result?: any;
  error?: any;
}

// Define a type for diagnostic subscribers
export type DiagnosticUpdateCallback = (uri: string, diagnostics: any[]) => void;

// Define a type for subscription context
export interface SubscriptionContext {
  callback: DiagnosticUpdateCallback;
}

// Logging level type
export type LoggingLevel = 'debug' | 'info' | 'notice' | 'warning' | 'error' | 'critical' | 'alert' | 'emergency';

// Tool input type
export const ToolInputSchema = ToolSchema.shape.inputSchema;
export type ToolInput = z.infer<typeof ToolInputSchema>;

// Tool handler types
export type ToolHandler = (args: any) => Promise<{ content: Array<{ type: string, text: string }>, isError?: boolean }>;

// Resource handler type
export type ResourceHandler = (uri: string) => Promise<{ contents: Array<{ type: string, text: string, uri: string }> }>;

// Subscription handler type
export type SubscriptionHandler = (uri: string) => Promise<{ ok: boolean, context?: SubscriptionContext, error?: string }>;

// Unsubscription handler type
export type UnsubscriptionHandler = (uri: string, context: any) => Promise<{ ok: boolean, error?: string }>;

// Prompt types
export interface Prompt {
  name: string;
  description: string;
  arguments?: Array<{
    name: string;
    description: string;
    required: boolean;
  }>;
}

export type PromptHandler = (args?: Record<string, string>) => Promise<{
  messages: Array<{
    role: string;
    content: {
      type: string;
      text: string;
    };
  }>;
}>;

// Schema definitions
export const GetInfoOnLocationArgsSchema = z.object({
  file_path: z.string().describe("Path to the file"),
  language_id: z.string().describe("The programming language the file is written in"),
  line: z.number().describe(`Line number`),
  column: z.number().describe(`Column position`),
});

export const GetCompletionsArgsSchema = z.object({
  file_path: z.string().describe(`Path to the file`),
  language_id: z.string().describe(`The programming language the file is written in`),
  line: z.number().describe(`Line number`),
  column: z.number().describe(`Column position`),
});

export const GetCodeActionsArgsSchema = z.object({
  file_path: z.string().describe(`Path to the file`),
  language_id: z.string().describe(`The programming language the file is written in`),
  start_line: z.number().describe(`Start line number`),
  start_column: z.number().describe(`Start column position`),
  end_line: z.number().describe(`End line number`),
  end_column: z.number().describe(`End column position`),
});

export const OpenDocumentArgsSchema = z.object({
  file_path: z.string().describe(`Path to the file to open`),
  language_id: z.string().describe(`The programming language the file is written in`),
});

export const CloseDocumentArgsSchema = z.object({
  file_path: z.string().describe(`Path to the file to close`),
});

export const GetDiagnosticsArgsSchema = z.object({
  file_path: z.string().optional().describe(`Path to the file to get diagnostics for. If not provided, returns diagnostics for all open files.`),
});

export const SetLogLevelArgsSchema = z.object({
  level: z.enum(['debug', 'info', 'notice', 'warning', 'error', 'critical', 'alert', 'emergency'])
    .describe("The logging level to set")
});

export const RestartLSPServerArgsSchema = z.object({
  root_dir: z.string().optional().describe("The root directory for the LSP server. If not provided, the server will not be initialized automatically."),
});

export const StartLSPArgsSchema = z.object({
  root_dir: z.string().describe("The root directory for the LSP server"),
});
