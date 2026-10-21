import { loadSonarUi } from './ui-runtime.js';
import { resolve } from 'node:path';
import { requireThat } from '../domain.js';
import { resolveRepository } from '../repository.js';
import { booleanFlag, take } from '../cli-helpers.js';
import type { CliOutputOptions } from '../cli-output.js';
import { SonarClient } from './client.js';
import { views, initialScreen, paintScreen, type View } from './screen.js';
export async function runSonar(
  args: string[],
  dataDir: string,
  options: CliOutputOptions,
  plain = false,
): Promise<void> {
  const once = booleanFlag(args, '--once');
  const monitor = booleanFlag(args, '--monitor');
  const ascii = booleanFlag(args, '--ascii');
  const view = take(args, '--view') ?? 'monitor';
  const workspace = resolve(take(args, '--workspace') ?? process.cwd());
  requireThat(
    views.includes(view as View) && (!monitor || view === 'monitor') && args.length === 0,
    'INVALID_ARGUMENT',
    'Use sonar [--monitor | --view monitor|threads|files|tickets|activity] [--workspace PATH] [--ascii] [--once].',
  );
  await resolveRepository(workspace);
  const client = new SonarClient(dataDir, workspace);
  if (once || plain || !options.interactive || process.env.TERM === 'dumb') {
    const snapshot = await client.once();
    if (options.mode === 'json')
      process.stdout.write(
        JSON.stringify(
          snapshot ?? {
            status: 'stopped',
            message: 'Start the daemon with bassfish daemon start.',
            content: null,
          },
          null,
          2,
        ) + '\n',
      );
    else if (!snapshot)
      process.stdout.write('Sonar · daemon stopped\nRun bassfish daemon start.\n');
    else
      process.stdout.write(
        paintScreen(
          { phase: 'live', snapshot, gap: false },
          initialScreen('monitor'),
          Math.max(80, options.width),
          30,
          ascii,
        ).plain() + '\n',
      );
    return;
  }
  const { render, createElement, SonarApp } = await loadSonarUi();
  const app = render(
    createElement(SonarApp, { client, initialView: view as View, ascii, color: options.color }),
    {
      alternateScreen: true,
      incrementalRendering: true,
      maxFps: 10,
      exitOnCtrlC: false,
      patchConsole: false,
      interactive: true,
    },
  );
  const stop = () => {
    client.close();
    app.unmount();
  };
  process.once('SIGTERM', stop);
  process.once('SIGINT', stop);
  const running = client.run();
  try {
    await app.waitUntilExit();
  } finally {
    client.close();
    app.unmount();
    await running;
    process.off('SIGTERM', stop);
    process.off('SIGINT', stop);
  }
}
