#!/usr/bin/env node

const originalEmitWarning = process.emitWarning;
process.emitWarning = function filteredWarning(...args: Parameters<typeof process.emitWarning>) {
  const warning = args[0];
  const message = warning instanceof Error ? warning.message : String(warning);
  const type =
    warning instanceof Error
      ? warning.name
      : typeof args[1] === 'string'
        ? args[1]
        : typeof args[1] === 'object' && args[1]
          ? args[1].type
          : undefined;
  if (
    type === 'ExperimentalWarning' &&
    message === 'SQLite is an experimental feature and might change at any time'
  )
    return;
  return Reflect.apply(originalEmitWarning, process, args);
} as typeof process.emitWarning;

try {
  await import('./cli-main.js');
} finally {
  process.emitWarning = originalEmitWarning;
}
