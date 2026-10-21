import type { DesignAnalysis, WebsiteData } from '../types/website.js';
import { toDesignTokens } from '../types/website.js';

export function generateRulesDoc(data: WebsiteData, design: DesignAnalysis): string {
  const tokens = toDesignTokens(design);
  const primaryFont = tokens.typography.fontFamily;
  const bodySize = tokens.typography.baseSize;
  const spacing = tokens.spacing.scale;
  const bg = tokens.colors.background;
  const text = tokens.colors.text;
  const accent = tokens.colors.primary;
  const radii = design.borderRadii.length ? design.borderRadii : design.spacing.borderRadii;

  return `# Cursor Rules — cloned from ${data.title || data.url}

Use these rules when rebuilding or extending UI inspired by ${data.url}.

## Visual direction
- Background default: \`${bg}\`
- Body text: \`${text}\`
- Accent / CTA: \`${accent}\`
- Primary font: \`${primaryFont}\`
- Base font size: \`${bodySize}\`
- Body line-height: \`${design.typography.body.lineHeight}\`
- Border radii observed: ${radii.slice(0, 6).map((r) => `\`${r}\``).join(', ') || '_none_'}
- Shadows observed: ${design.shadows.slice(0, 4).map((s) => `\`${s}\``).join(', ') || '_none_'}

## Do
- Prefer the extracted spacing scale: ${spacing.map((n) => `${n}px`).join(', ')}
- Keep heading hierarchy consistent with observed sizes:
${Object.entries(design.typography.headings)
  .map(([tag, h]) => `  - ${tag}: ${h.fontSize} / weight ${h.fontWeight}`)
  .join('\n') || '  - (no headings detected)'}
- Use flex/grid patterns similar to the source (flex≈${design.layout.flexUsage}, grid≈${design.layout.gridUsage})
- Respect responsive breakpoints around: ${design.responsive.breakpoints.map((b) => `${b.width}px`).join(', ')}

## Don't
- Do not invent a purple-on-white default theme unless the source palette clearly uses it
- Do not flatten the page into generic card grids if the source layout is section-based
- Do not replace the primary typeface with Inter/Roboto/Arial unless they appear in the source
- Do not ignore mobile nav patterns when \`hasMobileNav\` is true (${design.responsive.hasMobileNav})

## Component guidance
- Buttons should follow observed padding, radius, and contrast from the source button styles
- Navigation should mirror landmark structure: ${design.layout.sections
    .filter((s) => s.tag === 'nav' || s.tag === 'header')
    .map((s) => s.className || s.tag)
    .slice(0, 5)
    .join(', ') || 'header/nav'}
- Forms/inputs should reuse the source border radius and focus treatment when available

## Output expectations
- Match spacing rhythm before adding decorative effects
- Prefer CSS variables when the source exposes them
- Screenshots under \`output/\` are the visual source of truth when docs conflict with memory
`;
}
