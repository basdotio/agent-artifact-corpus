import type { LayoutAnalysis, ResponsiveAnalysis, WebsiteData } from '../types/website.js';

export function generateLayoutDoc(
  data: WebsiteData,
  layout: LayoutAnalysis,
  responsive: ResponsiveAnalysis,
): string {
  const lines: string[] = [
    `# Layout — ${data.title || data.url}`,
    '',
    `Source: ${data.url}`,
    '',
    '## Structure',
    '',
    `- Flex usages: ${layout.flexUsage}`,
    `- Grid usages: ${layout.gridUsage}`,
    `- Grid column patterns: ${layout.columns.join(', ') || '_none_'}`,
    '',
    '### Display types',
    ...Object.entries(layout.displayTypes)
      .sort((a, b) => b[1] - a[1])
      .map(([display, count]) => `- \`${display}\`: ${count}`),
    '',
    '### Containers',
    ...(layout.containers.length
      ? layout.containers.map(
          (c) => `- \`${c.selector}\` — max-width: \`${c.maxWidth}\`${c.width ? `, width: \`${c.width}\`` : ''}`,
        )
      : ['_None detected_']),
    '',
    '### Landmarks / sections',
    ...(layout.sections.length
      ? layout.sections.map((s) => `- \`<${s.tag}>\`${s.className ? ` .${s.className}` : ''}${s.role ? ` role=${s.role}` : ''}`)
      : ['_None detected_']),
    '',
    '## Responsive',
    '',
    `- Viewport meta: ${responsive.viewportMeta ?? '_missing_'}`,
    `- Mobile nav: ${responsive.hasMobileNav ? 'detected' : 'not detected'}`,
    `- Fluid images: ${responsive.fluidImages ? 'likely' : 'unknown'}`,
    '',
    '### Sampled viewports',
    ...responsive.breakpoints.map((b) => {
      const shot = b.screenshotPath ? ` — \`${b.screenshotPath}\`` : '';
      const sections = b.visibleSections.slice(0, 8).join(', ') || '_none_';
      return `- **${b.width}×${b.height}**${shot}\n  - Visible: ${sections}`;
    }),
    '',
    '### Media queries',
    ...(responsive.mediaQueries.length
      ? responsive.mediaQueries.slice(0, 30).map((mq) => `- \`${mq}\``)
      : ['_None extracted_']),
    '',
  ];

  return lines.join('\n');
}
