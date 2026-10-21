// Legacy single content prompt interface for backward compatibility
export interface SingleContentPrompt {
  id: string
  name: string
  content: string
  description: string
  variables: string[]
  createdAt: string
  updatedAt?: string
}

// New enhanced types for multi-message prompts
export interface PromptMessage {
  role: 'user' | 'assistant'
  content: MessageContent
}

export interface MessageContent {
  type: 'text' | 'image'
  text?: string
  image?: string
}

export interface MultiMessagePrompt {
  id: string
  name: string
  description?: string
  variables: string[]
  createdAt: string
  updatedAt?: string
  version: '2.0' // Version identifier for multi-message prompts

  // Multi-message structure
  messages: PromptMessage[]
}

// Union type for backward compatibility
export type Prompt = SingleContentPrompt | MultiMessagePrompt

// Type guards
export function isMultiMessagePrompt(prompt: Prompt): prompt is MultiMessagePrompt {
  return 'version' in prompt && prompt.version === '2.0'
}

export function isSingleContentPrompt(prompt: Prompt): prompt is SingleContentPrompt {
  return 'content' in prompt
}

export interface AddPromptParams {
  name: string
  content: string
  description?: string
}

// New parameter types for multi-message prompts
export interface AddMultiMessagePromptParams {
  name: string
  description?: string
  messages: PromptMessage[]
}

export interface UpdatePromptParams {
  id: string
  name?: string
  description?: string
  messages?: PromptMessage[]
}

export interface ApplyPromptParams {
  id: string
  variables: Record<string, string>
}

export interface ApplyPromptResult {
  result: string
  messages?: PromptMessage[] // For multi-message prompts
}

export interface DeletePromptResult {
  success: boolean
  message: string
}

export interface UpdatePromptResult {
  success: boolean
  message: string
  prompt: Prompt
}

// MCP Prompt types
export interface McpPrompt {
  name: string
  description?: string
  arguments?: McpPromptArgument[]
}

export interface McpPromptArgument {
  name: string
  description?: string
  required?: boolean
}

export interface McpPromptMessage {
  role: 'user' | 'assistant'
  content: {
    type: string
    text?: string
    resource?: any
    // Other content types as needed
  }
}

export interface McpGetPromptResult {
  messages: McpPromptMessage[]
}
