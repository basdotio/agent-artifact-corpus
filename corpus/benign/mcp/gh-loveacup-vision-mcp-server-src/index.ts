#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { loadConfig } from "./config.js";
import { VisionApiClient } from "./utils/api-client.js";
import {
  analyzeImageSchema,
  analyzeImage,
} from "./tools/analyze-image.js";
import { ocrImageSchema, ocrImage } from "./tools/ocr-image.js";
import {
  compareImagesSchema,
  compareImages,
} from "./tools/compare-images.js";
import {
  analyzeVideoSchema,
  analyzeVideo,
} from "./tools/analyze-video.js";

const config = loadConfig();
const client = new VisionApiClient(config);

const server = new McpServer({
  name: "vision-mcp-server",
  version: "1.0.0",
});

// Tool: analyze_image
server.tool(
  "analyze_image",
  "Analyze an image using a vision language model. Supports local file paths and URLs.",
  analyzeImageSchema.shape,
  async (input) => {
    try {
      const result = await analyzeImage(client, input);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: `Error: ${msg}` }],
        isError: true,
      };
    }
  }
);

// Tool: ocr_image
server.tool(
  "ocr_image",
  "Extract text from an image using OCR. Supports plain text, Markdown, and JSON output formats.",
  ocrImageSchema.shape,
  async (input) => {
    try {
      const result = await ocrImage(client, input);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: `Error: ${msg}` }],
        isError: true,
      };
    }
  }
);

// Tool: compare_images
server.tool(
  "compare_images",
  "Compare 2-4 images and describe differences/similarities. Supports local file paths and URLs.",
  compareImagesSchema.shape,
  async (input) => {
    try {
      const result = await compareImages(client, input);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: `Error: ${msg}` }],
        isError: true,
      };
    }
  }
);

// Tool: analyze_video
server.tool(
  "analyze_video",
  "Analyze video content using a vision language model. Requires a model with video support (e.g., Qwen3-VL).",
  analyzeVideoSchema.shape,
  async (input) => {
    try {
      const result = await analyzeVideo(client, input);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      return {
        content: [{ type: "text", text: `Error: ${msg}` }],
        isError: true,
      };
    }
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `Vision MCP Server started (model: ${config.model}, endpoint: ${config.baseUrl})`
  );
}

main().catch((err) => {
  console.error("Failed to start Vision MCP Server:", err);
  process.exit(1);
});
