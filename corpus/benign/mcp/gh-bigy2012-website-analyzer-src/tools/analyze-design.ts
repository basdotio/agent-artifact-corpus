import { analyzeColors } from '../analyzers/color.js';
import { analyzeTypography } from '../analyzers/typography.js';
import { analyzeSpacing, analyzeShadows } from '../analyzers/spacing.js';
import { analyzeLayout } from '../analyzers/layout.js';
import { analyzeComponents } from '../analyzers/component.js';
import type { DesignAnalysis, WebsiteData } from '../types/website.js';
import { toDesignTokens } from '../types/website.js';
import { inspectPage } from './inspect.js';

export async function analyzeDesign(urlOrData: string | WebsiteData): Promise<{
  url: string;
  title: string;
  tokens: ReturnType<typeof toDesignTokens>;
  design: Omit<DesignAnalysis, 'responsive'> & { components: ReturnType<typeof analyzeComponents> };
}> {
  const data = typeof urlOrData === 'string' ? (await inspectPage(urlOrData)).data : urlOrData;
  const spacing = analyzeSpacing(data);
  const shadows = analyzeShadows(data);
  const components = analyzeComponents(data);

  const designCore = {
    colors: analyzeColors(data),
    typography: analyzeTypography(data),
    spacing,
    layout: analyzeLayout(data),
    borderRadii: spacing.borderRadii,
    shadows,
    components,
  };

  // tokens helper expects full DesignAnalysis including responsive — use empty responsive stub
  const tokens = toDesignTokens({
    ...designCore,
    responsive: {
      breakpoints: [],
      mediaQueries: [],
      hasMobileNav: false,
      fluidImages: false,
      viewportMeta: null,
    },
  });

  return {
    url: data.url,
    title: data.title,
    tokens,
    design: designCore,
  };
}
