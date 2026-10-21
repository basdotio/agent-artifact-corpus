#!/usr/bin/env bun

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { YoutubeTranscript } from "./youtube-transcript";

// Create an MCP server
const server = new McpServer({
	name: "youtube-transcript-mcp",
	version: "0.1.0",
});

// Add an addition tool
server.registerTool(
	"get-transcript",
	{
		title: "Get YouTube Transcript",
		description: "Get the transcript of a YouTube video",
		inputSchema: { url_or_video_id: z.string() },
	},
	async ({ url_or_video_id }) => {
		const transcript = await YoutubeTranscript.fetchTranscript(url_or_video_id);

		// Convert seconds to [XmYs] format
		const formatTime = (seconds: number) => {
			const minutes = Math.floor(seconds / 60);
			const secs = Math.floor(seconds % 60);
			return `[${minutes}m${secs}s]`;
		};

		// Format each segment with timestamp
		const formattedSegments = transcript.map(
			(item) => `${formatTime(item.offset)} ${item.text}`,
		);

		const transcriptText = formattedSegments.join(" ");

		return {
			content: [{ type: "text", text: transcriptText }],
		};
	},
);

// Start receiving messages on stdin and sending messages on stdout
const transport = new StdioServerTransport();
await server.connect(transport);
