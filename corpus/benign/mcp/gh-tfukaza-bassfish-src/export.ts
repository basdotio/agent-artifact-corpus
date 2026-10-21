import { createHash } from 'node:crypto';
import { mkdir, rename, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { strToU8, zipSync } from 'fflate';
import type { CurrentProject } from './domain.js';

const stable = (value: unknown): string =>
  JSON.stringify(
    value,
    (_key, item) =>
      item && typeof item === 'object' && !Array.isArray(item)
        ? Object.fromEntries(
            Object.entries(item as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)),
          )
        : item,
    2,
  ) + '\n';
const fixed = new Date(1980, 1, 1, 0, 0, 0, 0);

export async function exportProject(
  dataDir: string,
  projectId: string,
  snapshot: CurrentProject,
): Promise<{ path: string; bytes: number; sha256: string; exportedAt: string }> {
  const files: Record<string, [Uint8Array, { mtime: Date; level: 0 }]> = {};
  const add = (path: string, value: string) => {
    files[path] = [strToU8(value), { mtime: fixed, level: 0 }];
  };
  for (const ticket of snapshot.tickets) {
    const { body, ...metadata } = ticket;
    add(`tickets/${ticket.id}.json`, stable(metadata));
    add(`tickets/${ticket.id}.md`, body);
  }
  for (const thread of snapshot.threads) {
    const messages = snapshot.messages.filter(message => message.threadId === thread.id);
    const visibility = snapshot.visibility.filter(item => item.threadId === thread.id);
    add(`threads/${thread.id}.json`, stable({ thread, messages, visibility }));
    const latest = new Map<string, boolean>();
    for (const item of visibility) latest.set(item.messageId, item.visible);
    add(
      `threads/${thread.id}.md`,
      `# ${thread.title}\n\n${messages.map(message => (latest.get(message.id) === false ? `> [Message ${message.sequence} retracted]` : `**${message.name}:** ${message.body}`)).join('\n\n')}\n`,
    );
  }
  const inventory = Object.keys(files)
    .sort()
    .map(path => ({ path, sha256: createHash('sha256').update(files[path]![0]).digest('hex') }));
  add(
    'manifest.json',
    stable({
      schemaVersion: 3,
      projectId,
      exportedAt: snapshot.exportedAt,
      revisions: [...snapshot.threads, ...snapshot.tickets].map(resource => ({
        id: resource.id,
        revision: resource.revision,
      })),
      inventory,
    }),
  );
  const archive = zipSync(
    Object.fromEntries(Object.entries(files).sort(([a], [b]) => a.localeCompare(b))),
  );
  const sha256 = createHash('sha256').update(archive).digest('hex');
  const directory = join(dataDir, 'exports');
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const path = join(directory, `${projectId}-${sha256.slice(0, 12)}.zip`);
  const temporary = `${path}.${process.pid}.tmp`;
  await writeFile(temporary, archive, { mode: 0o600 });
  await rename(temporary, path);
  return { path, bytes: archive.byteLength, sha256, exportedAt: snapshot.exportedAt };
}
