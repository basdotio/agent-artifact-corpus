import type { ScrapedElement } from '../types/website.js';

const COLOR_PROPS = ['color', 'background-color', 'border-color', 'outline-color', 'fill', 'stroke'];

export function collectColorValues(
  elements: ScrapedElement[],
  cssVariables: Record<string, string>,
): Map<string, { count: number; usage: Set<string> }> {
  const map = new Map<string, { count: number; usage: Set<string> }>();

  const add = (raw: string, usage: string) => {
    const normalized = normalizeColor(raw);
    if (!normalized) return;
    const entry = map.get(normalized) ?? { count: 0, usage: new Set() };
    entry.count += 1;
    entry.usage.add(usage);
    map.set(normalized, entry);
  };

  for (const [name, value] of Object.entries(cssVariables)) {
    if (/color|bg|background|accent|primary|secondary|muted|border/i.test(name)) {
      add(value, `var(${name})`);
    }
  }

  for (const el of elements) {
    for (const prop of COLOR_PROPS) {
      const value = el.styles[prop];
      if (value) add(value, `${el.tag}${el.className ? '.' + el.className.split(/\s+/)[0] : ''}:${prop}`);
    }
    const bg = el.styles['background-color'];
    if (bg) add(bg, 'background');
    const color = el.styles.color;
    if (color) add(color, 'text');
  }

  return map;
}

export function normalizeColor(value: string): string | null {
  const v = value.trim().toLowerCase();
  if (!v || v === 'transparent' || v === 'inherit' || v === 'initial' || v === 'currentcolor' || v === 'none') {
    return null;
  }

  const rgba = v.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/);
  if (rgba) {
    const r = Math.round(Number(rgba[1]));
    const g = Math.round(Number(rgba[2]));
    const b = Math.round(Number(rgba[3]));
    const a = rgba[4] !== undefined ? Number(rgba[4]) : 1;
    if (a === 0) return null;
    if (a < 1) return `rgba(${r}, ${g}, ${b}, ${roundAlpha(a)})`;
    return rgbToHex(r, g, b);
  }

  if (/^#[0-9a-f]{3,8}$/i.test(v)) {
    return expandHex(v);
  }

  return v;
}

function roundAlpha(a: number): number {
  return Math.round(a * 100) / 100;
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((n) => n.toString(16).padStart(2, '0')).join('')}`;
}

function expandHex(hex: string): string {
  if (hex.length === 4) {
    return `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
  }
  if (hex.length === 5) {
    return `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`;
  }
  return hex.slice(0, 7);
}

export function extractLengthValues(elements: ScrapedElement[], props: string[]): number[] {
  const values: number[] = [];
  for (const el of elements) {
    for (const prop of props) {
      const raw = el.styles[prop];
      if (!raw) continue;
      const px = parsePx(raw);
      if (px !== null && px > 0 && px < 500) values.push(px);
    }
  }
  return values;
}

export function parsePx(value: string): number | null {
  const m = value.trim().match(/^(-?[\d.]+)px$/);
  if (!m) return null;
  return Math.round(Number(m[1]) * 100) / 100;
}

export function uniqueSorted(values: number[]): number[] {
  return [...new Set(values.map((v) => Math.round(v)))].sort((a, b) => a - b);
}

export function topFrequent(values: number[], limit = 12): number[] {
  const counts = new Map<number, number>();
  for (const v of values) {
    const key = Math.round(v);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0] - b[0])
    .slice(0, limit)
    .map(([v]) => v)
    .sort((a, b) => a - b);
}

/** Collect distinct non-empty CSS values for a property, ranked by frequency. */
export function collectStyleValues(elements: ScrapedElement[], prop: string, limit = 16): string[] {
  const counts = new Map<string, number>();
  for (const el of elements) {
    const raw = (el.styles[prop] ?? '').trim();
    if (!raw || raw === 'none' || raw === '0px' || raw === 'rgba(0, 0, 0, 0)') continue;
    counts.set(raw, (counts.get(raw) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([value]) => value);
}
