// Type definitions for @modelcontextprotocol/sdk
declare module '@modelcontextprotocol/sdk' {
  // Base types
  export interface ServerOptions {
    name: string;
    version: string;
  }

  export interface ServerCapabilities {
    prompts: Record<string, unknown>;
    tools: Record<string, unknown>;
  }

  export interface ServerConfig {
    capabilities: ServerCapabilities;
  }

  // Request/Response types
  export interface PromptRequest {
    prompt: string;
    args?: Record<string, unknown>;
  }

  export interface ToolRequest {
    tool: string;
    args: Record<string, unknown>;
  }

  export interface Message {
    role: 'system' | 'user' | 'assistant';
    content: { type: 'text'; text: string };
  }

  export interface PromptResponse {
    messages: Message[];
  }

  export interface ToolResponse {
    content: Array<{ type: 'text'; text: string }>;
  }

  // Server class
  export class Server {
    constructor(options: ServerOptions, config: ServerConfig);
    
    // Prompt methods
    prompt(
      name: string, 
      handler: (args: Record<string, unknown>) => Promise<PromptResponse>
    ): void;
    
    // Tool methods
    tool(
      name: string, 
      handler: (args: Record<string, unknown>) => Promise<ToolResponse>
    ): void;
    
    // Request handling
    setRequestHandler<T, U>(
      schema: any, 
      handler: (req: T) => Promise<U>
    ): void;
    
    // Transport
    connect(transport: StreamableHTTPServerTransport): Promise<void>;
  }

  // Transport class
  export class StreamableHTTPServerTransport {
    constructor(options: {
      port: number;
      beforeHandle?: (req: any, res: any, next: () => void) => void;
    });
    
    addRoute(
      method: string, 
      path: string, 
      handler: (req: any, res: any) => void
    ): void;
  }

  // Schemas
  export const ListPromptsRequestSchema: any;
  export const GetPromptRequestSchema: any;
  export const ListToolsRequestSchema: any;
  export const CallToolRequestSchema: any;
}
