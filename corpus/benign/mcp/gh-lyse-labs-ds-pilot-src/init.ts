import { existsSync, mkdirSync, readFileSync, writeFileSync, unlinkSync } from "fs";
import { resolve } from "path";
import { globSync } from "glob";

const CLAUDE_MD_SECTION = `
## Design System

Before creating a new component, use the \`search_components\` tool to check if a similar component already exists.
Use \`get_component_props\` to inspect a component's props, types, and defaults before using it.
Use \`list_tokens\` and \`get_token\` to find design tokens instead of hardcoding colors, spacing, or typography values.
`;

const SKILL_CONTENT = `---
name: using-ds-pilot
description: "Use when creating or modifying UI components — always check the design system for existing components and tokens before writing code"
---

# ds-pilot: Design System Tools

Before writing UI code, use the design system MCP tools:

- **Before creating a component** — call \`search_components\` to check if a similar component already exists. If one does, inform the user and suggest using it instead of creating a duplicate.
- **Before modifying a component** — call \`get_component_props\` to understand its current props, defaults, and variants.
- **Before hardcoding a value** (color, spacing, font size, etc.) — call \`list_tokens\` or \`get_token\` to find the corresponding design token.
`;

interface InitResult {
  componentsDir: string;
  tokensFile: string | null;
  skillInstalled: boolean;
  claudeMdUpdated: boolean;
  claudeMdCleaned: boolean;
  settingsUpdated: boolean;
}

export function runInit(cwd: string = process.cwd()): InitResult {
  const componentsDir = detectComponentsDir(cwd);
  const tokensFile = detectTokensFile(cwd);

  const settingsUpdated = writeSettings(cwd, componentsDir, tokensFile);
  const skillInstalled = installSkill(cwd);
  const claudeMdCleaned = skillInstalled ? cleanClaudeMdSection(cwd) : false;
  const claudeMdUpdated = skillInstalled ? false : updateClaudeMd(cwd);

  return { componentsDir, tokensFile, skillInstalled, claudeMdUpdated, claudeMdCleaned, settingsUpdated };
}

function detectComponentsDir(cwd: string): string {
  // Find the directory with the most component files
  const componentFiles = globSync("**/*.{vue,tsx,jsx}", {
    cwd,
    ignore: ["**/node_modules/**", "**/dist/**", "**/.nuxt/**", "**/.next/**", "**/.output/**"],
    absolute: false,
  });

  if (componentFiles.length === 0) return "./src/components";

  // Count files per top-level directory path
  const dirCounts = new Map<string, number>();
  for (const file of componentFiles) {
    const parts = file.split("/");
    // Find the deepest "components" directory in the path
    const compIdx = parts.lastIndexOf("components");
    if (compIdx !== -1) {
      const dir = parts.slice(0, compIdx + 1).join("/");
      dirCounts.set(dir, (dirCounts.get(dir) || 0) + 1);
    }
  }

  if (dirCounts.size === 0) {
    // No "components" directory found, use the most common parent
    for (const file of componentFiles) {
      const dir = file.split("/").slice(0, -1).join("/");
      if (dir) dirCounts.set(dir, (dirCounts.get(dir) || 0) + 1);
    }
  }

  if (dirCounts.size === 0) return "./src/components";

  // Return the directory with the most component files
  const bestDir = [...dirCounts.entries()].sort((a, b) => b[1] - a[1])[0][0];
  return `./${bestDir}`;
}

function detectTokensFile(cwd: string): string | null {
  const candidates = [
    "tokens.json",
    "design-tokens.json",
    "src/tokens.json",
    "src/theme/tokens.json",
    "styles/tokens.json",
    "tokens.css",
    "src/tokens.css",
  ];

  for (const file of candidates) {
    if (existsSync(resolve(cwd, file))) return `./${file}`;
  }

  const found = globSync("**/tokens.{json,css}", {
    cwd,
    ignore: ["node_modules/**"],
    absolute: false,
  });

  return found.length > 0 ? `./${found[0]}` : null;
}

function writeSettings(cwd: string, componentsDir: string, tokensFile: string | null): boolean {
  const mcpFile = resolve(cwd, ".mcp.json");

  let config: Record<string, unknown> = {};
  if (existsSync(mcpFile)) {
    try {
      config = JSON.parse(readFileSync(mcpFile, "utf-8"));
    } catch {
      console.warn("Warning: existing .mcp.json contains invalid JSON. Overwriting.");
    }
  }

  const mcpServers = (config.mcpServers as Record<string, unknown>) || {};
  const args = ["-y", "@lyse-labs/ds-pilot", "serve", "--components", componentsDir];
  if (tokensFile) {
    args.push("--tokens", tokensFile);
  }

  mcpServers["ds-pilot"] = {
    command: "npx",
    args,
  };

  config.mcpServers = mcpServers;
  writeFileSync(mcpFile, JSON.stringify(config, null, 2) + "\n");
  return true;
}

function installSkill(cwd: string): boolean {
  try {
    const skillDir = resolve(cwd, ".claude", "skills", "using-ds-pilot");
    mkdirSync(skillDir, { recursive: true });
    writeFileSync(resolve(skillDir, "SKILL.md"), SKILL_CONTENT);
    return true;
  } catch {
    return false;
  }
}

function cleanClaudeMdSection(cwd: string): boolean {
  const claudeMdPath = resolve(cwd, "CLAUDE.md");

  if (!existsSync(claudeMdPath)) return false;

  const content = readFileSync(claudeMdPath, "utf-8");
  if (!content.includes(CLAUDE_MD_SECTION)) return false;

  const cleaned = content.replace(CLAUDE_MD_SECTION, "");
  if (cleaned.trim() === "") {
    unlinkSync(claudeMdPath);
  } else {
    writeFileSync(claudeMdPath, cleaned);
  }
  return true;
}

function updateClaudeMd(cwd: string): boolean {
  const claudeMdPath = resolve(cwd, "CLAUDE.md");

  let content = "";
  if (existsSync(claudeMdPath)) {
    content = readFileSync(claudeMdPath, "utf-8");
    if (content.includes("search_components")) {
      return false;
    }
  }

  content += CLAUDE_MD_SECTION;
  writeFileSync(claudeMdPath, content);
  return true;
}
