#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { extractTokensFromTailwind } from "./tools/extract-tailwind.js";
import { extractTokensFromCSS } from "./tools/extract-css.js";
import { extractTokensFromFigmaVariables } from "./tools/extract-figma.js";
import { extractTokensFromDTCG } from "./tools/extract-dtcg.js";
import { generateMaterial3Theme } from "./tools/generate-material3.js";
import { generateSwiftUITheme } from "./tools/generate-swiftui.js";
import { generateTailwindConfig } from "./tools/generate-tailwind.js";
import { generateCSSVariables } from "./tools/generate-css.js";
import { validateContrast } from "./tools/validate-contrast.js";
import { parseTokensFromString } from "./utils/token-validator.js";

const server = new McpServer({
  name: "design-token-bridge-mcp",
  version: "1.0.3",
});

function toolResult(text: string) {
  return { content: [{ type: "text" as const, text }] };
}

function errorResult(error: unknown) {
  const msg = error instanceof Error ? error.message : String(error);
  return { content: [{ type: "text" as const, text: JSON.stringify({ error: msg }) }], isError: true as const };
}

// --- Extraction Tools (Inputs) ---

server.registerTool(
  "extract_tokens_from_tailwind",
  {
    description:
      "Parse a Tailwind config and extract theme values into universal design tokens",
    inputSchema: {
      config: z
        .string()
        .describe(
          "The contents of a tailwind.config.js or tailwind.config.ts file"
        ),
    },
  },
  async ({ config }) => {
    try {
      const tokens = extractTokensFromTailwind(config);
      return toolResult(JSON.stringify(tokens, null, 2));
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "extract_tokens_from_css",
  {
    description:
      "Parse CSS custom properties (variables) and extract design tokens",
    inputSchema: {
      css: z.string().describe("The contents of a CSS file with custom properties"),
    },
  },
  async ({ css }) => {
    try {
      const tokens = extractTokensFromCSS(css);
      return toolResult(JSON.stringify(tokens, null, 2));
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "extract_tokens_from_figma_variables",
  {
    description:
      "Parse Figma variables export JSON and extract design tokens",
    inputSchema: {
      variables: z
        .string()
        .describe("Figma Variables REST API JSON export as a string"),
    },
  },
  async ({ variables }) => {
    try {
      const tokens = extractTokensFromFigmaVariables(variables);
      return toolResult(JSON.stringify(tokens, null, 2));
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "extract_tokens_from_json",
  {
    description:
      "Parse W3C Design Tokens Community Group (DTCG) format JSON into universal tokens",
    inputSchema: {
      json: z.string().describe("W3C DTCG format JSON string"),
    },
  },
  async ({ json }) => {
    try {
      const tokens = extractTokensFromDTCG(json);
      return toolResult(JSON.stringify(tokens, null, 2));
    } catch (e) {
      return errorResult(e);
    }
  }
);

// --- Generation Tools (Outputs) ---

server.registerTool(
  "generate_material3_theme",
  {
    description:
      "Generate Kotlin Jetpack Compose Material 3 theme files from universal design tokens",
    inputSchema: {
      tokens: z.string().describe("Universal design tokens JSON string"),
    },
  },
  async ({ tokens }) => {
    try {
      const parsed = parseTokensFromString(tokens);
      if (!parsed.valid) {
        return toolResult(JSON.stringify({ error: "Invalid tokens", details: parsed.errors }));
      }
      const kotlin = generateMaterial3Theme(parsed.tokens!);
      return toolResult(kotlin);
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "generate_swiftui_theme",
  {
    description:
      "Generate SwiftUI theme files from universal design tokens, with optional Liquid Glass support",
    inputSchema: {
      tokens: z.string().describe("Universal design tokens JSON string"),
      liquidGlass: z
        .boolean()
        .optional()
        .default(false)
        .describe("Include iOS 26+ Liquid Glass modifiers"),
    },
  },
  async ({ tokens, liquidGlass }) => {
    try {
      const parsed = parseTokensFromString(tokens);
      if (!parsed.valid) {
        return toolResult(JSON.stringify({ error: "Invalid tokens", details: parsed.errors }));
      }
      const swift = generateSwiftUITheme(parsed.tokens!, liquidGlass);
      return toolResult(swift);
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "generate_tailwind_config",
  {
    description:
      "Generate a tailwind.config.js theme from universal design tokens",
    inputSchema: {
      tokens: z.string().describe("Universal design tokens JSON string"),
      format: z
        .enum(["esm", "cjs"])
        .optional()
        .default("esm")
        .describe("Output format: ES modules or CommonJS"),
    },
  },
  async ({ tokens, format }) => {
    try {
      const parsed = parseTokensFromString(tokens);
      if (!parsed.valid) {
        return toolResult(JSON.stringify({ error: "Invalid tokens", details: parsed.errors }));
      }
      const config = generateTailwindConfig(parsed.tokens!, format);
      return toolResult(config);
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "generate_css_variables",
  {
    description:
      "Generate CSS custom properties from universal design tokens with light/dark mode support",
    inputSchema: {
      tokens: z.string().describe("Universal design tokens JSON string"),
      darkTokens: z
        .string()
        .optional()
        .describe(
          "Optional dark mode universal design tokens JSON string"
        ),
    },
  },
  async ({ tokens, darkTokens }) => {
    try {
      const parsed = parseTokensFromString(tokens);
      if (!parsed.valid) {
        return toolResult(JSON.stringify({ error: "Invalid tokens", details: parsed.errors }));
      }
      let darkParsed;
      if (darkTokens) {
        darkParsed = parseTokensFromString(darkTokens);
        if (!darkParsed.valid) {
          return toolResult(JSON.stringify({ error: "Invalid dark tokens", details: darkParsed.errors }));
        }
      }
      const css = generateCSSVariables(parsed.tokens!, darkParsed?.tokens);
      return toolResult(css);
    } catch (e) {
      return errorResult(e);
    }
  }
);

server.registerTool(
  "validate_contrast",
  {
    description:
      "Check color combinations in design tokens for WCAG AA/AAA accessibility compliance",
    inputSchema: {
      tokens: z.string().describe("Universal design tokens JSON string"),
      level: z
        .enum(["AA", "AAA"])
        .optional()
        .default("AA")
        .describe("WCAG compliance level to check"),
    },
  },
  async ({ tokens, level }) => {
    try {
      const parsed = parseTokensFromString(tokens);
      if (!parsed.valid) {
        return toolResult(JSON.stringify({ error: "Invalid tokens", details: parsed.errors }));
      }
      const report = validateContrast(parsed.tokens!, level);
      return toolResult(JSON.stringify(report, null, 2));
    } catch (e) {
      return errorResult(e);
    }
  }
);

// --- Start Server ---

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("design-token-bridge-mcp running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
