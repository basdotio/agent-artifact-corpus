export interface ColorToken {
  value: string;
  count: number;
  usage: string[];
}

export interface ColorAnalysis {
  palette: ColorToken[];
  backgrounds: ColorToken[];
  text: ColorToken[];
  accents: ColorToken[];
  cssVariables: Record<string, string>;
}

export interface FontToken {
  family: string;
  count: number;
  weights: number[];
  sizes: string[];
}

export interface TypographyAnalysis {
  fonts: FontToken[];
  headings: Record<string, { fontSize: string; fontWeight: string; lineHeight: string; fontFamily: string }>;
  body: { fontSize: string; fontWeight: string; lineHeight: string; fontFamily: string };
  scale: string[];
}

export interface SpacingAnalysis {
  margins: string[];
  paddings: string[];
  gaps: string[];
  scale: number[];
  common: number[];
  borderRadii: string[];
}

export interface LayoutAnalysis {
  displayTypes: Record<string, number>;
  flexUsage: number;
  gridUsage: number;
  containers: Array<{ selector: string; maxWidth: string; width: string }>;
  columns: number[];
  sections: Array<{ tag: string; className: string; role: string }>;
}

export interface ComponentInfo {
  name: string;
  type: string;
  selector: string;
  count: number;
  sampleHtml: string;
  styles: Record<string, string>;
  attributes: string[];
}

export interface ComponentsAnalysis {
  buttons: ComponentInfo[];
  links: ComponentInfo[];
  forms: ComponentInfo[];
  cards: ComponentInfo[];
  navigation: ComponentInfo[];
  inputs: ComponentInfo[];
  other: ComponentInfo[];
}

export interface BreakpointSnapshot {
  width: number;
  height: number;
  screenshotPath?: string;
  layoutShift: boolean;
  visibleSections: string[];
}

export interface ResponsiveAnalysis {
  breakpoints: BreakpointSnapshot[];
  mediaQueries: string[];
  hasMobileNav: boolean;
  fluidImages: boolean;
  viewportMeta: string | null;
}

export interface DesignAnalysis {
  colors: ColorAnalysis;
  typography: TypographyAnalysis;
  spacing: SpacingAnalysis;
  layout: LayoutAnalysis;
  responsive: ResponsiveAnalysis;
  borderRadii: string[];
  shadows: string[];
}

/** Simplified token view matching the docs example shape. */
export interface DesignTokens {
  colors: {
    primary: string;
    background: string;
    text: string;
  };
  typography: {
    fontFamily: string;
    baseSize: string;
  };
  spacing: {
    base: number;
    scale: number[];
  };
}

export function toDesignTokens(design: DesignAnalysis): DesignTokens {
  const background = design.colors.backgrounds[0]?.value ?? '#ffffff';
  const text = design.colors.text[0]?.value ?? '#111827';
  const primary =
    design.colors.accents[0]?.value ??
    design.colors.palette.find((c) => c.value !== background && c.value !== text)?.value ??
    design.colors.palette[0]?.value ??
    '#2563eb';

  const scale =
    design.spacing.scale.length > 0 ? design.spacing.scale : design.spacing.common.length > 0 ? design.spacing.common : [4, 8, 12, 16, 24, 32, 48, 64];

  return {
    colors: { primary, background, text },
    typography: {
      fontFamily: design.typography.body.fontFamily || design.typography.fonts[0]?.family || 'sans-serif',
      baseSize: design.typography.body.fontSize || '16px',
    },
    spacing: {
      base: scale[0] ?? 4,
      scale,
    },
  };
}

export interface HeadingSummary {
  level: number;
  text: string;
  tag: string;
}

export interface LinkSummary {
  href: string;
  text: string;
}

export interface ImageSummary {
  src: string;
  alt: string;
}

export interface ButtonSummary {
  text: string;
  type: string;
  selector: string;
}

export interface FormSummary {
  action: string;
  method: string;
  fieldCount: number;
  id: string;
}

/** Structured inspect payload for `inspect_page`. */
export interface PageInspectResult {
  url: string;
  title: string;
  description: string;
  headings: HeadingSummary[];
  links: LinkSummary[];
  images: ImageSummary[];
  buttons: ButtonSummary[];
  forms: FormSummary[];
  semanticElements: Record<string, number>;
  inspectedAt: string;
}

/** Content outline used by `content.md`. */
export interface ContentAnalysis {
  title: string;
  description: string;
  headings: string[];
  landmarkCounts: Record<string, number>;
  linkCount: number;
  imageCount: number;
  formCount: number;
  buttonCount: number;
}

export interface ScrapedElement {
  tag: string;
  id: string;
  className: string;
  text: string;
  href?: string;
  role?: string;
  styles: Record<string, string>;
  rect: { x: number; y: number; width: number; height: number };
}

export interface WebsiteData {
  url: string;
  title: string;
  description: string;
  html: string;
  cssVariables: Record<string, string>;
  stylesheets: string[];
  elements: ScrapedElement[];
  screenshotPath?: string;
  inspectedAt: string;
}

export interface GeneratedDocs {
  outputDir: string;
  files: string[];
}
