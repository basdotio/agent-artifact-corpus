import { Prompt, MultiMessagePrompt, SingleContentPrompt, PromptMessage } from '../types/index.js'

export class PromptValidationUtils {
  static isValidPromptStructure(data: any): data is Prompt {
    if (data.version === '2.0') {
      return this.isValidMultiMessagePrompt(data)
    }
    return this.isValidSingleContentPrompt(data)
  }

  private static isValidMultiMessagePrompt(data: any): data is MultiMessagePrompt {
    return (
      typeof data.id === 'string' &&
      typeof data.name === 'string' &&
      Array.isArray(data.variables) &&
      typeof data.createdAt === 'string' &&
      data.version === '2.0' &&
      Array.isArray(data.messages) &&
      data.messages.every(this.isValidMessage) &&
      data.messages.length > 0
    )
  }

  private static isValidSingleContentPrompt(data: any): data is SingleContentPrompt {
    return (
      typeof data.id === 'string' &&
      typeof data.name === 'string' &&
      typeof data.content === 'string' &&
      typeof data.description === 'string' &&
      Array.isArray(data.variables) &&
      typeof data.createdAt === 'string'
    )
  }

  private static isValidMessage(message: any): message is PromptMessage {
    if (!['user', 'assistant'].includes(message.role)) {
      return false
    }

    if (!message.content || typeof message.content.type !== 'string') {
      return false
    }

    const { type, text, image } = message.content

    if (type === 'text') {
      return typeof text === 'string'
    }

    if (type === 'image') {
      return typeof image === 'string'
    }

    return false
  }

  static validateMessageContent(content: any): boolean {
    if (!content || typeof content.type !== 'string') {
      return false
    }

    if (content.type === 'text') {
      return typeof content.text === 'string' && content.text.length > 0
    }

    if (content.type === 'image') {
      return typeof content.image === 'string' && content.image.length > 0
    }

    return false
  }

  static validateMessages(messages: any[]): boolean {
    if (!Array.isArray(messages) || messages.length === 0) {
      return false
    }

    return messages.every(this.isValidMessage)
  }
}