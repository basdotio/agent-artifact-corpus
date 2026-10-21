import path from 'path'
import { v4 as uuidv4 } from 'uuid'
import { PROMPTS_CONFIG } from '../config/index.js'
import {
  type Prompt,
  type SingleContentPrompt,
  type MultiMessagePrompt,
  type PromptMessage,
  type AddPromptParams,
  type AddMultiMessagePromptParams,
  type ApplyPromptParams,
  type ApplyPromptResult,
  type DeletePromptResult,
  type UpdatePromptParams,
  type UpdatePromptResult,
  isMultiMessagePrompt,
  isSingleContentPrompt
} from '../types/index.js'
import { FileSystemService } from './filesystem.service.js'
import { NotFoundError, ValidationError } from '../utils/mcp-error.js'
import { PromptValidationUtils } from '../utils/prompt-validation.js'

export class PromptsService {
  private readonly promptsDir: string
  private readonly fileSystemService: FileSystemService

  constructor() {
    this.promptsDir = PROMPTS_CONFIG.promptsDir
    this.fileSystemService = new FileSystemService()
    this.ensurePromptsDirectory()
  }

  private async ensurePromptsDirectory(): Promise<void> {
    try {
      await this.fileSystemService.ensureDirectory(this.promptsDir)
    } catch (error) {
      console.error('Failed to create prompts directory:', error)
      throw error
    }
  }

  private extractVariables(content: string): string[] {
    const variableRegex = /{{([^{}]+)}}/g
    const matches = content.match(variableRegex) || []
    return [...new Set(matches.map(match => match.slice(2, -2)))]
  }

  private extractVariablesFromMessages(messages: PromptMessage[]): string[] {
    const variables = new Set<string>()

    for (const message of messages) {
      if (message.content.type === 'text' && message.content.text) {
        const messageVars = this.extractVariables(message.content.text)
        messageVars.forEach(variable => variables.add(variable))
      }
    }

    return Array.from(variables)
  }

  async addPrompt(params: AddPromptParams): Promise<Prompt> {
    if (!params.name || !params.name.trim()) {
      throw new ValidationError('Prompt name is required')
    }

    if (!params.content || !params.content.trim()) {
      throw new ValidationError('Prompt content is required')
    }

    const id = `prompt-${uuidv4().slice(0, 8)}`
    const variables = this.extractVariables(params.content)

    const now = new Date().toISOString()
    const prompt: SingleContentPrompt = {
      id,
      name: params.name.trim(),
      content: params.content,
      description: params.description?.trim() || '',
      variables,
      createdAt: now,
      updatedAt: now
    }

    try {
      await this.fileSystemService.writeJSONFile(
        path.join(this.promptsDir, `${id}.json`),
        prompt
      )
      return prompt
    } catch (error) {
      console.error('Failed to save prompt:', error)
      throw error
    }
  }

  async addMultiMessagePrompt(params: AddMultiMessagePromptParams): Promise<MultiMessagePrompt> {
    if (!params.name || !params.name.trim()) {
      throw new ValidationError('Prompt name is required')
    }

    if (!params.messages || !Array.isArray(params.messages) || params.messages.length === 0) {
      throw new ValidationError('At least one message is required')
    }

    if (!PromptValidationUtils.validateMessages(params.messages)) {
      throw new ValidationError('Invalid message structure')
    }

    const id = `prompt-${uuidv4().slice(0, 8)}`
    const variables = this.extractVariablesFromMessages(params.messages)

    const prompt: MultiMessagePrompt = {
      id,
      name: params.name.trim(),
      description: params.description?.trim() || '',
      variables,
      createdAt: new Date().toISOString(),
      version: '2.0',
      messages: params.messages
    }

    try {
      await this.fileSystemService.writeJSONFile(
        path.join(this.promptsDir, `${id}.json`),
        prompt
      )
      return prompt
    } catch (error) {
      console.error('Failed to save multi-message prompt:', error)
      throw error
    }
  }

  async getPrompt(id: string): Promise<Prompt> {
    if (!id || !id.trim()) {
      throw new ValidationError('Prompt ID is required')
    }

    try {
      const filePath = path.join(this.promptsDir, `${id}.json`)
      return await this.fileSystemService.readJSONFile<Prompt>(filePath)
    } catch (error) {
      if (error instanceof Error && error.message.includes('not found')) {
        throw new NotFoundError(`Prompt not found: ${id}`)
      }
      throw error
    }
  }

  async listPrompts(): Promise<Prompt[]> {
    try {
      const files = await this.fileSystemService.listFiles(this.promptsDir, '.json')
      
      const prompts: Prompt[] = []
      
      for (const file of files) {
        try {
          const filePath = path.join(this.promptsDir, file)
          const prompt = await this.fileSystemService.readJSONFile<Prompt>(filePath)
          prompts.push(prompt)
        } catch (error) {
          console.error(`Error reading prompt file ${file}:`, error)
          // Continue with other files even if one fails
        }
      }
      
      return prompts
    } catch (error) {
      console.error('Failed to list prompts:', error)
      throw error
    }
  }

  async deletePrompt(id: string): Promise<DeletePromptResult> {
    if (!id || !id.trim()) {
      throw new ValidationError('Prompt ID is required')
    }

    try {
      // First check if the prompt exists
      await this.getPrompt(id)
      
      // If it exists, delete it
      const filePath = path.join(this.promptsDir, `${id}.json`)
      await this.fileSystemService.deleteFile(filePath)
      
      return {
        success: true,
        message: `Prompt ${id} deleted successfully`
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes('not found')) {
        throw new NotFoundError(`Prompt not found: ${id}`)
      }
      console.error('Failed to delete prompt:', error)
      throw error
    }
  }

  async updatePrompt(params: UpdatePromptParams): Promise<UpdatePromptResult> {
    if (!params.id || !params.id.trim()) {
      throw new ValidationError('Prompt ID is required')
    }

    // At least one field to update must be provided
    if (!params.name && !params.description && !params.messages) {
      throw new ValidationError('At least one field to update must be provided')
    }

    try {
      // First get the existing prompt
      const existingPrompt = await this.getPrompt(params.id)
      
      let updatedPrompt: Prompt

      if (isMultiMessagePrompt(existingPrompt)) {
        // Update existing multi-message prompt
        updatedPrompt = {
          ...existingPrompt,
          ...(params.name && { name: params.name.trim() }),
          ...(params.description !== undefined && { description: params.description.trim() || '' }),
          ...(params.messages && {
            messages: params.messages,
            variables: this.extractVariablesFromMessages(params.messages)
          }),
          updatedAt: new Date().toISOString()
        }
      } else {
        // Convert single content prompt to multi-message if messages are provided
        if (params.messages) {
          updatedPrompt = {
            id: existingPrompt.id,
            name: params.name?.trim() || existingPrompt.name,
            description: params.description !== undefined ? (params.description.trim() || '') : existingPrompt.description,
            variables: this.extractVariablesFromMessages(params.messages),
            createdAt: existingPrompt.createdAt,
            updatedAt: new Date().toISOString(),
            version: '2.0',
            messages: params.messages
          }
        } else {
          // Keep as single content format
          updatedPrompt = {
            ...existingPrompt,
            ...(params.name && { name: params.name.trim() }),
            ...(params.description !== undefined && { description: params.description.trim() || '' }),
            updatedAt: new Date().toISOString()
          }
        }
      }
      
      // Save the updated prompt
      const filePath = path.join(this.promptsDir, `${params.id}.json`)
      await this.fileSystemService.writeJSONFile(filePath, updatedPrompt)
      
      return {
        success: true,
        message: `Prompt ${params.id} updated successfully`,
        prompt: updatedPrompt
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes('not found')) {
        throw new NotFoundError(`Prompt not found: ${params.id}`)
      }
      console.error('Failed to update prompt:', error)
      throw error
    }
  }

  async applyPrompt(params: ApplyPromptParams): Promise<ApplyPromptResult> {
    if (!params.id || !params.id.trim()) {
      throw new ValidationError('Prompt ID is required')
    }

    if (!params.variables || typeof params.variables !== 'object') {
      throw new ValidationError('Variables must be provided as an object')
    }

    try {
      const prompt = await this.getPrompt(params.id)
      
      // Check if all required variables are provided
      const missingVariables = prompt.variables.filter(
        variable => !(variable in params.variables)
      )
      
      if (missingVariables.length > 0) {
        throw new ValidationError(
          `Missing required variables: ${missingVariables.join(', ')}`
        )
      }
      
      if (isMultiMessagePrompt(prompt)) {
        // Handle multi-message prompts
        const appliedMessages = prompt.messages.map(message => ({
          ...message,
          content: {
            ...message.content,
            ...(message.content.type === 'text' && message.content.text && {
              text: this.replaceVariables(message.content.text, params.variables)
            })
          }
        }))

        return {
          result: JSON.stringify(appliedMessages, null, 2),
          messages: appliedMessages
        }
      } else {
        // Handle single content prompts
        const result = this.replaceVariables(prompt.content, params.variables)
        return { result }
      }
    } catch (error) {
      console.error('Failed to apply prompt:', error)
      throw error
    }
  }

  private replaceVariables(text: string, variables: Record<string, string>): string {
    return text.replace(/{{([^{}]+)}}/g, (match, variable) => {
      return variables[variable.trim()] || match
    })
  }
}
