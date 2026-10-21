import type { ColorAnalysis, ScrapedElement, WebsiteData } from '../types/website.js';
import { collectColorValues, normalizeColor } from '../lib/css.js';

export function analyzeColors(data: WebsiteData): ColorAnalysis {
  const map = collectColorValues(data.elements, data.cssVariables);
  const all = [...map.entries()]
    .map(([value, meta]) => ({
      value,
      count: meta.count,
      usage: [...meta.usage].slice(0, 8),
    }))
    .sort((a, b) => b.count - a.count);

  const backgrounds = rankByUsage(data.elements, 'background-color');
  const text = rankByUsage(data.elements, 'color');
  const accents = all
    .filter((c) => !backgrounds.some((b) => b.value === c.value) && !text.some((t) => t.value === c.value))
    .slice(0, 12);

  return {
    palette: all.slice(0, 24),
    backgrounds: backgrounds.slice(0, 10),
    text: text.slice(0, 10),
    accents,
    cssVariables: filterColorVars(data.cssVariables),
  };
}

function rankByUsage(elements: ScrapedElement[], prop: string) {
  const map = new Map<string, { count: number; usage: Set<string> }>();
  for (const el of elements) {
    const value = normalizeColor(el.styles[prop] ?? '');
    if (!value) continue;
    const entry = map.get(value) ?? { count: 0, usage: new Set() };
    entry.count += 1;
    entry.usage.add(el.tag);
    map.set(value, entry);
  }
  return [...map.entries()]
    .map(([value, meta]) => ({ value, count: meta.count, usage: [...meta.usage] }))
    .sort((a, b) => b.count - a.count);
}

function filterColorVars(vars: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(vars)) {
    if (/color|bg|background|accent|primary|secondary|muted|border|fill|stroke/i.test(k) || /#|rgb|hsl/.test(v)) {
      out[k] = v;
    }
  }
  return out;
}
