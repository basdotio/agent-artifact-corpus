import fs from 'fs/promises'
import path from 'path'
import { NotFoundError } from '../utils/mcp-error.js'

export class FileSystemService {
  async readJSONFile<T>(filePath: string): Promise<T> {
    try {
      const content = await fs.readFile(filePath, 'utf8')
      return JSON.parse(content) as T
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        throw new NotFoundError(`File not found: ${filePath}`)
      }
      throw new Error(`Failed to read file: ${(error as Error).message}`)
    }
  }

  async writeJSONFile<T>(filePath: string, data: T): Promise<void> {
    try {
      await fs.writeFile(
        filePath,
        JSON.stringify(data, null, 2),
        'utf8'
      )
    } catch (error) {
      throw new Error(`Failed to write file: ${(error as Error).message}`)
    }
  }

  async deleteFile(filePath: string): Promise<void> {
    try {
      await fs.unlink(filePath)
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        throw new NotFoundError(`File not found: ${filePath}`)
      }
      throw new Error(`Failed to delete file: ${(error as Error).message}`)
    }
  }

  async listFiles(directory: string, extension: string): Promise<string[]> {
    try {
      const files = await fs.readdir(directory)
      return files.filter(file => file.endsWith(extension))
    } catch (error) {
      throw new Error(`Failed to list files: ${(error as Error).message}`)
    }
  }
  
  async ensureDirectory(directory: string): Promise<void> {
    try {
      await fs.mkdir(directory, { recursive: true })
    } catch (error) {
      throw new Error(`Failed to create directory: ${(error as Error).message}`)
    }
  }
}
