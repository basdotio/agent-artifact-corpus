import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { realpath } from 'node:fs/promises';
import { BassfishError } from './domain.js';

const exec = promisify(execFile);
export async function resolveRepository(workspace: string): Promise<string> {
  try {
    const root = await realpath(workspace);
    const env = { ...process.env };
    // An enclosing shell's Git overrides must not redirect a workspace's project identity.
    for (const key of Object.keys(env)) if (key.startsWith('GIT_')) delete env[key];
    const { stdout } = await exec(
      'git',
      ['-C', root, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
      { env, timeout: 5000 },
    );
    return await realpath(stdout.trim());
  } catch {
    throw new BassfishError(
      'NOT_A_REPOSITORY',
      'The configured workspace must be a local Git repository.',
    );
  }
}
