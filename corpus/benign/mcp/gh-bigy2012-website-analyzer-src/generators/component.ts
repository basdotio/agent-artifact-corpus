import type { ComponentsAnalysis, WebsiteData } from '../types/website.js';

export function generateComponentsDoc(data: WebsiteData, components: ComponentsAnalysis): string {
  const sections: Array<[string, typeof components.buttons]> = [
    ['Buttons', components.buttons],
    ['Links', components.links],
    ['Navigation', components.navigation],
    ['Forms', components.forms],
    ['Inputs', components.inputs],
    ['Cards', components.cards],
    ['Other', components.other],
  ];

  const lines: string[] = [
    `# Components — ${data.title || data.url}`,
    '',
    `Source: ${data.url}`,
    '',
  ];

  for (const [title, items] of sections) {
    lines.push(`## ${title}`, '');
    if (!items.length) {
      lines.push('_None detected_', '');
      continue;
    }
    for (const item of items) {
      lines.push(`### \`${item.selector}\` (×${item.count})`);
      lines.push('');
      lines.push('```html');
      lines.push(item.sampleHtml);
      lines.push('```');
      lines.push('');
      lines.push('Styles:');
      for (const [k, v] of Object.entries(item.styles)) {
        lines.push(`- \`${k}\`: \`${v}\``);
      }
      if (item.attributes.length) {
        lines.push(`Attributes: ${item.attributes.join(', ')}`);
      }
      lines.push('');
    }
  }

  return lines.join('\n');
}
