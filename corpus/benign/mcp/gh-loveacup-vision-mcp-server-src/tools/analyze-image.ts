import { z } from "zod";
import type { VisionApiClient } from "../utils/api-client.js";
import { resolveImageSource } from "../utils/file-handler.js";
import type { ChatMessage } from "../types.js";

export const analyzeImageSchema = z.object({
  image: z
    .string()
    .describe("Image source: local file path or URL"),
  prompt: z
    .string()
    .default("Describe this image in detail.")
    .describe("Analysis prompt / question about the image"),
  detail: z
    .enum(["low", "high", "auto"])
    .default("auto")
    .describe("Image detail level for analysis"),
});

export type AnalyzeImageInput = z.infer<typeof analyzeImageSchema>;

export async function analyzeImage(
  client: VisionApiClient,
  input: AnalyzeImageInput
): Promise<string> {
  const imageUrl = resolveImageSource(input.image);

  const messages: ChatMessage[] = [
    {
      role: "user",
      content: [
        { type: "text", text: input.prompt },
        {
          type: "image_url",
          image_url: { url: imageUrl, detail: input.detail },
        },
      ],
    },
  ];

  return client.chat(messages);
}
