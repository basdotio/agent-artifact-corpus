import { stripVTControlCharacters } from 'node:util';
import stringWidth from 'string-width';

export type Tone = 'normal' | 'muted' | 'accent' | 'good' | 'warn' | 'bad';
export interface Cell {
  text: string;
  tone: Tone;
  selected?: boolean;
  bold?: boolean;
}
export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}
const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
export function safeText(value: string): string {
  return stripVTControlCharacters(value)
    .replace(/[\u0000-\u0008\u000b-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/g, '')
    .replaceAll('\t', '    ');
}
export function clip(value: string, width: number, start = 0): string {
  let position = 0,
    result = '';
  for (const { segment } of segmenter.segment(safeText(value).replaceAll('\n', ' '))) {
    const size = stringWidth(segment);
    if (position >= start && position + size <= start + width) result += segment;
    else if (position < start && position + size > start)
      result += ' '.repeat(position + size - start);
    if (position >= start + width) break;
    position += size;
  }
  return result;
}
export function wrapped(value: string, width: number): string[] {
  if (width < 1) return [];
  return safeText(value)
    .split('\n')
    .flatMap(line => {
      if (!line) return [''];
      const rows: string[] = [];
      let row = '';
      for (const { segment } of segmenter.segment(line)) {
        if (stringWidth(row + segment) > width) {
          rows.push(row);
          row = '';
        }
        row += segment;
      }
      if (row) rows.push(row);
      return rows;
    });
}
export function age(at: number | string | null | undefined, now: number): string {
  if (!at) return 'unknown';
  const seconds = Math.max(
    0,
    Math.floor((now - (typeof at === 'string' ? Date.parse(at) : at)) / 1000),
  );
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m${seconds % 60}s`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d`;
}
export function stateTone(state: string): Tone {
  if (['done', 'ready', 'live', 'COMMITTED'].includes(state)) return 'good';
  if (['blocked', 'QUEUED', 'reconnecting', 'recovering', 'waiting'].includes(state)) return 'warn';
  if (['FAILED', 'error', 'content_unavailable'].includes(state)) return 'bad';
  return 'normal';
}
export function timeLabel(at: number | string): string {
  return new Date(at).toLocaleTimeString([], { hour12: false });
}

/** Cell canvas keeps box/graph geometry deterministic and clips before terminal output. */
export class Canvas {
  readonly rows: Cell[][];
  constructor(
    readonly width: number,
    readonly height: number,
    readonly ascii = false,
  ) {
    this.rows = Array.from({ length: height }, () =>
      Array.from({ length: width }, () => ({ text: ' ', tone: 'normal' as Tone })),
    );
  }
  text(
    x: number,
    y: number,
    value: string,
    tone: Tone = 'normal',
    width = this.width - x,
    selected = false,
    bold = false,
  ): void {
    if (y < 0 || y >= this.height) return;
    const rendered = clip(value, width);
    let offset = 0;
    for (const { segment } of segmenter.segment(rendered)) {
      const size = stringWidth(segment);
      if (x + offset >= 0 && x + offset + size <= this.width && size) {
        this.rows[y]![x + offset] = { text: segment, tone, selected, bold };
        for (let i = 1; i < size; i++)
          this.rows[y]![x + offset + i] = { text: '', tone, selected, bold };
      }
      offset += size;
    }
    if (selected)
      for (let i = offset; i < width && x + i < this.width; i++)
        if (x + i >= 0) this.rows[y]![x + i] = { text: ' ', tone, selected, bold };
  }
  panel(rect: Rect, title: string, focused = false): Rect {
    const { x, y, w, h } = rect;
    const [tl, tr, bl, br, hz, vt] = this.ascii
      ? ['+', '+', '+', '+', '-', '|']
      : ['╭', '╮', '╰', '╯', '─', '│'];
    const tone = focused ? 'accent' : 'muted';
    this.text(x, y, tl! + hz!.repeat(Math.max(0, w - 2)) + tr!, tone, w);
    this.text(x, y + h - 1, bl! + hz!.repeat(Math.max(0, w - 2)) + br!, tone, w);
    for (let row = y + 1; row < y + h - 1; row++) {
      this.text(x, row, vt!, tone, 1);
      this.text(x + w - 1, row, vt!, tone, 1);
    }
    this.text(x + 2, y, ` ${title} `, focused ? 'accent' : 'normal', w - 4, false, true);
    return { x: x + 2, y: y + 1, w: Math.max(0, w - 4), h: Math.max(0, h - 2) };
  }
  lines(rect: Rect, lines: { text: string; tone?: Tone; bold?: boolean }[], offset = 0): void {
    lines
      .slice(offset, offset + rect.h)
      .forEach((line, i) =>
        this.text(rect.x, rect.y + i, line.text, line.tone, rect.w, false, line.bold),
      );
  }
  plain(): string {
    return this.rows
      .map(row =>
        row
          .map(c => c.text)
          .join('')
          .trimEnd(),
      )
      .join('\n');
  }
}

export function markdown(
  text: string,
  width: number,
  horizontal = 0,
): { text: string; tone?: Tone; bold?: boolean }[] {
  let code = false;
  return safeText(text)
    .split('\n')
    .flatMap(line => {
      if (/^\s*(```|~~~)/.test(line)) {
        code = !code;
        return [{ text: code ? `┌ code ${line.trim().slice(3)}` : '└', tone: 'muted' as Tone }];
      }
      if (code) return [{ text: `│ ${clip(line, width - 2, horizontal)}`, tone: 'normal' as Tone }];
      const heading = /^#{1,6}\s/.test(line);
      return wrapped(line.replace(/^#{1,6}\s/, '').replace(/\*\*([^*]+)\*\*/g, '$1'), width).map(
        text => ({
          text,
          tone: heading
            ? ('accent' as Tone)
            : line.startsWith('>')
              ? ('muted' as Tone)
              : ('normal' as Tone),
          bold: heading,
        }),
      );
    });
}
