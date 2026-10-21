import { z } from "zod";
import type { VisionApiClient } from "../utils/api-client.js";
import { resolveImageSource } from "../utils/file-handler.js";
import type { ChatMessage } from "../types.js";

export const ocrImageSchema = z.object({
  image: z
    .string()
    .describe("Image source: local file path or URL"),
  languages: z
    .string()
    .default("")
    .describe("Hint for expected languages, e.g. 'zh,en'"),
  format: z
    .enum(["plain", "markdown", "json"])
    .default("plain")
    .describe("Output format for extracted text"),
});

export type OcrImageInput = z.infer<typeof ocrImageSchema>;

const FORMAT_INSTRUCTIONS: Record<string, string> = {
  plain:
    "Extract ALL text from this image. Output the raw text preserving the original layout as much as possible.",
  markdown:
    "Extract ALL text from this image and format the result as Markdown. Preserve headings, lists, tables, and other structural elements.",
  json:
    'Extract ALL text from this image. Return a JSON object with a "blocks" array, where each block has "text" (string) and "type" (one of: heading, paragraph, list_item, table, caption, other).',
};

export async function ocrImage(
  client: VisionApiClient,
  input: OcrImageInput
): Promise<string> {
  const imageUrl = resolveImageSource(input.image);

  let prompt = FORMAT_INSTRUCTIONS[input.format] || FORMAT_INSTRUCTIONS.plain;
  if (input.languages) {
    prompt += `\nExpected languages: ${input.languages}. Please ensure correct recognition of characters in these languages.`;
  }

  const messages: ChatMessage[] = [
    {
      role: "user",
      content: [
        { type: "text", text: prompt },
        {
          type: "image_url",
          image_url: { url: imageUrl, detail: "high" },
        },
      ],
    },
  ];

  return client.chat(messages);
}
