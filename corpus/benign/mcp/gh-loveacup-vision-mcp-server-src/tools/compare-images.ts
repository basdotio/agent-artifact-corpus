import { z } from "zod";
import type { VisionApiClient } from "../utils/api-client.js";
import { resolveImageSource } from "../utils/file-handler.js";
import type { ChatMessage, MessageContent } from "../types.js";

export const compareImagesSchema = z.object({
  images: z
    .array(z.string())
    .min(2)
    .max(4)
    .describe("2-4 image sources (file paths or URLs) to compare"),
  prompt: z
    .string()
    .default("Compare these images and describe the differences and similarities.")
    .describe("Comparison prompt / question about the images"),
});

export type CompareImagesInput = z.infer<typeof compareImagesSchema>;

export async function compareImages(
  client: VisionApiClient,
  input: CompareImagesInput
): Promise<string> {
  const content: MessageContent[] = [
    { type: "text", text: input.prompt },
  ];

  for (const img of input.images) {
    const imageUrl = resolveImageSource(img);
    content.push({
      type: "image_url",
      image_url: { url: imageUrl, detail: "auto" },
    });
  }

  const messages: ChatMessage[] = [{ role: "user", content }];

  return client.chat(messages);
}
