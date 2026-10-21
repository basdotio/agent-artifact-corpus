/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import fs from 'node:fs';
import fsPromises from 'node:fs/promises';
import path from 'node:path';

import {ToolError} from './ToolError.js';

let allowedRoots: string[] | undefined;

function isWithinRoot(candidate: string, root: string): boolean {
  const relative = path.relative(root, candidate);
  return (
    relative === '' ||
    (!relative.startsWith(`..${path.sep}`) &&
      relative !== '..' &&
      !path.isAbsolute(relative))
  );
}

function assertWithinAllowedRoots(candidate: string): void {
  if (!allowedRoots) {
    return;
  }
  if (allowedRoots.some(root => isWithinRoot(candidate, root))) {
    return;
  }
  throw new ToolError(
    'PERMISSION_DENIED',
    `Local file access is outside the configured allowed roots: ${candidate}`,
  );
}

/**
 * Configure the optional local-file sandbox. Roots must already exist so their
 * real paths can be pinned before any tool call follows symlinks.
 */
export function configureAllowedRoots(roots?: readonly string[]): void {
  if (!roots?.length) {
    allowedRoots = undefined;
    return;
  }

  allowedRoots = [
    ...new Set(roots.map(root => fs.realpathSync(path.resolve(root)))),
  ];
  for (const root of allowedRoots) {
    if (!fs.statSync(root).isDirectory()) {
      throw new Error(`Allowed root is not a directory: ${root}`);
    }
  }
}

export function getAllowedRoots(): readonly string[] | undefined {
  return allowedRoots;
}

export function assertLocalFileReadAllowed(filePath: string): string {
  const resolved = fs.realpathSync(path.resolve(filePath));
  assertWithinAllowedRoots(resolved);
  return resolved;
}

export async function openLocalFileReadAllowed(filePath: string) {
  const resolved = assertLocalFileReadAllowed(filePath);
  let handle: Awaited<ReturnType<typeof fsPromises.open>> | undefined;
  try {
    handle = await fsPromises.open(
      resolved,
      fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK,
    );
    const stat = await handle.stat();
    if (!stat.isFile()) {
      await handle.close();
      throw new ToolError(
        'INVALID_ARGUMENT',
        `Local file input must be a regular file: ${resolved}`,
      );
    }
    return {handle, resolvedPath: resolved, stat};
  } catch (error) {
    await handle?.close().catch(() => undefined);
    if (
      typeof error === 'object' &&
      error !== null &&
      'code' in error &&
      (error.code === 'ELOOP' || error.code === 'EMLINK')
    ) {
      throw new ToolError(
        'PERMISSION_DENIED',
        `Refusing to read through a symbolic link: ${resolved}`,
        {cause: error},
      );
    }
    throw error;
  }
}

export function assertLocalFileWriteAllowed(filePath: string): string {
  const resolved = path.resolve(filePath);
  let candidate: string;
  let targetExists = false;
  try {
    const stat = fs.lstatSync(resolved);
    targetExists = true;
    if (stat.isSymbolicLink()) {
      try {
        candidate = fs.realpathSync(resolved);
      } catch (error) {
        throw new ToolError(
          'PERMISSION_DENIED',
          `Refusing to write through an unresolved symbolic link: ${resolved}`,
          {cause: error},
        );
      }
    } else {
      candidate = fs.realpathSync(resolved);
    }
  } catch (error) {
    if (error instanceof ToolError) {
      throw error;
    }
    if (
      typeof error !== 'object' ||
      error === null ||
      !('code' in error) ||
      error.code !== 'ENOENT'
    ) {
      throw error;
    }
    const parent = fs.realpathSync(path.dirname(resolved));
    candidate = path.join(parent, path.basename(resolved));
  }
  assertWithinAllowedRoots(candidate);
  if (targetExists && !fs.statSync(candidate).isFile()) {
    throw new ToolError(
      'INVALID_ARGUMENT',
      `Local file output must target a regular file: ${candidate}`,
    );
  }
  return candidate;
}

function unwrapViewSource(url: string): string {
  let result = url.trim();
  while (/^view-source:/i.test(result)) {
    result = result.slice('view-source:'.length).trimStart();
  }
  return result;
}

export function isBlockedLocalBrowserUrl(url: string): boolean {
  if (!allowedRoots) {
    return false;
  }
  const unwrapped = unwrapViewSource(url);
  try {
    const parsed = new URL(unwrapped);
    return parsed.protocol === 'file:' || /^filesystem:file:/i.test(unwrapped);
  } catch {
    return false;
  }
}

export function assertBrowserUrlAllowed(url: string): void {
  if (!isBlockedLocalBrowserUrl(url)) {
    return;
  }
  throw new ToolError(
    'PERMISSION_DENIED',
    'file: browser pages are disabled while --allowedRoots is configured.',
  );
}

export function formatBrowserUrlForOutput(url: string): string {
  return isBlockedLocalBrowserUrl(url)
    ? '[blocked local file page: --allowedRoots is configured]'
    : url;
}
