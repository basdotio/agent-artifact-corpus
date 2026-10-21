/**
 * Secure file reading service for sober_thinking tool
 */

import { promises as fs } from 'node:fs';
import { join, resolve } from 'node:path';
import { logger } from '../utils/logger.js';
import { validateFilePath, maskEnvValue } from '../utils/security.js';
import type { FileContent } from '../types/app-types.js';
import { ToolExecutionError } from '../types/app-types.js';
import { TIMEOUTS, SECURITY } from '../config/constants.js';

export class FileReaderService {
  private readonly allowedFiles = [
    'README.md',
    '.env',
    'CHANGELOG',
    'CHANGELOG.md',
    'package.json',
    'tsconfig.json'
  ] as const;
  
  /**
   * Read project files safely for sober_thinking tool
   */
  async readProjectFiles(): Promise<string> {
    const startTime = Date.now();
    
    try {
      const cwd = process.cwd();
      const files = this.allowedFiles.map(filename => join(cwd, filename));
      
      logger.debug('Reading project files', { files: this.allowedFiles });
      
      // Read all files in parallel with timeout protection
      const results = await Promise.all(
        files.map(async (filePath) => {
          const filename = filePath.split(/[\\/]/).pop() || 'unknown';
          
          try {
            validateFilePath(filePath);
            
            if (filename === '.env') {
              return await this.readEnvFile(filePath, filename);
            } else {
              return await this.readRegularFile(filePath, filename);
            }
          } catch (error) {
            logger.warn(`Failed to read file: ${filename}`, { error: error instanceof Error ? error.message : 'Unknown error' });
            return `## ${filename}\n(File not found or unreadable)\n\n`;
          }
        })
      );
      
      const combinedContent = results.join('\n');
      const duration = Date.now() - startTime;
      
      logger.toolCall('sober_thinking', true, duration);
      logger.info('Project files read successfully', { 
        filesCount: this.allowedFiles.length,
        durationMs: duration,
        contentLength: combinedContent.length
      });
      
      return combinedContent;
      
    } catch (error) {
      const duration = Date.now() - startTime;
      logger.toolCall('sober_thinking', false, duration);
      
      if (error instanceof ToolExecutionError) {
        throw error;
      }
      
      const message = error instanceof Error ? error.message : 'Unknown error';
      throw new ToolExecutionError('sober_thinking', `Failed to read project files: ${message}`);
    }
  }
  
  /**
   * Read a regular file with security checks
   */
  private async readRegularFile(filePath: string, filename: string): Promise<string> {
    const absolutePath = resolve(filePath);
    
    try {
      // Check file size first to prevent reading huge files
      const stats = await fs.stat(absolutePath);
      if (stats.size > SECURITY.MAX_FILE_SIZE) {
        logger.warn(`File ${filename} too large`, { size: stats.size, maxSize: SECURITY.MAX_FILE_SIZE });
        return `## ${filename}\n(File too large to read - ${Math.round(stats.size / 1024)}KB)\n\n`;
      }
      
      // Read with timeout protection
      const content = await this.readFileWithTimeout(absolutePath);
      
      return `## ${filename}\n${content}\n\n`;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.warn(`Failed to read regular file: ${filename}`, { error: message });
      return `## ${filename}\n(Error reading file: ${message})\n\n`;
    }
  }
  
  /**
   * Read .env file with value masking for security
   */
  private async readEnvFile(filePath: string, filename: string): Promise<string> {
    const absolutePath = resolve(filePath);
    
    try {
      const rawContent = await this.readFileWithTimeout(absolutePath);
      
      // Mask sensitive values line by line
      const maskedContent = rawContent
        .split('\n')
        .map(line => maskEnvValue(line))
        .join('\n');
      
      logger.debug('Environment file read and masked', { 
        originalLines: rawContent.split('\n').length,
        maskedLines: maskedContent.split('\n').length
      });
      
      return `## ${filename}\n${maskedContent}\n\n`;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      logger.warn(`Failed to read env file: ${filename}`, { error: message });
      return `## ${filename}\n(Error reading environment file: ${message})\n\n`;
    }
  }
  
  /**
   * Read file with timeout protection
   */
  private async readFileWithTimeout(filePath: string): Promise<string> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      controller.abort();
    }, TIMEOUTS.FILE_READ_TIMEOUT_MS);
    
    try {
      // Note: fs.readFile doesn't support AbortSignal in older Node versions
      // For now, we'll use a Promise.race approach
      const readPromise = fs.readFile(filePath, 'utf8');
      const timeoutPromise = new Promise<never>((_, reject) => {
        controller.signal.addEventListener('abort', () => {
          reject(new Error('File read timeout'));
        });
      });
      
      const content = await Promise.race([readPromise, timeoutPromise]);
      clearTimeout(timeoutId);
      
      return content;
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }
  
  /**
   * Check if a file exists and is readable
   */
  async isFileAccessible(filename: string): Promise<boolean> {
    try {
      const filePath = join(process.cwd(), filename);
      validateFilePath(filePath);
      
      await fs.access(filePath, fs.constants.R_OK);
      return true;
    } catch {
      return false;
    }
  }
  
  /**
   * Get file information without reading content
   */
  async getFileInfo(filename: string): Promise<FileContent | null> {
    try {
      const filePath = join(process.cwd(), filename);
      validateFilePath(filePath);
      
      const stats = await fs.stat(filePath);
      
      return {
        filename,
        content: '', // Not read for info-only requests
        size: stats.size,
        lastModified: stats.mtime
      };
    } catch {
      return null;
    }
  }
}

// Export singleton instance
export const fileReaderService = new FileReaderService();