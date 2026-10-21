import { requireThat } from './domain.js';

export function applyUnifiedPatch(body: string, patch: string): string {
  const rows = patch.replaceAll('\r\n', '\n').split('\n');
  requireThat(
    rows.filter(row => row.startsWith('--- ')).length <= 1 &&
      rows.filter(row => row.startsWith('+++ ')).length <= 1,
    'PATCH_REJECTED',
    'A patch may contain only one file section.',
  );
  requireThat(
    !rows.some(row => /^(rename (from|to)|new file mode|deleted file mode)/.test(row)),
    'PATCH_REJECTED',
    'File creation, deletion, and rename patches are not supported.',
  );
  const source = body.split('\n');
  const output: string[] = [];
  let sourceIndex = 0;
  let index = 0;
  while (index < rows.length && !rows[index]!.startsWith('@@ ')) index++;
  requireThat(index < rows.length, 'PATCH_REJECTED', 'The unified patch contains no hunks.');
  while (index < rows.length) {
    const header = rows[index++]!;
    const match = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/.exec(header);
    requireThat(match, 'PATCH_REJECTED', 'A patch hunk header is invalid.');
    const oldStart = Number(match[1]) - 1;
    requireThat(
      oldStart >= sourceIndex && oldStart <= source.length,
      'PATCH_REJECTED',
      'A patch hunk is out of order or out of range.',
    );
    output.push(...source.slice(sourceIndex, oldStart));
    sourceIndex = oldStart;
    let removed = 0;
    let added = 0;
    while (index < rows.length && !rows[index]!.startsWith('@@ ')) {
      const row = rows[index++]!;
      if (row === '\\ No newline at end of file' || (index === rows.length && row === '')) continue;
      const marker = row[0];
      const text = row.slice(1);
      requireThat(
        marker === ' ' || marker === '+' || marker === '-',
        'PATCH_REJECTED',
        'A patch hunk line is invalid.',
      );
      if (marker === ' ' || marker === '-') {
        requireThat(
          source[sourceIndex] === text,
          'PATCH_REJECTED',
          'Patch context does not exactly match the claimed revision.',
        );
        if (marker === ' ') output.push(text);
        sourceIndex++;
        removed++;
      }
      if (marker === '+') {
        output.push(text);
        added++;
      }
    }
    requireThat(
      removed === Number(match[2] ?? 1) && added === Number(match[4] ?? 1),
      'PATCH_REJECTED',
      'Patch hunk counts do not match its header.',
    );
  }
  output.push(...source.slice(sourceIndex));
  return output.join('\n');
}

export interface OutlineItem {
  level: number;
  heading: string;
  path: string[];
  startLine: number;
  endLine: number;
}
export function outline(body: string): OutlineItem[] {
  const lines = body.split('\n');
  const items: OutlineItem[] = [];
  const stack: string[] = [];
  let fence: string | undefined;
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index]!;
    const marker = /^ {0,3}(```+|~~~+)/.exec(line)?.[1];
    if (marker) {
      if (!fence) fence = marker[0];
      else if (marker[0] === fence) fence = undefined;
      continue;
    }
    if (fence) continue;
    const atx = /^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
    const setext = index + 1 < lines.length ? /^ {0,3}(=+|-+)\s*$/.exec(lines[index + 1]!) : null;
    const level = atx
      ? atx[1]!.length
      : setext && line.trim()
        ? setext[1]![0] === '='
          ? 1
          : 2
        : 0;
    if (!level) continue;
    const heading = (atx ? atx[2] : line.trim())!;
    stack.length = level - 1;
    stack[level - 1] = heading;
    items.push({ level, heading, path: [...stack], startLine: index + 1, endLine: lines.length });
    if (!atx) index++;
  }
  for (let index = 0; index < items.length; index++) {
    const next = items.slice(index + 1).find(item => item.level <= items[index]!.level);
    if (next) items[index]!.endLine = next.startLine - 1;
  }
  return items;
}
