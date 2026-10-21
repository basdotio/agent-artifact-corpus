#!/usr/bin/env bun
import { readFileSync } from 'node:fs';
import { runRecipe } from '../examples/run-recipe.ts';
import { RUN_CAVEAT, browserSsoUnavailableMessage, describeError, makeClient } from './surface.ts';

const HELP = `pantry — reuse capability-scoped recipes from any harness.

Usage:
  pantry list [--shared] [--json]
  pantry get <name> [--json]
  pantry run <name> [--input <json>|@file|-] [--json]
  pantry push <file.json> [--shared] [--json]
  pantry mcp                                 start the MCP server over stdio
  pantry login                               explain browser SSO availability

Authentication:
  Employee access uses the Pantry deployment browser management app and SSO.
  Browser login/session handoff is not implemented in this CLI build.
  For non-interactive automation, explicitly configure PANTRY_TOKEN or
  ~/.terrarium/pantry-token.secret with a scoped credential.
`;

function has(flag: string): boolean {
  return process.argv.includes(flag);
}
function opt(flag: string): string | undefined {
  const i = process.argv.indexOf(flag);
  return i >= 0 ? process.argv[i + 1] : undefined;
}
function json(value: unknown): void {
  console.log(JSON.stringify(value, null, 2));
}
function parseInput(raw: string | undefined): unknown {
  if (!raw) return undefined;
  if (raw === '-') return JSON.parse(readFileSync(0, 'utf8'));
  if (raw.startsWith('@')) return JSON.parse(readFileSync(raw.slice(1), 'utf8'));
  return JSON.parse(raw);
}
function rows(recipes: { name: string; description?: string; capabilities?: string[] }[]): string {
  if (!recipes.length) return 'No recipes.';
  return recipes
    .map((r) =>
      `${r.name.padEnd(24)} ${(r.capabilities ?? []).join(', ').padEnd(24)} ${r.description ?? ''}`.trimEnd(),
    )
    .join('\n');
}

export async function main(): Promise<void> {
  const argv = process.argv.slice(2).filter((a) => a !== '--json' && a !== '--shared');
  const [cmd, arg] = argv;
  const asJson = has('--json');
  if (!cmd || cmd === 'help' || cmd === '--help' || cmd === '-h') {
    console.log(HELP);
    return;
  }
  if (cmd === 'mcp') {
    const { runStdio } = await import('./mcp.ts');
    await runStdio();
    return;
  }
  if (cmd === 'login') throw new Error(browserSsoUnavailableMessage());
  const { client, url } = makeClient();
  try {
    if (cmd === 'list') {
      const recipes = await client.list(has('--shared') ? { scope: 'shared' } : undefined);
      asJson ? json({ recipes }) : console.log(rows(recipes));
      return;
    }
    if (cmd === 'get') {
      if (!arg) throw new Error('usage: pantry get <name>');
      const recipe = await client.get(arg);
      if (!recipe) {
        asJson ? json({ found: false, name: arg }) : console.log(`Recipe '${arg}' not found.`);
        return;
      }
      asJson ? json({ found: true, recipe }) : json(recipe);
      return;
    }
    if (cmd === 'run') {
      if (!arg) throw new Error('usage: pantry run <name> [--input <json>|@file|-]');
      if (!asJson) console.error(RUN_CAVEAT);
      const recipe = await client.get(arg);
      if (!recipe) throw new Error(`Recipe '${arg}' not found; cannot run.`);
      const result = runRecipe(recipe, { input: parseInput(opt('--input')) });
      asJson ? json({ caveat: RUN_CAVEAT, result }) : json(result);
      return;
    }
    if (cmd === 'push') {
      if (!arg) throw new Error('usage: pantry push <file.json>');
      const recipe = JSON.parse(readFileSync(arg, 'utf8'));
      if (has('--shared')) recipe.visibility = 'shared';
      const saved = await client.push(recipe);
      asJson ? json({ saved }) : console.log(`Pushed '${saved.name}' v${saved.version} to ${url}.`);
      return;
    }
    throw new Error(`unknown command: ${cmd}\n${HELP}`);
  } catch (err) {
    throw new Error(describeError(err, url));
  }
}

if (import.meta.main)
  main().catch((err) => {
    console.error(err.message);
    process.exitCode = 1;
  });
