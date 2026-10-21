import type { DesignAnalysis, WebsiteData } from '../types/website.js';
import { toDesignTokens } from '../types/website.js';

export function generateDesignDoc(data: WebsiteData, design: DesignAnalysis): string {
  const tokens = toDesignTokens(design);
  const radii = design.borderRadii.length ? design.borderRadii : design.spacing.borderRadii;
  const shadows = design.shadows;

  const lines: string[] = [
    `# Design System — ${data.title || data.url}`,
    '',
    `Source: ${data.url}`,
    `Inspected: ${data.inspectedAt}`,
    '',
    '## Tokens (simplified)',
    '',
    '```json',
    JSON.stringify(tokens, null, 2),
    '```',
    '',
    '## Colors',
    '',
    '### Palette',
    ...design.colors.palette.slice(0, 16).map((c) => `- \`${c.value}\` (×${c.count}) — ${c.usage.slice(0, 3).join(', ')}`),
    '',
    '### Backgrounds',
    ...design.colors.backgrounds.slice(0, 8).map((c) => `- \`${c.value}\` (×${c.count})`),
    '',
    '### Text',
    ...design.colors.text.slice(0, 8).map((c) => `- \`${c.value}\` (×${c.count})`),
    '',
    '### Accents',
    ...design.colors.accents.slice(0, 8).map((c) => `- \`${c.value}\` (×${c.count})`),
    '',
    '### CSS Variables',
    ...Object.entries(design.colors.cssVariables)
      .slice(0, 30)
      .map(([k, v]) => `- \`${k}\`: \`${v}\``),
    '',
    '## Typography',
    '',
    '### Fonts',
    ...design.typography.fonts.slice(0, 8).map(
      (f) => `- **${f.family}** (×${f.count}) — weights: ${f.weights.join(', ') || 'n/a'}`,
    ),
    '',
    '### Body',
    `- Family: \`${design.typography.body.fontFamily}\``,
    `- Size: \`${design.typography.body.fontSize}\``,
    `- Weight: \`${design.typography.body.fontWeight}\``,
    `- Line height: \`${design.typography.body.lineHeight}\``,
    '',
    '### Headings',
    ...Object.entries(design.typography.headings).map(
      ([tag, h]) => `- **${tag}**: ${h.fontSize} / ${h.fontWeight} / ${h.fontFamily}`,
    ),
    '',
    '### Type scale',
    design.typography.scale.map((s) => `\`${s}\``).join(', ') || '_none_',
    '',
    '## Spacing',
    '',
    `- Common scale: ${design.spacing.scale.map((n) => `${n}px`).join(', ') || '_none_'}`,
    `- Margins: ${design.spacing.margins.join(', ') || '_none_'}`,
    `- Paddings: ${design.spacing.paddings.join(', ') || '_none_'}`,
    `- Gaps: ${design.spacing.gaps.join(', ') || '_none_'}`,
    '',
    '## Border radius',
    '',
    radii.length ? radii.map((r) => `- \`${r}\``).join('\n') : '_none_',
    '',
    '## Shadows',
    '',
    shadows.length ? shadows.map((s) => `- \`${s}\``).join('\n') : '_none_',
    '',
    '## Layout',
    '',
    `- Flex usages: ${design.layout.flexUsage}`,
    `- Grid usages: ${design.layout.gridUsage}`,
    `- Grid column counts: ${design.layout.columns.join(', ') || '_none_'}`,
    `- Display types: ${Object.entries(design.layout.displayTypes)
      .map(([k, v]) => `${k}(${v})`)
      .join(', ')}`,
    '',
    '### Containers',
    ...design.layout.containers.slice(0, 10).map((c) => `- \`${c.selector}\` max-width: \`${c.maxWidth}\``),
    '',
    '## Responsive',
    '',
    `- Viewport meta: ${design.responsive.viewportMeta ?? '_missing_'}`,
    `- Mobile nav detected: ${design.responsive.hasMobileNav ? 'yes' : 'no'}`,
    `- Fluid images: ${design.responsive.fluidImages ? 'yes' : 'unknown'}`,
    '',
    '### Breakpoints sampled',
    ...design.responsive.breakpoints.map(
      (b) =>
        `- ${b.width}×${b.height}${b.screenshotPath ? ` — screenshot: \`${b.screenshotPath}\`` : ''} — sections: ${b.visibleSections.slice(0, 5).join(', ')}`,
    ),
    '',
    '### Media queries',
    ...design.responsive.mediaQueries.slice(0, 20).map((mq) => `- \`${mq}\``),
    '',
  ];

  return lines.join('\n');
}

export function generateDesignJson(data: WebsiteData, design: DesignAnalysis): string {
  return JSON.stringify(
    {
      url: data.url,
      title: data.title,
      inspectedAt: data.inspectedAt,
      tokens: toDesignTokens(design),
      design,
    },
    null,
    2,
  );
}
