/**
 * @file cli/index
 * @description CLI dispatch entry point: routes commands to serve or the one-shot commands,
 *   and unifies exit codes.
 *
 * Responsibilities:
 * - Parse argv and dispatch to serve / search / status / test / repl / help / version
 * - With no arguments, start the MCP stdio server (preserving how MCP clients already launch it)
 * - Collapse all failures into exit codes; never throws from this layer
 */

// CLI dispatch layer. All dependencies (runtime, output streams, the serve implementation) are
// injected by the caller, so it can be driven entirely in tests without spawning a subprocess.

import { SERVER_NAME, SERVER_VERSION } from '../server-info.js';
import { parseArgs, usage } from './args.js';
import {
  cmdSearch, cmdStatus, cmdTest, EXIT, writeLine, type CliDeps,
} from './commands.js';
import { runRepl } from './repl.js';

/**
 * Re-exported so a caller reaching for the exit-code contract through the
 * dispatcher keeps finding it; commands.ts owns it because that is where most
 * of the codes are produced, and importing it back here would be a cycle.
 */
export { EXIT };

/** CLI dependencies: CliDeps plus the serve implementation (injected by the entry point). */
export interface CliRunDeps extends CliDeps {
  serve: () => Promise<void>;
  input: NodeJS.ReadableStream;
}

/**
 * Run one CLI invocation and return the exit code. This is the only CLI entry point:
 * index.ts merely injects the real dependencies and converts the exit code into a process exit.
 */
export async function runCli(argv: string[], deps: CliRunDeps): Promise<number> {
  const parsed = parseArgs(argv);
  if (!parsed.ok) {
    writeLine(deps.error, `error: ${parsed.message}`);
    writeLine(deps.error, usage());
    return EXIT.usage;
  }
  const { args } = parsed;

  // One fatal boundary for the whole dispatcher, so the header's "never
  // throws" promise holds for every command: expected failures are exit codes
  // inside the commands, and a bug that makes a command reject still collapses
  // to one line on the injected error stream plus EXIT.failure.
  try {
    switch (args.command) {
      case 'help':
        writeLine(deps.output, usage());
        return EXIT.ok;

      case 'version':
        writeLine(deps.output, `${SERVER_NAME} ${SERVER_VERSION}`);
        return EXIT.ok;

      case 'status':
        return await cmdStatus(deps, args);

      case 'search':
        return await cmdSearch(deps, args);

      case 'test':
        return await cmdTest(deps, args);

      case 'repl':
        return await runRepl(deps, deps);

      // Parsed commands without a dedicated case, including 'serve', land here.
      default:
        await deps.serve();
        return EXIT.ok;
    }
  } catch (err) {
    writeLine(deps.error, `[${SERVER_NAME}] fatal: ${err instanceof Error ? err.message : String(err)}`);
    return EXIT.failure;
  }
}
