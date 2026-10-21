import type { LayoutAnalysis, WebsiteData } from '../types/website.js';

export function analyzeLayout(data: WebsiteData): LayoutAnalysis {
  const displayTypes: Record<string, number> = {};
  let flexUsage = 0;
  let gridUsage = 0;
  const containers: LayoutAnalysis['containers'] = [];
  const columns = new Set<number>();

  for (const el of data.elements) {
    const display = (el.styles.display ?? '').trim();
    if (display) displayTypes[display] = (displayTypes[display] ?? 0) + 1;
    if (display === 'flex' || display === 'inline-flex') flexUsage += 1;
    if (display === 'grid' || display === 'inline-grid') {
      gridUsage += 1;
      const cols = el.styles['grid-template-columns'];
      if (cols && cols !== 'none') {
        const count = cols.trim().split(/\s+/).filter(Boolean).length;
        if (count > 0) columns.add(count);
      }
    }

    const cls = el.className.toLowerCase();
    if (/container|wrapper|content|max-w/.test(cls) || el.styles['max-width']) {
      const maxWidth = el.styles['max-width'];
      if (maxWidth && maxWidth !== 'none') {
        containers.push({
          selector: el.id ? `#${el.id}` : `${el.tag}${cls ? '.' + cls.split(/\s+/)[0] : ''}`,
          maxWidth,
          width: el.styles.width ?? '',
        });
      }
    }
  }

  const sections = data.elements
    .filter((e) => ['header', 'nav', 'main', 'section', 'article', 'aside', 'footer'].includes(e.tag))
    .slice(0, 30)
    .map((e) => ({
      tag: e.tag,
      className: e.className.split(/\s+/).filter(Boolean).slice(0, 3).join(' '),
      role: e.role ?? '',
    }));

  return {
    displayTypes,
    flexUsage,
    gridUsage,
    containers: dedupeContainers(containers).slice(0, 20),
    columns: [...columns].sort((a, b) => a - b),
    sections,
  };
}

function dedupeContainers(items: LayoutAnalysis['containers']) {
  const seen = new Set<string>();
  return items.filter((c) => {
    const key = `${c.selector}|${c.maxWidth}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
