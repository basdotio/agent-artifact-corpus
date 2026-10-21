import { resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { requireThat } from './domain.js';
import { connectDaemon, ensureDaemon } from './daemon.js';
import { processAncestry, readOrCreateClaudeClientId } from './agents/claude-native.js';
import { formatDeliveryContext, type DeliveryBatch } from './notification-delivery.js';

export function formatClaudeDeliveryNotification(batch: DeliveryBatch): Record<string, unknown> {
  return {
    type: 'bassfish_notifications',
    message: formatDeliveryContext(batch),
    ...batch,
  };
}

/** Claude plugin Monitor entrypoint. Each stdout line is one native Claude notification. */
export async function runNotificationWatcher(args: string[], dataDir: string): Promise<void> {
  requireThat(
    args.shift() === '--native-claude',
    'INVALID_ARGUMENT',
    'notifications watch is an internal Claude plugin command.',
  );
  const index = args.indexOf('--workspace');
  requireThat(
    index >= 0 && args[index + 1] && !args[index + 1]!.startsWith('--'),
    'INVALID_ARGUMENT',
    'notifications watch requires --workspace PATH.',
  );
  const workspace = resolve(args[index + 1]!);
  args.splice(index, 2);
  const dataIndex = args.indexOf('--plugin-data');
  requireThat(
    dataIndex >= 0 && args[dataIndex + 1] && !args[dataIndex + 1]!.startsWith('--'),
    'INVALID_ARGUMENT',
    'notifications watch requires --plugin-data PATH.',
  );
  const pluginData = resolve(args[dataIndex + 1]!);
  args.splice(dataIndex, 2);
  requireThat(args.length === 0, 'INVALID_ARGUMENT', 'Unknown notifications watch argument.');
  const clientId = await readOrCreateClaudeClientId(pluginData);
  const processAncestors = await processAncestry();
  const controller = new AbortController();
  let activeClient: Awaited<ReturnType<typeof connectDaemon>> | undefined;
  const stop = () => {
    controller.abort();
    activeClient?.socket.destroy();
  };
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
  let backoffMs = 250;
  let lastWarningAt = 0;
  let outageAt: number | undefined;
  try {
    while (!controller.signal.aborted) {
      let client;
      try {
        await ensureDaemon(dataDir, {}, controller.signal);
        client = await connectDaemon(dataDir);
        activeClient = client;
        if (controller.signal.aborted) {
          client.socket.destroy();
          break;
        }
        while (!controller.signal.aborted) {
          const batch = await client.call<DeliveryBatch>(
            'waitNativeDelivery',
            { workspace, host: 'claude', clientId, processAncestors, timeoutMs: 20_000 },
            controller.signal,
            25_000,
          );
          backoffMs = 250;
          if (outageAt !== undefined) {
            process.stderr.write(
              `Bassfish notification delivery recovered after ${Math.round((Date.now() - outageAt) / 1000)}s.\n`,
            );
            outageAt = undefined;
          }
          if (batch.count === 0) continue;
          const notification = formatClaudeDeliveryNotification(batch);
          process.stdout.write(`${JSON.stringify(notification)}\n`);
        }
      } catch (error) {
        if (controller.signal.aborted) break;
        const code = (error as { code?: string }).code ?? '';
        if (
          ![
            'OUTCOME_UNKNOWN',
            'CONNECTION_CLOSED',
            'ALREADY_RUNNING',
            'STORAGE_BUSY',
            'STORAGE_UNAVAILABLE',
            'DAEMON_STOPPING',
            'ECONNRESET',
            'EPIPE',
            'ETIMEDOUT',
            'DAEMON_START_FAILED',
            'ECONNREFUSED',
            'ENOENT',
          ].includes(code)
        )
          throw error;
        client?.socket.destroy();
        const firstFailure = outageAt === undefined;
        outageAt ??= Date.now();
        if (firstFailure || Date.now() - lastWarningAt >= 60_000) {
          process.stderr.write(
            `Bassfish notification delivery deferred (${code || 'unavailable'}).\n`,
          );
          lastWarningAt = Date.now();
        }
        try {
          await delay(backoffMs / 2 + (Math.random() * backoffMs) / 2, undefined, {
            signal: controller.signal,
          });
        } catch {
          break;
        }
        backoffMs = Math.min(backoffMs * 2, 5_000);
      } finally {
        client?.socket.destroy();
        activeClient = undefined;
      }
    }
  } finally {
    process.off('SIGINT', stop);
    process.off('SIGTERM', stop);
  }
}
