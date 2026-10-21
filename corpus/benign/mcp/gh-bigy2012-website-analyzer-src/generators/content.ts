import type { ContentAnalysis, WebsiteData } from '../types/website.js';
import { analyzeContent } from '../lib/dom.js';

export function generateContentDoc(data: WebsiteData, content?: ContentAnalysis): string {
  const analysis = content ?? analyzeContent(data.html, data.title, data.description);

  const lines: string[] = [
    `# Content — ${analysis.title || data.url}`,
    '',
    `Source: ${data.url}`,
    '',
    '## Meta',
    '',
    `- **Title:** ${analysis.title || '_n/a_'}`,
    `- **Description:** ${analysis.description || '_n/a_'}`,
    '',
    '## Counts',
    '',
    `- Links: ${analysis.linkCount}`,
    `- Images: ${analysis.imageCount}`,
    `- Forms: ${analysis.formCount}`,
    `- Buttons: ${analysis.buttonCount}`,
    '',
    '## Landmarks',
    '',
    ...Object.entries(analysis.landmarkCounts).map(([tag, count]) => `- \`<${tag}>\`: ${count}`),
    '',
    '## Heading outline',
    '',
    ...(analysis.headings.length
      ? analysis.headings.map((h) => {
          const match = h.match(/^(h[1-6]):\s*(.*)$/i);
          if (!match) return `- ${h}`;
          const level = Number(match[1].slice(1));
          const indent = '  '.repeat(Math.max(0, level - 1));
          return `${indent}- **${match[1]}:** ${match[2]}`;
        })
      : ['_No headings detected_']),
    '',
  ];

  return lines.join('\n');
}
