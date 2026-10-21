#!/usr/bin/env node

import { Command } from "commander";
import { resolve } from "path";
import { scanComponents } from "./scanner/components.js";
import { parseTokens } from "./scanner/tokens.js";
import { searchComponents, getComponentWithProps, listTokens, getToken } from "./tools.js";
import { startMCPServer } from "./mcp.js";
import { runInit } from "./init.js";

const program = new Command();

program
  .name("ds-pilot")
  .description("Expose your design system to AI agents via MCP")
  .version("0.2.2");

program
  .command("init")
  .description("Configure ds-pilot for your project (MCP + skill)")
  .action(() => {
    const result = runInit();
    console.log("ds-pilot initialized:");
    console.log(`  Components: ${result.componentsDir}`);
    console.log(`  Tokens: ${result.tokensFile || "not found"}`);
    console.log(`  Skill: ${result.skillInstalled ? "installed" : "failed (CLAUDE.md fallback used)"}`);
    if (result.claudeMdCleaned) console.log(`  CLAUDE.md: old section removed`);
    console.log(`  MCP: ${result.settingsUpdated ? "configured" : "already configured"}`);
  });

program
  .command("serve")
  .description("Start the MCP server")
  .requiredOption("--components <dir>", "Components directory")
  .option("--tokens <file>", "Tokens file (JSON or CSS)")
  .action(async (opts) => {
    await startMCPServer({
      componentsDir: resolve(opts.components),
      tokensFile: opts.tokens ? resolve(opts.tokens) : undefined,
    });
  });

const list = program.command("list").description("List components or tokens");

list
  .command("components")
  .description("List all components")
  .requiredOption("--dir <dir>", "Components directory")
  .action((opts) => {
    const components = scanComponents(resolve(opts.dir));
    for (const c of components) {
      console.log(`  ${c.name} (${c.exportType}) — ${c.filePath}`);
    }
    console.log(`\n${components.length} components found.`);
  });

list
  .command("tokens")
  .description("List all design tokens")
  .requiredOption("--file <file>", "Tokens file")
  .option("--type <type>", "Filter by type (color, dimension, etc.)")
  .action((opts) => {
    const tokens = parseTokens(resolve(opts.file));
    const filtered = listTokens(tokens, opts.type);
    for (const t of filtered) {
      let line = `  ${t.name}: ${t.value} (${t.type})`;
      if (t.group) {
        line += ` [${t.group}]`;
      }
      if (t.resolvedValue) {
        line += ` -> ${t.resolvedValue}`;
      }
      console.log(line);
    }
    console.log(`\n${filtered.length} tokens found.`);
  });

program
  .command("search <query>")
  .description("Search for components by name")
  .requiredOption("--dir <dir>", "Components directory")
  .action((query, opts) => {
    const components = scanComponents(resolve(opts.dir));
    const results = searchComponents(components, query);
    if (results.length === 0) {
      console.log("No components found.");
      return;
    }
    for (const c of results) {
      console.log(`  ${c.name} — ${c.filePath}`);
    }
  });

program
  .command("props <name>")
  .description("Show props for a specific component")
  .requiredOption("--dir <dir>", "Components directory")
  .action((name, opts) => {
    const components = scanComponents(resolve(opts.dir));
    const result = getComponentWithProps(components, name);
    if (!result) {
      console.log(`Component "${name}" not found.`);
      return;
    }
    console.log(`${result.name} (${result.exportType})`);
    console.log(`File: ${result.filePath}\n`);
    console.log("Props:");
    for (const p of result.props) {
      const req = p.required ? "required" : "optional";
      let line = `  ${p.name}: ${p.type} (${req})`;
      if (p.defaultValue) {
        line += ` = ${p.defaultValue}`;
      }
      if (p.variants) {
        line += ` [${p.variants.join(", ")}]`;
      }
      console.log(line);
    }
  });

program.parse();
