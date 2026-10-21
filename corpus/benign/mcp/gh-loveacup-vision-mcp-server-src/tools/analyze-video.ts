import { z } from "zod";
import type { VisionApiClient } from "../utils/api-client.js";
import { resolveVideoSource, isUrl } from "../utils/file-handler.js";
import type { ChatMessage, MessageContent } from "../types.js";

export const analyzeVideoSchema = z.object({
  video: z
    .string()
    .describe("Video source: local file path or URL"),
  prompt: z
    .string()
    .default("Describe what happens in this video.")
    .describe("Analysis prompt / question about the video"),
});

export type AnalyzeVideoInput = z.infer<typeof analyzeVideoSchema>;

export async function analyzeVideo(
  client: VisionApiClient,
  input: AnalyzeVideoInput
): Promise<string> {
  // For models that support native video input (like Qwen3-VL),
  // send the video as a single "video_url" or "image_url" content.
  // Some OpenAI-compatible APIs treat video as image_url type.
  const videoUrl = resolveVideoSource(input.video);

  const content: MessageContent[] = [
    { type: "text", text: input.prompt },
    {
      type: "image_url",
      image_url: { url: videoUrl, detail: "auto" },
    },
  ];

  const messages: ChatMessage[] = [{ role: "user", content }];

  try {
    return await client.chat(messages);
  } catch (err) {
    // If the model doesn't support video via image_url,
    // return a clear error message
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.includes("video") || msg.includes("unsupported")) {
      throw new Error(
        `Video analysis failed. The model may not support direct video input. Error: ${msg}`
      );
    }
    throw err;
  }
}
