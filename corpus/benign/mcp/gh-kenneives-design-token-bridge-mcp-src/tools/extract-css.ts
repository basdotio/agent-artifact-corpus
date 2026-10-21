import type { DesignTokens, ColorToken, TypographyToken, ElevationToken } from "../types/tokens.js";

/**
 * Extract design tokens from CSS custom properties.
 * Parses :root, [data-theme], and @media (prefers-color-scheme) blocks.
 */
export function extractTokensFromCSS(cssContent: string): DesignTokens {
  const tokens: DesignTokens = {};
  const vars = parseCustomProperties(cssContent);

  if (vars.size === 0) {
    throw new Error("No CSS custom properties found in the provided CSS.");
  }

  const colors: Record<string, ColorToken> = {};
  const typography: Record<string, TypographyToken> = {};
  const spacing: Record<string, number> = {};
  const radii: Record<string, number> = {};
  const elevation: Record<string, ElevationToken> = {};

  for (const [name, value] of vars) {
    const tokenName = name
      .replace(/^--/, "")
      .replace(/^(color|clr)-/, "")
      .replace(/^(font|type|text)-/, "")
      .replace(/^(space|spacing)-/, "")
      .replace(/^(radius|radii|rounded)-/, "")
      .replace(/^(shadow|elevation)-/, "");

    // Detect category by prefix
    if (name.match(/^--(color|clr|bg|fg|text-color|border-color)/)) {
      const hex = colorToHex(value);
      if (hex) colors[tokenName] = { value: hex };
    } else if (name.match(/^--(font|type|text)/)) {
      const typo = parseTypographyValue(name, value);
      if (typo) {
        const key = tokenName.replace(/^(size|weight|family|height)-?/, "");
        if (key) {
          typography[key] = { ...typography[key], ...typo };
        }
      }
    } else if (name.match(/^--(space|spacing|gap|padding|margin)/)) {
      const px = parseToPixels(value);
      if (px !== null) spacing[tokenName] = px;
    } else if (name.match(/^--(radius|radii|rounded|border-radius)/)) {
      const px = parseToPixels(value);
      if (px !== null) radii[tokenName] = px;
    } else if (name.match(/^--(shadow|elevation)/)) {
      const parsed = parseShadowValue(value);
      if (parsed) elevation[tokenName] = parsed;
    } else {
      // Try to auto-detect by value format
      const hex = colorToHex(value);
      if (hex) {
        colors[tokenName] = { value: hex };
      } else {
        const px = parseToPixels(value);
        if (px !== null) spacing[tokenName] = px;
      }
    }
  }

  if (Object.keys(colors).length > 0) tokens.colors = colors;
  if (Object.keys(typography).length > 0) tokens.typography = typography;
  if (Object.keys(spacing).length > 0) tokens.spacing = spacing;
  if (Object.keys(radii).length > 0) tokens.radii = radii;
  if (Object.keys(elevation).length > 0) tokens.elevation = elevation;

  const hasContent = Object.values(tokens).some((v) => v !== undefined);
  if (!hasContent) {
    throw new Error("CSS custom properties found but none could be mapped to design tokens.");
  }

  return tokens;
}

/**
 * Parse all CSS custom properties from the document.
 * Extracts from :root, html, [data-theme], etc.
 */
function parseCustomProperties(css: string): Map<string, string> {
  const vars = new Map<string, string>();

  // Remove comments
  const cleaned = css.replace(/\/\*[\s\S]*?\*\//g, "");

  // Match property declarations: --name: value;
  const propRegex = /(--[\w-]+)\s*:\s*([^;]+);/g;
  let match;
  while ((match = propRegex.exec(cleaned)) !== null) {
    const name = match[1].trim();
    const value = match[2].trim();
    // Don't overwrite — first declaration wins (light mode / :root)
    if (!vars.has(name)) {
      vars.set(name, value);
    }
  }

  return vars;
}

/** Convert various CSS color formats to hex */
function colorToHex(value: string): string | null {
  // Already hex
  if (/^#[0-9a-fA-F]{3,8}$/.test(value)) {
    return normalizeHex(value);
  }

  // rgb(r, g, b) or rgba(r, g, b, a)
  const rgbMatch = value.match(
    /rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*[\d.]+)?\s*\)/
  );
  if (rgbMatch) {
    const r = parseInt(rgbMatch[1]).toString(16).padStart(2, "0");
    const g = parseInt(rgbMatch[2]).toString(16).padStart(2, "0");
    const b = parseInt(rgbMatch[3]).toString(16).padStart(2, "0");
    return `#${r}${g}${b}`.toUpperCase();
  }

  // hsl(h, s%, l%) — approximate conversion
  const hslMatch = value.match(
    /hsla?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)%\s*,\s*(\d+(?:\.\d+)?)%/
  );
  if (hslMatch) {
    return hslToHex(
      parseFloat(hslMatch[1]),
      parseFloat(hslMatch[2]),
      parseFloat(hslMatch[3])
    );
  }

  return null;
}

function normalizeHex(hex: string): string {
  if (/^#[0-9a-fA-F]{3}$/.test(hex)) {
    const [, r, g, b] = hex;
    return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
  }
  return hex.toUpperCase();
}

function hslToHex(h: number, s: number, l: number): string {
  s /= 100;
  l /= 100;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`.toUpperCase();
}

function parseTypographyValue(
  name: string,
  value: string
): Partial<TypographyToken> | null {
  if (name.includes("size") || name.includes("font-size")) {
    const px = parseToPixels(value);
    if (px !== null) return { fontSize: px };
  }
  if (name.includes("weight") || name.includes("font-weight")) {
    const w = parseInt(value, 10);
    if (!isNaN(w)) return { fontWeight: w } as Partial<TypographyToken>;
  }
  if (name.includes("family") || name.includes("font-family")) {
    // Take the first font in the stack
    const family = value.split(",")[0].replace(/['"]/g, "").trim();
    return { fontFamily: family } as Partial<TypographyToken>;
  }
  if (name.includes("line-height") || name.includes("leading")) {
    const px = parseToPixels(value);
    if (px !== null) return { lineHeight: px } as Partial<TypographyToken>;
  }
  return null;
}

function parseShadowValue(value: string): ElevationToken | null {
  const match = value.match(
    /(-?\d+(?:\.\d+)?)\s*(?:px)?\s+(-?\d+(?:\.\d+)?)\s*(?:px)?\s+(-?\d+(?:\.\d+)?)\s*(?:px)?(?:\s+(-?\d+(?:\.\d+)?)\s*(?:px)?)?\s+(rgba?\([^)]+\)|#[0-9a-fA-F]+)/
  );
  if (!match) return null;

  const x = parseFloat(match[1]);
  const y = parseFloat(match[2]);
  const blur = parseFloat(match[3]);
  const colorStr = match[5];

  let shadowColor = "#000000";
  let shadowOpacity = 1;

  const hex = colorToHex(colorStr);
  if (hex) shadowColor = hex;

  const rgbaAlpha = colorStr.match(/rgba?\([^,]+,[^,]+,[^,]+,\s*([\d.]+)\)/);
  if (rgbaAlpha) shadowOpacity = parseFloat(rgbaAlpha[1]);

  return {
    shadowColor,
    shadowOffset: { x, y },
    shadowRadius: blur,
    shadowOpacity,
  };
}

function parseToPixels(value: string): number | null {
  const match = value.match(/^(-?\d+(?:\.\d+)?)\s*(px|rem|em)?$/);
  if (!match) return null;
  const num = parseFloat(match[1]);
  const unit = match[2] || "px";
  switch (unit) {
    case "px": return num;
    case "rem":
    case "em": return num * 16;
    default: return null;
  }
}
