/**
 * @license
 * Copyright 2026
 * SPDX-License-Identifier: Apache-2.0
 */

import {randomInt} from 'node:crypto';
import {
  closeSync,
  constants as fsConstants,
  fchmodSync,
  fstatSync,
  ftruncateSync,
  mkdirSync,
  openSync,
  readFileSync,
  writeSync,
} from 'node:fs';
import path from 'node:path';

interface CloakBrowserModule {
  ensureBinary(): Promise<string>;
  binaryInfo(): {installed: boolean};
  getDefaultStealthArgs(): string[];
}

async function loadCloakBrowser(): Promise<CloakBrowserModule> {
  try {
    return (await import('cloakbrowser')) as unknown as CloakBrowserModule;
  } catch {
    throw new Error(
      '--cloak requires the `cloakbrowser` package. ' +
        'Install it with `npm install cloakbrowser`, or re-run via ' +
        '`npx js-reverse-mcp@latest --cloak` to pull it as an optional dependency.',
    );
  }
}

/**
 * Redirect `console.log` / `console.info` to stderr for the duration of `fn`.
 *
 * MCP servers use **stdout** as the JSON-RPC channel — any non-protocol bytes
 * there corrupt the protocol and the client disconnects. cloakbrowser's
 * `ensureBinary()` writes download progress via `console.log` (stdout), so we
 * must redirect those writes to stderr while it runs. Progress is still
 * visible (stderr surfaces in the MCP client's server log panel).
 */
async function withStdoutRedirectedToStderr<T>(
  fn: () => Promise<T>,
): Promise<T> {
  const origLog = console.log;
  const origInfo = console.info;
  console.log = (...args: unknown[]) => console.error(...args);
  console.info = (...args: unknown[]) => console.error(...args);
  try {
    return await fn();
  } finally {
    console.log = origLog;
    console.info = origInfo;
  }
}

export function getOrCreateSeed(profileDir: string): number {
  mkdirSync(profileDir, {recursive: true, mode: 0o700});
  const seedFile = path.join(profileDir, '.cloak-seed');
  let fd: number | undefined;
  try {
    fd = openSync(
      seedFile,
      fsConstants.O_RDWR |
        fsConstants.O_CREAT |
        fsConstants.O_NOFOLLOW |
        fsConstants.O_NONBLOCK,
      0o600,
    );
    if (!fstatSync(fd).isFile()) {
      throw new Error(
        `Cloak fingerprint seed is not a regular file: ${seedFile}`,
      );
    }
    fchmodSync(fd, 0o600);
    const parsed = Number.parseInt(readFileSync(fd, 'utf8').trim(), 10);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
    const seed = randomInt(10000, 100000);
    ftruncateSync(fd, 0);
    writeSync(fd, String(seed), 0, 'utf8');
    return seed;
  } finally {
    if (fd !== undefined) {
      closeSync(fd);
    }
  }
}

export interface CloakSetup {
  executablePath: string;
  args: string[];
}

export function buildCloakArgs(defaultArgs: readonly string[], seed: number) {
  return [
    ...defaultArgs.filter(
      arg => arg !== '--no-sandbox' && !arg.startsWith('--fingerprint='),
    ),
    `--fingerprint=${seed}`,
  ];
}

/**
 * Resolve the CloakBrowser binary and build the cloak-specific args.
 *
 * When profileDir is provided, the fingerprint seed is persisted there so the
 * same profile always presents the same virtual identity (a stable "returning
 * visitor"). When undefined (isolated mode), a random seed is generated for
 * this launch only.
 */
export async function setupCloak(
  profileDir: string | undefined,
): Promise<CloakSetup> {
  const cloak = await loadCloakBrowser();

  // cloakbrowser writes download progress to stdout (`console.log`).
  // We must redirect those writes to stderr to avoid corrupting the MCP
  // JSON-RPC channel — see the helper's docstring above.
  const executablePath = await withStdoutRedirectedToStderr(async () => {
    if (!cloak.binaryInfo().installed) {
      process.stderr.write(
        '[js-reverse-mcp] Downloading CloakBrowser stealth binary (~200MB, one-time setup)...\n',
      );
    }
    return cloak.ensureBinary();
  });

  const seed = profileDir
    ? getOrCreateSeed(profileDir)
    : randomInt(10000, 100000);

  // Follow the current CloakBrowser platform profile and future stealth flags,
  // but keep this desktop debugging server sandboxed and replace the random
  // upstream fingerprint with our profile-stable seed.
  return {
    executablePath,
    args: buildCloakArgs(cloak.getDefaultStealthArgs(), seed),
  };
}
