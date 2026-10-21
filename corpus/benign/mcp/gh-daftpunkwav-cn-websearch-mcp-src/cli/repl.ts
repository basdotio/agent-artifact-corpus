/**
 * @file cli/repl
 * @description Interactive terminal session: type a query to search; slash
 *   commands control the system.
 *
 * Responsibilities:
 * - Provide a readline session: bare text is treated as a search, `/commands`
 *   control strategy/count/providers
 * - Process input lines serially so concurrent searches do not interleave
 *   output
 * - Any single command failure only prints the error and continues; the
 *   session is never ended by it
 */

// Interactive session layer. Session state (strategy/count/provider
// filter/output format) lives only in memory and is never written back to the
// config file — the CLI is a consumer, not a configuration tool.

import { createInterface } from 'node:readline';
import { effectiveCount } from '../config.js';
import { summarizeError } from '../errors.js';
import { parseProviderNames } from '../provider-selection.js';
import { SEARCH_STRATEGIES, type SearchStrategy } from '../types.js';
import { redactedConfig } from './render.js';
import {
  cmdSearch, cmdStatus, cmdTest, writeLine, DEFAULT_PROBE_QUERY, type CliDeps,
} from './commands.js';
import type { CliArgs } from './args.js';

const PROMPT = 'cn-websearch> ';

/** Mutable in-session state. */
export interface ReplSession {
  strategy: SearchStrategy;
  count: number;
  providers?: string[];
  dedupe: boolean;
  json: boolean;
}

const HELP = [
  'Commands (any other input is treated as a search query):',
  '  /search <query>          Search with the current settings',
  '  /aggregate <query>       Search several providers at once and merge the results',
  '  /strategy [name]         Show or set strategy: fallback | aggregate',
  '  /count [n]               Show or set the desired number of results',
  '  /providers [a,b]         Show or set the provider subset for this session',
  '  /status                  Show effective settings and provider status',
  '  /test [provider...]      Probe providers once (real requests)',
  '  /config                  Show the redacted effective configuration',
  '  /json [on|off]           Toggle raw JSON output',
  '  /help                    Show this help',
  '  /quit                    Exit (also: /exit, /q, Ctrl-D)',
].join('\n');

/** Whether the line is a slash command rather than a bare-text search. */
function looksLikeCommand(line: string): boolean {
  return line.startsWith('/');
}

/**
 * Run the interactive session. Returns the exit code (always 0 on normal
 * exit). All input/output goes through the injected io, so tests can
 * substitute streams for a real terminal.
 */
export function runRepl(
  deps: CliDeps,
  io: { input: NodeJS.ReadableStream },
): Promise<number> {
  const { config } = deps.runtime;
  const session: ReplSession = {
    strategy: config.strategy,
    count: config.count,
    dedupe: config.dedupe,
    json: false,
  };
  const chainNames = deps.runtime.chain.map((p) => p.name);

  const rl = createInterface({
    input: io.input,
    output: deps.output,
    prompt: PROMPT,
  });
  const write = (text: string): void => {
    writeLine(deps.output, text);
  };
  write(`cn-websearch-mcp interactive session — ${chainNames.length} provider(s) ready: ${chainNames.join(', ') || '(none)'}`);
  write('Type a query to search, or /help for commands.');

  /**
   * The one way a session line reaches the search command. Bare text,
   * `/search` and `/aggregate` all map the session settings here, so a setting
   * added to the session cannot be honoured by one spelling and silently
   * dropped by another; the guards below are likewise stated once.
   *
   * `label` is the command the user actually typed, so a refusal names the
   * command they used instead of always answering `/search`. `strategy` is the
   * one caller-owned override `/aggregate` makes.
   */
  const doSearch = async (
    query: string,
    label: string,
    strategy: SearchStrategy,
  ): Promise<void> => {
    const trimmed = query.trim();
    if (!trimmed) {
      write(`usage: /${label} <query>`);
      return;
    }
    // In-session switches are slash commands; if a user passes a --flag as the query, silently
    // searching a "--" query would be misleading, so offer a workable alternative instead.
    if (trimmed.startsWith('-')) {
      write(`error: /${label} takes a query only — use /json, /count, /strategy or /providers to change session settings`);
      return;
    }
    const args: CliArgs = {
      command: 'search',
      query: trimmed,
      count: session.count,
      strategy,
      providers: session.providers,
      dedupe: session.dedupe,
      json: session.json,
    };
    await cmdSearch(deps, args);
  };

  /** Handle one line of input; the return value indicates whether exit was requested. */
  const handle = async (line: string): Promise<boolean> => {
    const trimmed = line.trim();
    if (!trimmed) return false;
    if (!looksLikeCommand(trimmed)) {
      await doSearch(trimmed, 'search', session.strategy);
      return false;
    }

    const [rawCmd, ...rest] = trimmed.slice(1).split(/\s+/);
    const cmd = (rawCmd ?? '').toLowerCase();
    const argText = rest.join(' ').trim();

    switch (cmd) {
      case 'quit':
      case 'exit':
      case 'q':
        return true;

      case 'help':
      case '?':
        write(HELP);
        return false;

      case 'search':
      case 'aggregate':
        // /aggregate is a one-shot multi-source search; it does not change
        // the session default strategy.
        await doSearch(argText, cmd, cmd === 'aggregate' ? 'aggregate' : session.strategy);
        return false;

      case 'strategy': {
        if (!argText) {
          write(`strategy: ${session.strategy}`);
          return false;
        }
        const value = argText.toLowerCase() as SearchStrategy;
        if (!(SEARCH_STRATEGIES as readonly string[]).includes(value)) {
          write(`error: unknown strategy "${argText}" (expected ${SEARCH_STRATEGIES.join('|')})`);
          return false;
        }
        session.strategy = value;
        write(`strategy: ${value}`);
        return false;
      }

      case 'count': {
        if (!argText) {
          write(`count: ${session.count}`);
          return false;
        }
        const n = Number(argText);
        if (!Number.isInteger(n) || n <= 0) {
          write(`error: invalid count "${argText}" (expected a positive integer)`);
          return false;
        }
        // Store and echo the effective count: the search layer clamps to the same
        // range, so an out-of-range value must not be reported as if it took effect.
        // `n` is already a positive integer, so effectiveCount's fallback is unreachable.
        const effective = effectiveCount(n, session.count);
        session.count = effective;
        write(`count: ${effective}`);
        return false;
      }

      case 'providers': {
        if (!argText) {
          write(`providers: ${session.providers?.join(', ') ?? '(all available)'}`);
          return false;
        }
        if (argText === 'all' || argText === '-') {
          session.providers = undefined;
          write('providers: (all available)');
          return false;
        }
        // Same name rules as the one-shot commands and the MCP tool layer.
        const parsed = parseProviderNames(argText);
        if (!parsed.ok) {
          write(`error: ${parsed.error}`);
          return false;
        }
        session.providers = parsed.names;
        write(`providers: ${parsed.names.join(', ')}`);
        return false;
      }

      case 'status':
        await cmdStatus(deps, { command: 'status', query: '', json: session.json });
        return false;

      case 'test':
        // Positional words are provider names; the probe query stays the neutral
        // default, so a health check never searches for a slot name.
        await cmdTest(deps, {
          command: 'test',
          query: DEFAULT_PROBE_QUERY,
          providers: argText ? argText.split(/\s+/).filter((s) => s !== '') : session.providers,
          json: session.json,
        });
        return false;

      case 'config':
        write(JSON.stringify(redactedConfig(config), null, 2));
        return false;

      case 'json': {
        if (!argText) {
          write(`json: ${session.json ? 'on' : 'off'}`);
          return false;
        }
        const value = argText.toLowerCase();
        if (value !== 'on' && value !== 'off') {
          write('error: expected /json on or /json off');
          return false;
        }
        session.json = value === 'on';
        write(`json: ${value}`);
        return false;
      }

      default:
        write(`unknown command: /${cmd} — type /help for the list`);
        return false;
    }
  };

  // Serial queue: input lines can arrive faster than async searches; chaining
  // awaits prevents interleaved output.
  let pending: Promise<void> = Promise.resolve();
  let quit = false;
  // Whether readline has already been torn down (stdin EOF, Ctrl-D or Ctrl-C).
  // Tracked here because the interface is closed while a search may still be in
  // flight, and prompting a closed interface throws ERR_USE_AFTER_CLOSE.
  let closed = false;
  rl.on('line', (raw) => {
    if (quit) return;
    pending = pending.then(async () => {
      if (quit) return;
      try {
        const shouldQuit = await handle(raw);
        if (shouldQuit) {
          quit = true;
          rl.close();
          return;
        }
      } catch (err) {
        // An unexpected failure in a single command must not end the session.
        // summarizeError keeps credential-looking text out of the terminal.
        write(`error: ${summarizeError(err)}`);
      }
      if (!closed) rl.prompt();
    });
  });

  rl.on('SIGINT', () => {
    write('');
    quit = true;
    rl.close();
  });

  return new Promise<number>((resolve) => {
    rl.on('close', () => {
      closed = true;
      void pending.then(() => {
        resolve(0);
      });
    });
    rl.prompt();
  });
}
