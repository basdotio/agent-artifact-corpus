import { BassfishError, requireThat } from './domain.js';
import { boundedIntegerOption, take } from './cli-helpers.js';
import type { Call, CliInteraction } from './cli-helpers.js';
export function presentProjectCli(value: unknown): unknown {
  return value;
}
export async function runProjectCli(
  action: string | undefined,
  args: string[],
  call: Call,
  _interaction?: CliInteraction,
): Promise<unknown> {
  if (action === 'inspect' || action === 'export') {
    requireThat(args.length === 0, 'INVALID_ARGUMENT', `Project ${action} takes no arguments.`);
    return call(action === 'inspect' ? 'inspectProject' : 'exportProject', {});
  }
  if (action === 'history') {
    const limit = boundedIntegerOption(args, '--limit', { min: 1, max: 100 }) ?? 50,
      cursor = take(args, '--cursor');
    requireThat(
      args.length === 0,
      'INVALID_ARGUMENT',
      'Use project history [--limit N] [--cursor C].',
    );
    return call('listProjectHistory', { limit, ...(cursor ? { cursor } : {}) });
  }
  throw new BassfishError('INVALID_ARGUMENT', 'Use project inspect, export, or history.');
}
