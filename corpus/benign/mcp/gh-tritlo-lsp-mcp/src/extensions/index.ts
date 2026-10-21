// Extensions management system for LSP-MCP
import * as fs from "fs/promises";
import * as path from "path";
import { debug, info, warning, logError } from "../logging/index.js";
import {
  ToolHandler,
  ResourceHandler,
  SubscriptionHandler,
  UnsubscriptionHandler,
  PromptHandler,
  Prompt,
  ToolInput
} from "../types/index.js";

// Type definitions for extension structure
interface Extension {
  getToolHandlers?: () => Record<string, { schema: any, handler: ToolHandler }>;
  getToolDefinitions?: () => Array<{
    name: string;
    description: string;
    inputSchema: ToolInput;
  }>;
  getResourceHandlers?: () => Record<string, ResourceHandler>;
  getSubscriptionHandlers?: () => Record<string, SubscriptionHandler>;
  getUnsubscriptionHandlers?: () => Record<string, UnsubscriptionHandler>;
  getResourceTemplates?: () => Array<{
    name: string;
    scheme: string;
    pattern: string;
    description: string;
    subscribe: boolean;
  }>;
  getPromptDefinitions?: () => Prompt[];
  getPromptHandlers?: () => Record<string, PromptHandler>;
}

// Track active extensions
const activeExtensions: Record<string, Extension> = {};

// Import an extension module by language ID
async function importExtension(languageId: string): Promise<Extension | null> {
  try {
    // Normalize language ID to use only alphanumeric characters and hyphens
    const safeLanguageId = languageId.replace(/[^a-zA-Z0-9-]/g, '');

    // Check if extension file exists
    const extensionPath = path.resolve(process.cwd(), 'dist', 'src', 'extensions', `${safeLanguageId}.js`);
    try {
      await fs.access(extensionPath);
    } catch (error) {
      info(`No extension found for language: ${languageId}`);
      return null;
    }

    // Import the extension module
    const extensionModule = await import(`./${safeLanguageId}.js`);
    return extensionModule as Extension;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logError(`Error importing extension for ${languageId}: ${errorMessage}`);
    return null;
  }
}

// Activate an extension by language ID
export async function activateExtension(languageId: string): Promise<{success: boolean}> {
  try {
    // Check if already active
    if (activeExtensions[languageId]) {
      info(`Extension for ${languageId} is already active`);
      return { success: true };
    }

    // Import the extension
    const extension = await importExtension(languageId);
    if (!extension) {
      info(`No extension found for language: ${languageId}`);
      return { success: false };
    }

    // Store the active extension
    activeExtensions[languageId] = extension;
    info(`Activated extension for language: ${languageId}`);
    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logError(`Error activating extension for ${languageId}: ${errorMessage}`);
    return { success: false };
  }
}

// Deactivate an extension by language ID
export function deactivateExtension(languageId: string): {success: boolean} {
  try {
    // Check if active
    if (!activeExtensions[languageId]) {
      info(`No active extension found for language: ${languageId}`);
      return { success: false };
    }

    // Remove the extension
    delete activeExtensions[languageId];
    info(`Deactivated extension for language: ${languageId}`);

    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    logError(`Error deactivating extension for ${languageId}: ${errorMessage}`);
    return { success: false };
  }
}

// List all active extensions
export function listActiveExtensions(): string[] {
  return Object.keys(activeExtensions);
}

// Get all tool handlers from active extensions
export function getExtensionToolHandlers(): Record<string, { schema: any, handler: ToolHandler }> {
  const handlers: Record<string, { schema: any, handler: ToolHandler }> = {};

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getToolHandlers) {
      const extensionHandlers = extension.getToolHandlers();
      for (const [name, handler] of Object.entries(extensionHandlers)) {
        handlers[`${languageId}.${name}`] = handler;
      }
    }
  }

  return handlers;
}

// Get all tool definitions from active extensions
export function getExtensionToolDefinitions(): Array<{
  name: string;
  description: string;
  inputSchema: ToolInput;
}> {
  const definitions: Array<{
    name: string;
    description: string;
    inputSchema: ToolInput;
  }> = [];

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getToolDefinitions) {
      const extensionDefinitions = extension.getToolDefinitions();
      for (const def of extensionDefinitions) {
        definitions.push({
          name: `${languageId}.${def.name}`,
          description: def.description,
          inputSchema: def.inputSchema
        });
      }
    }
  }

  return definitions;
}

// Get all resource handlers from active extensions
export function getExtensionResourceHandlers(): Record<string, ResourceHandler> {
  const handlers: Record<string, ResourceHandler> = {};

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getResourceHandlers) {
      const extensionHandlers = extension.getResourceHandlers();
      for (const [scheme, handler] of Object.entries(extensionHandlers)) {
        handlers[`${languageId}.${scheme}`] = handler;
      }
    }
  }

  return handlers;
}

// Get all subscription handlers from active extensions
export function getExtensionSubscriptionHandlers(): Record<string, SubscriptionHandler> {
  const handlers: Record<string, SubscriptionHandler> = {};

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getSubscriptionHandlers) {
      const extensionHandlers = extension.getSubscriptionHandlers();
      for (const [scheme, handler] of Object.entries(extensionHandlers)) {
        handlers[`${languageId}.${scheme}`] = handler;
      }
    }
  }

  return handlers;
}

// Get all unsubscription handlers from active extensions
export function getExtensionUnsubscriptionHandlers(): Record<string, UnsubscriptionHandler> {
  const handlers: Record<string, UnsubscriptionHandler> = {};

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getUnsubscriptionHandlers) {
      const extensionHandlers = extension.getUnsubscriptionHandlers();
      for (const [scheme, handler] of Object.entries(extensionHandlers)) {
        handlers[`${languageId}.${scheme}`] = handler;
      }
    }
  }

  return handlers;
}

// Get all resource templates from active extensions
export function getExtensionResourceTemplates(): Array<{
  name: string;
  scheme: string;
  pattern: string;
  description: string;
  subscribe: boolean;
}> {
  const templates: Array<{
    name: string;
    scheme: string;
    pattern: string;
    description: string;
    subscribe: boolean;
  }> = [];

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getResourceTemplates) {
      const extensionTemplates = extension.getResourceTemplates();
      for (const template of extensionTemplates) {
        templates.push({
          name: `${languageId}.${template.name}`,
          scheme: `${languageId}.${template.scheme}`,
          pattern: template.pattern,
          description: template.description,
          subscribe: template.subscribe
        });
      }
    }
  }

  return templates;
}

// Get all prompt definitions from active extensions
export function getExtensionPromptDefinitions(): Prompt[] {
  const definitions: Prompt[] = [];

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getPromptDefinitions) {
      const extensionDefinitions = extension.getPromptDefinitions();
      for (const def of extensionDefinitions) {
        definitions.push({
          name: `${languageId}.${def.name}`,
          description: def.description,
          arguments: def.arguments
        });
      }
    }
  }

  return definitions;
}

// Get all prompt handlers from active extensions
export function getExtensionPromptHandlers(): Record<string, PromptHandler> {
  const handlers: Record<string, PromptHandler> = {};

  for (const [languageId, extension] of Object.entries(activeExtensions)) {
    if (extension.getPromptHandlers) {
      const extensionHandlers = extension.getPromptHandlers();
      for (const [name, handler] of Object.entries(extensionHandlers)) {
        handlers[`${languageId}.${name}`] = handler;
      }
    }
  }

  return handlers;
}
