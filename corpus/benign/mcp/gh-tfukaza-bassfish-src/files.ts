import { lstat, realpath, stat } from 'node:fs/promises';
import { basename, dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { BassfishError, requireThat } from './domain.js';
import type { FileTarget } from './domain.js';

/** Locks name paths, not inodes: editor replacement writes retain their reservation. */
function containsPath(directory: string, path: string): boolean {
  const suffix = relative(directory, path);
  return (
    suffix === '' || (!isAbsolute(suffix) && suffix !== '..' && !suffix.startsWith(`..${sep}`))
  );
}

export function fileSetsOverlap(left: FileTarget[], right: FileTarget[]): boolean {
  return left.some(a =>
    right.some(
      b =>
        a.path === b.path ||
        (a.kind === 'directory' && containsPath(a.path, b.path)) ||
        (b.kind === 'directory' && containsPath(b.path, a.path)),
    ),
  );
}

async function canonicalPath(path: string): Promise<string> {
  try {
    return await realpath(path);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    // A dangling symlink is not a missing destination: resolving it would silently
    // reserve the link's name while a writer follows a different target.
    try {
      await lstat(path);
      throw new BassfishError('INVALID_PATH', 'A target or ancestor is a dangling symlink.');
    } catch (missing) {
      if ((missing as NodeJS.ErrnoException).code !== 'ENOENT') throw missing;
    }
    const parent = dirname(path);
    requireThat(parent !== path, 'INVALID_PATH', 'The filesystem root cannot be resolved.');
    const ancestor = await canonicalPath(parent);
    try {
      requireThat(
        (await stat(ancestor)).isDirectory(),
        'INVALID_PATH',
        'A target ancestor is not a directory.',
      );
    } catch (missing) {
      if ((missing as NodeJS.ErrnoException).code !== 'ENOENT') throw missing;
    }
    return resolve(ancestor, basename(path));
  }
}

export async function resolveFileTargets(
  workspace: string,
  targets: FileTarget[],
): Promise<FileTarget[]> {
  requireThat(
    targets.length > 0 && targets.length <= 256,
    'INVALID_ARGUMENT',
    'Provide from 1 through 256 file or directory targets.',
  );
  const resolved: FileTarget[] = [];
  for (const target of targets) {
    requireThat(
      typeof target.path === 'string' &&
        target.path.length > 0 &&
        !target.path.includes('\0') &&
        (target.kind === 'file' || target.kind === 'directory'),
      'INVALID_ARGUMENT',
      'Each target needs a path and file or directory kind.',
    );
    try {
      const path = await canonicalPath(resolve(workspace, target.path));
      try {
        const info = await stat(path);
        requireThat(
          target.kind === 'directory' ? info.isDirectory() : info.isFile(),
          'PATH_KIND_MISMATCH',
          'The existing target does not match its requested kind.',
        );
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
      }
      const previous = resolved.find(item => item.path === path);
      requireThat(
        !previous || previous.kind === target.kind,
        'PATH_KIND_MISMATCH',
        'The same path cannot be both a file and a directory.',
      );
      if (!previous) resolved.push({ path, kind: target.kind });
    } catch (error) {
      if (error instanceof BassfishError) throw error;
      throw new BassfishError('INVALID_PATH', `Cannot resolve target ${target.path}.`, {
        cause: (error as NodeJS.ErrnoException).code,
      });
    }
  }
  return resolved
    .filter(
      target =>
        !resolved.some(
          parent =>
            parent !== target &&
            parent.kind === 'directory' &&
            containsPath(parent.path, target.path),
        ),
    )
    .sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
}
