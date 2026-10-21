#!/usr/bin/env node
import fetch from "node-fetch";
import FormData from "form-data";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  ErrorCode,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";

interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
  };
}

interface ExecuteCodeArgs {
  code: string;
  lang: string;
  args?: string;
  user_id?: string;
  entity_id?: string;
  files?: Array<{
    id: string;
    session_id: string;
    name: string;
  }>;
}

interface DownloadFileArgs {
  session_id: string;
  fileId: string;
}

interface UploadFilesArgs {
  entity_id: string;
  files: Array<{
    name: string;
    content: string;
    contentType?: string;
  }>;
}

interface GetFilesInfoArgs {
  session_id: string;
  detail?: string;
}

interface DeleteFileArgs {
  session_id: string;
  fileId: string;
}

interface ApiResponse {
  content: Array<{
    type: string;
    text?: string;
    json?: any;
    data?: string;
    mimeType?: string;
  }>;
  tools?: never;
  _meta?: Record<string, unknown>;
}

function validateExecuteCodeArgs(args: unknown): args is ExecuteCodeArgs {
  return (
    typeof args === "object" &&
    args !== null &&
    "code" in args &&
    typeof (args as any).code === "string" &&
    "lang" in args &&
    typeof (args as any).lang === "string"
  );
}

function validateDownloadFileArgs(args: unknown): args is DownloadFileArgs {
  return (
    typeof args === "object" &&
    args !== null &&
    "session_id" in args &&
    typeof (args as any).session_id === "string" &&
    "fileId" in args &&
    typeof (args as any).fileId === "string"
  );
}

function validateUploadFilesArgs(args: unknown): args is UploadFilesArgs {
  return (
    typeof args === "object" &&
    args !== null &&
    "entity_id" in args &&
    typeof (args as any).entity_id === "string" &&
    "files" in args &&
    Array.isArray((args as any).files)
  );
}

function validateGetFilesInfoArgs(args: unknown): args is GetFilesInfoArgs {
  return (
    typeof args === "object" &&
    args !== null &&
    "session_id" in args &&
    typeof (args as any).session_id === "string"
  );
}

function validateDeleteFileArgs(args: unknown): args is DeleteFileArgs {
  return (
    typeof args === "object" &&
    args !== null &&
    "session_id" in args &&
    typeof (args as any).session_id === "string" &&
    "fileId" in args &&
    typeof (args as any).fileId === "string"
  );
}

// Helper function to get API key with multiple fallbacks
function getApiKey(): string {
  // Try multiple possible environment variable names
  const apiKey =
    process.env.LIBRECHAT_API_KEY ||
    process.env.LIBRECHAT_API_TOKEN ||
    process.env.API_KEY ||
    process.env.API_TOKEN;

  if (!apiKey) {
    console.error(
      "Environment variables available:",
      Object.keys(process.env).filter(
        (k) => k.includes("API") || k.includes("LIBRECHAT")
      )
    );
    throw new Error(
      "API key not found. Please set LIBRECHAT_API_KEY environment variable."
    );
  }

  return apiKey;
}

class LibreChatCodeInterpreterServer {
  private server: Server;
  private tools: ToolDefinition[];
  private apiKey: string;
  private baseUrl: string;

  constructor() {
    // Get API key during initialization
    try {
      this.apiKey = getApiKey();
      console.error("API key loaded successfully");
    } catch (error) {
      console.error("Failed to load API key:", error);
      process.exit(1);
    }

    this.baseUrl =
      process.env.LIBRECHAT_BASE_URL || "https://api.librechat.ai/v1";
    console.error("Using base URL:", this.baseUrl);

    this.server = new Server(
      {
        name: "librechat-code-interpreter",
        version: "1.3.2",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.tools = [
      {
        name: "executeCode",
        description: "Execute code in sandbox via LibreChat",
        inputSchema: {
          type: "object",
          properties: {
            code: { type: "string" },
            lang: {
              type: "string",
              enum: [
                "c",
                "cpp",
                "d",
                "f90",
                "go",
                "java",
                "js",
                "php",
                "py",
                "rs",
                "ts",
                "r",
              ],
            },
            args: { type: "string" },
            user_id: { type: "string" },
            entity_id: {
              type: "string",
              maxLength: 40,
              pattern: "^[A-Za-z0-9_-]+$",
            },
            files: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  id: { type: "string" },
                  session_id: { type: "string" },
                  name: { type: "string" },
                },
                required: ["id", "name", "session_id"],
              },
            },
          },
          required: ["code", "lang"],
        },
      },
      {
        name: "downloadFile",
        description: "Download a file from LibreChat session",
        inputSchema: {
          type: "object",
          properties: {
            session_id: { type: "string" },
            fileId: { type: "string" },
          },
          required: ["session_id", "fileId"],
        },
      },
      {
        name: "uploadFiles",
        description: "Upload binary files to LibreChat",
        inputSchema: {
          type: "object",
          properties: {
            entity_id: { type: "string" },
            files: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  name: { type: "string" },
                  content: { type: "string" }, // base64
                  contentType: { type: "string" },
                },
                required: ["name", "content"],
              },
            },
          },
          required: ["entity_id", "files"],
        },
      },
      {
        name: "getFilesInfo",
        description: "List files in a LibreChat session",
        inputSchema: {
          type: "object",
          properties: {
            session_id: { type: "string" },
            detail: { type: "string", default: "simple" },
          },
          required: ["session_id"],
        },
      },
      {
        name: "deleteFile",
        description: "Delete a file from a LibreChat session",
        inputSchema: {
          type: "object",
          properties: {
            session_id: { type: "string" },
            fileId: { type: "string" },
          },
          required: ["session_id", "fileId"],
        },
      },
    ];

    this.setupHandlers();

    this.server.onerror = (error) => console.error("[MCP Error]", error);
    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  private setupHandlers(): void {
    this.server.setRequestHandler(
      ListToolsRequestSchema,
      async (): Promise<{ tools: ToolDefinition[] }> => ({
        tools: this.tools,
      })
    );

    this.server.setRequestHandler(
      CallToolRequestSchema,
      async (request: {
        params: {
          name: string;
          arguments?: Record<string, unknown>;
        };
      }): Promise<ApiResponse> => {
        const name = request.params.name;
        const args = request.params.arguments || {};

        switch (name) {
          case "executeCode":
            if (!args.code || !args.lang) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Missing 'code' or 'lang'"
              );
            }
            if (!validateExecuteCodeArgs(args)) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Invalid arguments for executeCode"
              );
            }
            return this.executeCode(args);
          case "downloadFile":
            if (!args.session_id || !args.fileId) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Missing 'session_id' or 'fileId'"
              );
            }
            if (!validateDownloadFileArgs(args)) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Invalid arguments for downloadFile"
              );
            }
            return this.downloadFile(args);
          case "uploadFiles":
            if (
              !args.entity_id ||
              !Array.isArray(args.files) ||
              args.files.length === 0
            ) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Missing 'entity_id' or 'files'"
              );
            }
            if (!validateUploadFilesArgs(args)) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Invalid arguments for uploadFiles"
              );
            }
            return this.uploadFiles(args);
          case "getFilesInfo":
            if (!args.session_id) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Missing 'session_id'"
              );
            }
            if (!validateGetFilesInfoArgs(args)) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Invalid arguments for getFilesInfo"
              );
            }
            return this.getFilesInfo(args);
          case "deleteFile":
            if (!args.session_id || !args.fileId) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Missing 'session_id' or 'fileId'"
              );
            }
            if (!validateDeleteFileArgs(args)) {
              throw new McpError(
                ErrorCode.InvalidParams,
                "Invalid arguments for deleteFile"
              );
            }
            return this.deleteFile(args);
          default:
            throw new McpError(
              ErrorCode.MethodNotFound,
              `Unknown tool: ${name}`
            );
        }
      }
    );
  }

  private async executeCode(args: ExecuteCodeArgs): Promise<ApiResponse> {
    try {
      const resp = await fetch(`${this.baseUrl}/exec`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": this.apiKey,
        },
        body: JSON.stringify(args),
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        console.error("LibreChat exec error:", resp.status, errorText);
        throw new McpError(
          ErrorCode.InternalError,
          `LibreChat exec failed: ${resp.status} ${resp.statusText} - ${errorText}`
        );
      }

      const result = await resp.json();
      return { content: [{ type: "json", json: result }] };
    } catch (error) {
      console.error("Execute code error:", error);
      throw error;
    }
  }

  private async downloadFile(args: DownloadFileArgs): Promise<ApiResponse> {
    try {
      const { session_id, fileId } = args;
      const resp = await fetch(
        `${this.baseUrl}/download/${session_id}/${fileId}`,
        {
          headers: { "x-api-key": this.apiKey },
        }
      );

      if (resp.status === 404) {
        return {
          content: [{ type: "text", text: `File not found: ${fileId}` }],
        };
      }

      if (!resp.ok) {
        const errorText = await resp.text();
        console.error("Download error:", resp.status, errorText);
        throw new McpError(
          ErrorCode.InternalError,
          `Download failed: ${resp.status} ${resp.statusText} - ${errorText}`
        );
      }

      const buffer = await resp.arrayBuffer();
      const base64 = Buffer.from(buffer).toString("base64");
      return {
        content: [
          {
            type: "embeddedResource",
            data: base64,
            mimeType: resp.headers.get("content-type") || undefined,
          },
        ],
      };
    } catch (error) {
      console.error("Download file error:", error);
      throw error;
    }
  }

  private async uploadFiles(args: UploadFilesArgs): Promise<ApiResponse> {
    try {
      const form = new FormData();
      form.append("entity_id", args.entity_id);

      for (const f of args.files) {
        const buf = Buffer.from(f.content, "base64");
        form.append("files", buf, {
          filename: f.name,
          contentType: f.contentType,
        });
      }

      const resp = await fetch(`${this.baseUrl}/upload`, {
        method: "POST",
        headers: { "x-api-key": this.apiKey },
        body: form,
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        console.error("Upload error:", resp.status, errorText);
        throw new McpError(
          ErrorCode.InternalError,
          `Upload failed: ${resp.status} ${resp.statusText} - ${errorText}`
        );
      }

      const result = await resp.json();
      return { content: [{ type: "json", json: result }] };
    } catch (error) {
      console.error("Upload files error:", error);
      throw error;
    }
  }

  private async getFilesInfo(args: GetFilesInfoArgs): Promise<ApiResponse> {
    try {
      const { session_id, detail } = args;
      const url = new URL(`${this.baseUrl}/files/${session_id}`);
      if (detail) url.searchParams.set("detail", detail);

      const resp = await fetch(url.toString(), {
        headers: { "x-api-key": this.apiKey },
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        console.error("Get files info error:", resp.status, errorText);
        throw new McpError(
          ErrorCode.InternalError,
          `List files failed: ${resp.status} ${resp.statusText} - ${errorText}`
        );
      }

      const list = await resp.json();
      return { content: [{ type: "json", json: list }] };
    } catch (error) {
      console.error("Get files info error:", error);
      throw error;
    }
  }

  private async deleteFile(args: DeleteFileArgs): Promise<ApiResponse> {
    try {
      const { session_id, fileId } = args;
      const resp = await fetch(
        `${this.baseUrl}/files/${session_id}/${fileId}`,
        {
          method: "DELETE",
          headers: { "x-api-key": this.apiKey },
        }
      );

      if (!resp.ok) {
        const errorText = await resp.text();
        console.error("Delete file error:", resp.status, errorText);
        throw new McpError(
          ErrorCode.InternalError,
          `Delete failed: ${resp.status} ${resp.statusText} - ${errorText}`
        );
      }

      const result = await resp.json();
      return { content: [{ type: "json", json: result }] };
    } catch (error) {
      console.error("Delete file error:", error);
      throw error;
    }
  }

  public async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("LibreChat code interpreter MCP server running on stdio");
  }
}

const server = new LibreChatCodeInterpreterServer();
server.run().catch(console.error);
