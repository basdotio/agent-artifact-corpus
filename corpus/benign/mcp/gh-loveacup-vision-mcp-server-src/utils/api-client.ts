import type {
  VisionConfig,
  ChatMessage,
  ChatCompletionResponse,
} from "../types.js";

export class VisionApiClient {
  private config: VisionConfig;

  constructor(config: VisionConfig) {
    this.config = config;
  }

  async chat(messages: ChatMessage[]): Promise<string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.config.apiKey) {
      headers["Authorization"] = `Bearer ${this.config.apiKey}`;
    }

    const body = {
      model: this.config.model,
      messages,
      max_tokens: this.config.maxTokens,
      temperature: this.config.temperature,
    };

    const response = await fetch(this.config.baseUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(
        `Vision API error (${response.status}): ${text}`
      );
    }

    const data = (await response.json()) as ChatCompletionResponse;

    if (!data.choices || data.choices.length === 0) {
      throw new Error("Vision API returned no choices");
    }

    return data.choices[0].message.content;
  }
}
