// Prompts module for LSP MCP
import { Prompt, PromptHandler } from "../types/index.js";
import { debug, info } from "../logging/index.js";

// Enum for prompt names
enum PromptName {
  LSP_GUIDE = "lsp_guide",
  LANGUAGE_HELP = "language_help",
}

// Get prompt definitions for the server
export const getPromptDefinitions = (): Prompt[] => {
  return [
    {
      name: PromptName.LSP_GUIDE,
      description: "A guide on how to use the LSP (Language Server Protocol) functions available through this MCP server",
    }
  ];
};

// Define handlers for each prompt
export const getPromptHandlers = (): Record<string, PromptHandler> => {
  return {
    [PromptName.LSP_GUIDE]: async () => {
      debug(`Handling LSP guide prompt`);

      return {
        messages: [
          {
            role: "user",
            content: {
              type: "text",
              text: "How do I use the LSP functions in this server?",
            },
          },
          {
            role: "assistant",
            content: {
              type: "text",
              text: `# LSP MCP Server Guide

This server provides access to Language Server Protocol (LSP) features through MCP tools. Here's how to use them:

## Getting Started

1. First, start the LSP server with a root directory:
   \`\`\`
   start_lsp(root_dir: "/path/to/your/project")
   \`\`\`

2. Open a file for analysis:
   \`\`\`
   open_document(file_path: "/path/to/your/project/src/file.ts", language_id: "typescript")
   \`\`\`

## Available Tools

- **get_info_on_location**: Get hover information (types, documentation) at a specific position
- **get_completions**: Get code completion suggestions at a cursor position
- **get_code_actions**: Get available code refactorings and quick fixes for a selection
- **get_diagnostics**: Get errors and warnings for open files
- **open_document**: Open a file for analysis
- **close_document**: Close a file when done
- **restart_lsp_server**: Restart the LSP server if needed
- **set_log_level**: Control the server's logging verbosity

## Workflow Example

1. Start LSP: \`start_lsp(root_dir: "/my/project")\`
2. Open file: \`open_document(file_path: "/my/project/src/app.ts", language_id: "typescript")\`
3. Get diagnostics: \`get_diagnostics(file_path: "/my/project/src/app.ts")\`
4. Get hover info: \`get_info_on_location(file_path: "/my/project/src/app.ts", line: 10, character: 15, language_id: "typescript")\`
5. Get completions: \`get_completions(file_path: "/my/project/src/app.ts", line: 12, character: 8, language_id: "typescript")\`
6. Close file when done: \`close_document(file_path: "/my/project/src/app.ts")\`

Remember that line and character positions are 1-based (first line is 1, first character is 1), but LSP internally uses 0-based positions.`,
            },
          },
        ],
      };
    },
  };
};
