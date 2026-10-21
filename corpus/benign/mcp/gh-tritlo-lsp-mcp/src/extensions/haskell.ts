// Haskell extension for LSP-MCP
import {
  ToolHandler,
  ResourceHandler,
  SubscriptionHandler,
  UnsubscriptionHandler,
  PromptHandler,
  Prompt,
  ToolInput
} from "../types/index.js";

// This extension provides no additional tools, resources, or prompts
// It's just a simple example of the extension structure

// Export tool handlers
export const getToolHandlers = (): Record<string, { schema: any, handler: ToolHandler }> => {
  return {};
};

// Export tool definitions
export const getToolDefinitions = (): Array<{
  name: string;
  description: string;
  inputSchema: ToolInput;
}> => {
  return [];
};

// Export resource handlers
export const getResourceHandlers = (): Record<string, ResourceHandler> => {
  return {};
};

// Export subscription handlers
export const getSubscriptionHandlers = (): Record<string, SubscriptionHandler> => {
  return {};
};

// Export unsubscription handlers
export const getUnsubscriptionHandlers = (): Record<string, UnsubscriptionHandler> => {
  return {};
};

// Export resource templates
export const getResourceTemplates = (): Array<{
  name: string;
  scheme: string;
  pattern: string;
  description: string;
  subscribe: boolean;
}> => {
  return [];
};

// Export prompt definitions
export const getPromptDefinitions = (): Prompt[] => {
  return [
    {
      name: "typed-hole-use",
      description: "Guide on using typed-holes in Haskell to explore type information and function possibilities"
    }
  ];
};

// Export prompt handlers
export const getPromptHandlers = (): Record<string, PromptHandler> => {
  return {
    "typed-hole-use": async (args?: Record<string,string>) => {
      return {
        messages: [
          {
            role: "user",
            content: {
              type: "text",
              text: `
              Please use a typed-hole to synthesize replacement code for this expression.

              You do this by replacing the expression with a hole \`_mcp_typed_hole\`
              and calling the code action on the location of the hole.

              Make sure you call it on the hole, i.e. the line should be the actual line of the hole
              and the column should one

              Then, looking at the labels that the code-action returns,
              you can see the identifiers that can be used to fill in the hole.
              `
            }
          },
        ]
      };
    }
  };
};
