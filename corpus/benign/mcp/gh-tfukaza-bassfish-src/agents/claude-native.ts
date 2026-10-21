import { randomUUID } from 'node:crypto';
import { open, mkdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { BassfishError, requireThat } from '../domain.js';

const execFileAsync = promisify(execFile);
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function readOrCreateClaudeClientId(pluginDataDir: string): Promise<string> {
  requireThat(
    pluginDataDir.length > 0,
    'INVALID_CLAUDE_PLUGIN_DATA',
    'Claude plugin data directory is missing.',
  );
  return readOrCreateClientId(
    pluginDataDir,
    'bassfish-client-id',
    'INVALID_CLAUDE_CLIENT_ID',
    'The Claude plugin client ID is corrupt; remove bassfish-client-id from the plugin data directory to regenerate it.',
  );
}

export async function readOrCreateOpenCodeClientId(dataDir: string): Promise<string> {
  requireThat(
    dataDir.length > 0,
    'INVALID_OPENCODE_DATA',
    'The Bassfish data directory is missing.',
  );
  return readOrCreateClientId(
    join(dataDir, 'native', 'opencode'),
    'client-id',
    'INVALID_OPENCODE_CLIENT_ID',
  );
}

async function readOrCreateClientId(
  directory: string,
  fileName: string,
  corruptCode: string,
  corruptMessage?: string,
): Promise<string> {
  await mkdir(directory, { recursive: true, mode: 0o700 });
  const path = join(directory, fileName);
  try {
    const existing = (await readFile(path, 'utf8')).trim();
    requireThat(
      uuidPattern.test(existing),
      corruptCode,
      corruptMessage ?? `The native client ID at ${path} is corrupt; remove it to regenerate it.`,
    );
    return existing;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
  }
  const created = randomUUID();
  try {
    const file = await open(path, 'wx', 0o600);
    try {
      await file.writeFile(`${created}\n`);
    } finally {
      await file.close();
    }
    return created;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'EEXIST') throw error;
    return readOrCreateClientId(directory, fileName, corruptCode, corruptMessage);
  }
}

export function ancestryFromProcessTable(table: string, startPid = process.pid): number[] {
  const parents = new Map<number, number>();
  for (const line of table.split('\n')) {
    const match = /^\s*(\d+)\s+(\d+)\s*$/.exec(line);
    if (match) parents.set(Number(match[1]), Number(match[2]));
  }
  const result: number[] = [];
  const seen = new Set<number>();
  let pid = startPid;
  while (pid > 0 && !seen.has(pid) && result.length < 64) {
    result.push(pid);
    seen.add(pid);
    const parent = parents.get(pid);
    if (!parent || parent === pid) break;
    pid = parent;
  }
  return result;
}

export async function processAncestry(pid = process.pid): Promise<number[]> {
  try {
    const { stdout } = await execFileAsync('ps', ['-axo', 'pid=,ppid='], {
      maxBuffer: 4 * 1024 * 1024,
    });
    const result = ancestryFromProcessTable(stdout, pid);
    requireThat(
      result.length > 0,
      'PROCESS_ANCESTRY_UNAVAILABLE',
      'Could not determine the host process ancestry.',
    );
    return result;
  } catch (error) {
    if (error instanceof BassfishError) throw error;
    throw new BassfishError(
      'PROCESS_ANCESTRY_UNAVAILABLE',
      'Could not determine the host process ancestry.',
    );
  }
}

export interface NativeHostCandidate {
  handle: string;
  processAncestors: number[];
}

export function selectNativeCandidate(
  candidates: NativeHostCandidate[],
  monitorAncestors: number[],
): NativeHostCandidate | undefined {
  const monitorIndex = new Map(monitorAncestors.map((pid, index) => [pid, index]));
  const scored = candidates
    .flatMap(candidate => {
      let best: [number, number] | undefined;
      candidate.processAncestors.forEach((pid, index) => {
        if (pid === 1) return;
        const other = monitorIndex.get(pid);
        if (other === undefined) return;
        const score: [number, number] = [Math.max(index, other), index + other];
        if (!best || score[0] < best[0] || (score[0] === best[0] && score[1] < best[1]))
          best = score;
      });
      return best ? [{ candidate, score: best }] : [];
    })
    .sort((a, b) => a.score[0] - b.score[0] || a.score[1] - b.score[1]);
  if (!scored[0]) return undefined;
  if (
    scored[1] &&
    scored[0].score[0] === scored[1].score[0] &&
    scored[0].score[1] === scored[1].score[1]
  )
    return undefined;
  return scored[0].candidate;
}
