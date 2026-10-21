import type { ComponentsAnalysis, DesignAnalysis, WebsiteData } from '../types/website.js';
import { toDesignTokens } from '../types/website.js';

export function generateReadme(
  data: WebsiteData,
  design: DesignAnalysis,
  components: ComponentsAnalysis,
  files: string[],
): string {
  const tokens = toDesignTokens(design);
  const colorPreview = design.colors.palette
    .slice(0, 8)
    .map((c) => `\`${c.value}\``)
    .join(', ');

  return `# Website Analysis — ${data.title || data.url}

## Overview
- **URL:** ${data.url}
- **Title:** ${data.title || '_n/a_'}
- **Description:** ${data.description || '_n/a_'}
- **Inspected at:** ${data.inspectedAt}

## Snapshot
- Primary / background / text: \`${tokens.colors.primary}\` / \`${tokens.colors.background}\` / \`${tokens.colors.text}\`
- Colors: ${colorPreview || '_none_'}
- Fonts: ${design.typography.fonts
    .slice(0, 4)
    .map((f) => f.family)
    .join(', ') || '_none_'}
- Spacing scale: ${tokens.spacing.scale.map((n) => `${n}px`).join(', ') || '_none_'}
- Components found: buttons ${components.buttons.length}, links ${components.links.length}, cards ${components.cards.length}, nav ${components.navigation.length}

## Generated files
${files.map((f) => `- \`${f}\``).join('\n')}

## How to use
1. Read \`design.md\` for tokens and layout patterns
2. Read \`rule.md\` when prompting an agent to rebuild the UI
3. Read \`component.md\` for concrete component selectors and styles
4. Read \`layout.md\` for structure and responsive breakpoints
5. Read \`content.md\` for title, headings outline, and landmark counts
6. Compare against screenshots in \`screenshots/\` if present

## Notes
This package was produced by **website-analyzer-mcp**. Values are inferred from computed styles and DOM structure; treat them as a strong starting point, not a perfect design-token export.
`;
}
