/**
 * Clean MCP type definitions (eliminating 'any' types)
 */

import { z } from 'zod';
import {
  JSONRPCMessageSchema,
  RequestSchema,
  NotificationSchema,
  ResultSchema,
  TextContentSchema,
  SamplingMessageSchema,
  CreateMessageRequestSchema,
  CreateMessageResultSchema,
  ToolSchema,
  ListToolsRequestSchema,
  ListToolsResultSchema,
  CallToolRequestSchema,
  CallToolResultSchema,
  ListPromptsRequestSchema,
  ListPromptsResultSchema,
  GetPromptRequestSchema,
  GetPromptResultSchema,
  ServerCapabilitiesSchema,
  ImplementationSchema,
  InitializeRequestSchema,
  InitializeResultSchema,
  PingRequestSchema,
  EmptyResultSchema,
} from '@modelcontextprotocol/sdk/types.js';

// Base MCP types
export type JSONRPCMessage = z.infer<typeof JSONRPCMessageSchema>;
export type MCPRequest = z.infer<typeof RequestSchema>;
export type MCPNotification = z.infer<typeof NotificationSchema>;
export type MCPResult = z.infer<typeof ResultSchema>;

// Content types
export type TextContent = z.infer<typeof TextContentSchema>;
export type MCPMessage = z.infer<typeof SamplingMessageSchema>;

// Tool types
export type Tool = z.infer<typeof ToolSchema>;
export type ListToolsRequest = z.infer<typeof ListToolsRequestSchema>;
export type ListToolsResult = z.infer<typeof ListToolsResultSchema>;
export type CallToolRequest = z.infer<typeof CallToolRequestSchema>;
export type CallToolResult = z.infer<typeof CallToolResultSchema>;

// Prompt types
export type ListPromptsRequest = z.infer<typeof ListPromptsRequestSchema>;
export type ListPromptsResult = z.infer<typeof ListPromptsResultSchema>;
export type GetPromptRequest = z.infer<typeof GetPromptRequestSchema>;
export type GetPromptResult = z.infer<typeof GetPromptResultSchema>;

// Message handling types
export type CreateMessageRequest = z.infer<typeof CreateMessageRequestSchema>;
export type CreateMessageResult = z.infer<typeof CreateMessageResultSchema>;

// Server types
export type ServerCapabilities = z.infer<typeof ServerCapabilitiesSchema>;
export type Implementation = z.infer<typeof ImplementationSchema>;
export type InitializeRequest = z.infer<typeof InitializeRequestSchema>;
export type InitializeResult = z.infer<typeof InitializeResultSchema>;
export type PingRequest = z.infer<typeof PingRequestSchema>;
export type EmptyResult = z.infer<typeof EmptyResultSchema>;

// Union types for this server's specific request/response handling
export type ChlorpromazineRequest = 
  | InitializeRequest
  | PingRequest
  | CreateMessageRequest
  | ListToolsRequest
  | CallToolRequest
  | ListPromptsRequest
  | GetPromptRequest;

export type ChlorpromazineResult = 
  | InitializeResult
  | EmptyResult
  | CreateMessageResult
  | ListToolsResult
  | CallToolResult
  | ListPromptsResult
  | GetPromptResult;

export type ChlorpromazineNotification = MCPNotification;

// Helper types for handlers
export type ToolCallParams = CallToolRequest['params'];
export type ToolCallResult = CallToolResult;
export type CreateMessageParams = CreateMessageRequest['params'];
export type PromptGetParams = GetPromptRequest['params'];