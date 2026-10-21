import { fileURLToPath } from 'node:url';
export function entryArgs(command: string, ...args: string[]): string[] {
  const entry = fileURLToPath(new URL('./cli.js', import.meta.url));
  if (!import.meta.url.endsWith('.ts')) return [entry, command, ...args];
  const source = entry.replace(/\.js$/, '.ts');
  // process.execPath carries the current runtime forward; Bun runs TypeScript without a loader.
  return (process.versions as { bun?: string }).bun
    ? [source, command, ...args]
    : ['--import', 'tsx', source, command, ...args];
}
