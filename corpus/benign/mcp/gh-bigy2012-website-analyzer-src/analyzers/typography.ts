import type { FontToken, TypographyAnalysis, WebsiteData } from '../types/website.js';

export function analyzeTypography(data: WebsiteData): TypographyAnalysis {
  const fontMap = new Map<string, { count: number; weights: Set<number>; sizes: Set<string> }>();
  const sizeSet = new Set<string>();
  const headings: TypographyAnalysis['headings'] = {};

  for (const el of data.elements) {
    const family = cleanFontFamily(el.styles['font-family'] ?? '');
    if (!family) continue;

    const entry = fontMap.get(family) ?? { count: 0, weights: new Set(), sizes: new Set() };
    entry.count += 1;
    const weight = Number.parseInt(el.styles['font-weight'] ?? '', 10);
    if (!Number.isNaN(weight)) entry.weights.add(weight);
    const size = el.styles['font-size'];
    if (size) {
      entry.sizes.add(size);
      sizeSet.add(size);
    }
    fontMap.set(family, entry);

    if (/^h[1-6]$/.test(el.tag) && !headings[el.tag]) {
      headings[el.tag] = {
        fontSize: el.styles['font-size'] ?? '',
        fontWeight: el.styles['font-weight'] ?? '',
        lineHeight: el.styles['line-height'] ?? '',
        fontFamily: family,
      };
    }
  }

  const fonts: FontToken[] = [...fontMap.entries()]
    .map(([family, meta]) => ({
      family,
      count: meta.count,
      weights: [...meta.weights].sort((a, b) => a - b),
      sizes: [...meta.sizes].sort(compareSize),
    }))
    .sort((a, b) => b.count - a.count);

  const bodyEl =
    data.elements.find((e) => e.tag === 'p') ??
    data.elements.find((e) => e.tag === 'body') ??
    data.elements[0];

  const body = {
    fontSize: bodyEl?.styles['font-size'] ?? '16px',
    fontWeight: bodyEl?.styles['font-weight'] ?? '400',
    lineHeight: bodyEl?.styles['line-height'] ?? 'normal',
    fontFamily: cleanFontFamily(bodyEl?.styles['font-family'] ?? fonts[0]?.family ?? 'sans-serif'),
  };

  return {
    fonts,
    headings,
    body,
    scale: [...sizeSet].sort(compareSize).slice(0, 16),
  };
}

function cleanFontFamily(raw: string): string {
  return raw
    .split(',')[0]
    ?.replace(/["']/g, '')
    .trim() ?? '';
}

function compareSize(a: string, b: string): number {
  const toPx = (v: string) => {
    const n = Number.parseFloat(v);
    if (v.endsWith('rem')) return n * 16;
    if (v.endsWith('em')) return n * 16;
    return n;
  };
  return toPx(a) - toPx(b);
}
