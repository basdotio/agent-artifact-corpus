export interface VisionConfig {
  baseUrl: string;
  model: string;
  apiKey?: string;
  maxTokens: number;
  temperature: number;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string | MessageContent[];
}

export type MessageContent = TextContent | ImageContent;

export interface TextContent {
  type: "text";
  text: string;
}

export interface ImageContent {
  type: "image_url";
  image_url: {
    url: string;
    detail?: "low" | "high" | "auto";
  };
}

export interface ChatCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: {
    index: number;
    message: {
      role: string;
      content: string;
    };
    finish_reason: string;
  }[];
  usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
