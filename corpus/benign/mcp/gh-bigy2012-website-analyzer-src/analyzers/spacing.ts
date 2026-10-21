import type { SpacingAnalysis, WebsiteData } from '../types/website.js';
import { collectStyleValues, extractLengthValues, topFrequent, uniqueSorted } from '../lib/css.js';

export function analyzeSpacing(data: WebsiteData): SpacingAnalysis {
  const marginProps = ['margin-top', 'margin-right', 'margin-bottom', 'margin-left'];
  const paddingProps = ['padding-top', 'padding-right', 'padding-bottom', 'padding-left'];

  const marginVals = extractLengthValues(data.elements, marginProps);
  const paddingVals = extractLengthValues(data.elements, paddingProps);
  const gapVals = extractLengthValues(data.elements, ['gap']);

  const common = topFrequent([...marginVals, ...paddingVals, ...gapVals], 14);
  const scale = uniqueSorted(common);
  const borderRadii = collectStyleValues(data.elements, 'border-radius', 12);

  return {
    margins: formatPxList(topFrequent(marginVals)),
    paddings: formatPxList(topFrequent(paddingVals)),
    gaps: formatPxList(topFrequent(gapVals, 8)),
    scale,
    common,
    borderRadii,
  };
}

export function analyzeShadows(data: WebsiteData): string[] {
  return collectStyleValues(data.elements, 'box-shadow', 12);
}

function formatPxList(values: number[]): string[] {
  return values.map((v) => `${v}px`);
}
