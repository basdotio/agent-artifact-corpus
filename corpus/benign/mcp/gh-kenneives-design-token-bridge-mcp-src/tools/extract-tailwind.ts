import type { DesignTokens, ColorToken, TypographyToken } from "../types/tokens.js";

/**
 * Extract design tokens from a Tailwind config file's text content.
 *
 * Strategy: We evaluate the config in a sandboxed way by extracting the
 * theme object. We support both `module.exports = { theme: ... }` (CJS)
 * and `export default { theme: ... }` (ESM) patterns, plus the
 * `defineConfig` wrapper from Tailwind v4.
 *
 * We do NOT use Babel/AST parsing — instead we use a safe regex + JSON
 * extraction approach that handles the vast majority of real-world configs.
 */

export function extractTokensFromTailwind(configContent: string): DesignTokens {
  const themeObj = extractThemeObject(configContent);
  if (!themeObj) {
    throw new Error(
      "Could not extract theme from Tailwind config. Ensure the config exports a theme or theme.extend object."
    );
  }

  const tokens: DesignTokens = {};

  // Colors
  const colors = themeObj.extend?.colors ?? themeObj.colors;
  if (colors && typeof colors === "object") {
    tokens.colors = extractColors(colors);
  }

  // Typography (fontSize)
  const fontSize = themeObj.extend?.fontSize ?? themeObj.fontSize;
  if (fontSize && typeof fontSize === "object") {
    tokens.typography = extractTypography(fontSize);
  }

  // Font family — merge into typography if present
  const fontFamily = themeObj.extend?.fontFamily ?? themeObj.fontFamily;
  if (fontFamily && typeof fontFamily === "object") {
    if (!tokens.typography) tokens.typography = {};
    for (const [name, value] of Object.entries(fontFamily)) {
      const family = Array.isArray(value) ? value[0] : String(value);
      // Create or update a typography entry for this font family
      tokens.typography[`font-${name}`] = {
        fontFamily: family,
        fontSize: 16, // default base size
      };
    }
  }

  // Spacing
  const spacing = themeObj.extend?.spacing ?? themeObj.spacing;
  if (spacing && typeof spacing === "object") {
    tokens.spacing = extractNumericMap(spacing);
  }

  // Border radius -> radii
  const borderRadius = themeObj.extend?.borderRadius ?? themeObj.borderRadius;
  if (borderRadius && typeof borderRadius === "object") {
    tokens.radii = extractNumericMap(borderRadius);
  }

  // Box shadow -> elevation
  const boxShadow = themeObj.extend?.boxShadow ?? themeObj.boxShadow;
  if (boxShadow && typeof boxShadow === "object") {
    tokens.elevation = extractElevation(boxShadow);
  }

  // Ensure we have at least one category
  const hasContent = Object.values(tokens).some((v) => v !== undefined);
  if (!hasContent) {
    throw new Error("Tailwind config theme contained no extractable token values.");
  }

  return tokens;
}

/**
 * Extract the theme object from config text using static analysis only.
 * No code execution (no eval/Function) — uses regex + JSON parsing.
 */
function extractThemeObject(content: string): Record<string, any> | null {
  // Strip TypeScript type annotations and imports for cleaner parsing
  const cleaned = content
    .replace(/import\s+.*?from\s+['"].*?['"]\s*;?\n?/g, "")
    .replace(/import\s+type\s+.*?\n/g, "")
    .replace(/:\s*Config\b/g, "")
    .replace(/satisfies\s+Config\b/g, "")
    .replace(/as\s+const\b/g, "")
    .replace(/require\s*\(\s*['"].*?['"]\s*\)/g, "{}");

  return extractThemeViaRegex(cleaned);
}

function extractThemeViaRegex(content: string): Record<string, any> | null {
  // Try to find and extract a balanced theme: { ... } block
  const themeBlock = extractBalancedBlock(content, /theme\s*:\s*\{/);
  if (themeBlock) {
    try {
      const relaxed = relaxJSON(themeBlock);
      return JSON.parse(relaxed);
    } catch {
      // Fall through to simpler patterns
    }
  }

  // Try export default { ... } or module.exports = { ... } as a whole config
  const configBlock = extractBalancedBlock(
    content,
    /(?:export\s+default|module\.exports\s*=)\s*(?:defineConfig\s*\(\s*)?\{/
  );
  if (configBlock) {
    try {
      const relaxed = relaxJSON(configBlock);
      const parsed = JSON.parse(relaxed);
      return parsed.theme || parsed;
    } catch {
      // Fall through
    }
  }

  return null;
}

/** Extract a balanced { ... } block starting at the match of `startPattern`. */
function extractBalancedBlock(content: string, startPattern: RegExp): string | null {
  const match = content.match(startPattern);
  if (!match || match.index === undefined) return null;

  // Find the opening brace position
  const braceStart = content.indexOf("{", match.index);
  if (braceStart === -1) return null;

  let depth = 0;
  for (let i = braceStart; i < content.length; i++) {
    if (content[i] === "{") depth++;
    else if (content[i] === "}") depth--;
    if (depth === 0) {
      return content.slice(braceStart, i + 1);
    }
  }
  return null;
}

/** Convert JS object literal syntax to valid JSON */
function relaxJSON(str: string): string {
  return (
    str
      // Remove comments
      .replace(/\/\/.*$/gm, "")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      // Quote unquoted keys
      .replace(/(?<=[{,]\s*)(\w[\w-]*)\s*:/g, '"$1":')
      // Single quotes to double quotes (simple cases)
      .replace(/'/g, '"')
      // Remove trailing commas
      .replace(/,\s*([}\]])/g, "$1")
  );
}

function extractColors(
  obj: Record<string, unknown>,
  prefix = ""
): Record<string, ColorToken> {
  const result: Record<string, ColorToken> = {};

  for (const [key, value] of Object.entries(obj)) {
    const name = prefix ? `${prefix}-${key}` : key;

    if (typeof value === "string" && isHexLike(value)) {
      result[name] = { value: normalizeToHex(value) };
    } else if (typeof value === "object" && value !== null) {
      // Nested color object like gray: { 50: '#...', 100: '#...' }
      Object.assign(result, extractColors(value as Record<string, unknown>, name));
    }
    // Skip CSS variable references, functions, etc.
  }

  return result;
}

function extractTypography(
  fontSize: Record<string, unknown>
): Record<string, TypographyToken> {
  const result: Record<string, TypographyToken> = {};

  for (const [name, value] of Object.entries(fontSize)) {
    if (typeof value === "string") {
      // Simple: "1rem" or "16px"
      const px = parseToPixels(value);
      if (px !== null) {
        result[name] = { fontSize: px };
      }
    } else if (Array.isArray(value)) {
      // Tailwind format: ["1rem", { lineHeight: "1.5rem" }] or ["1rem", "1.5rem"]
      const px = parseToPixels(String(value[0]));
      if (px !== null) {
        const token: TypographyToken = { fontSize: px };
        if (typeof value[1] === "string") {
          const lh = parseToPixels(value[1]);
          if (lh !== null) token.lineHeight = lh;
        } else if (typeof value[1] === "object" && value[1] !== null) {
          const opts = value[1] as Record<string, string>;
          if (opts.lineHeight) {
            const lh = parseToPixels(opts.lineHeight);
            if (lh !== null) token.lineHeight = lh;
          }
          if (opts.letterSpacing) {
            const ls = parseToPixels(opts.letterSpacing);
            if (ls !== null) token.letterSpacing = ls;
          }
          if (opts.fontWeight) {
            const fw = parseInt(opts.fontWeight, 10);
            if (!isNaN(fw)) token.fontWeight = fw;
          }
        }
        result[name] = token;
      }
    }
  }

  return result;
}

function extractNumericMap(obj: Record<string, unknown>): Record<string, number> {
  const result: Record<string, number> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === "number") {
      result[key] = value;
    } else if (typeof value === "string") {
      const px = parseToPixels(value);
      if (px !== null) result[key] = px;
    }
  }
  return result;
}

function extractElevation(
  boxShadow: Record<string, unknown>
): Record<string, { shadowColor: string; shadowOffset: { x: number; y: number }; shadowRadius: number; shadowOpacity: number }> {
  const result: Record<string, any> = {};
  for (const [name, value] of Object.entries(boxShadow)) {
    if (typeof value !== "string") continue;
    const parsed = parseShadow(value);
    if (parsed) result[name] = parsed;
  }
  return result;
}

function parseShadow(shadow: string) {
  // Parse: "0 2px 4px rgba(0,0,0,0.1)" or "0 2px 4px #00000019"
  const match = shadow.match(
    /(-?\d+(?:\.\d+)?)\s*(?:px)?\s+(-?\d+(?:\.\d+)?)\s*(?:px)?\s+(-?\d+(?:\.\d+)?)\s*(?:px)?(?:\s+(-?\d+(?:\.\d+)?)\s*(?:px)?)?\s+(rgba?\([^)]+\)|#[0-9a-fA-F]+)/
  );
  if (!match) return null;

  const x = parseFloat(match[1]);
  const y = parseFloat(match[2]);
  const blur = parseFloat(match[3]);
  const colorStr = match[5];

  let shadowColor = "#000000";
  let shadowOpacity = 1;

  if (colorStr.startsWith("rgba")) {
    const rgba = colorStr.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\)/);
    if (rgba) {
      const r = parseInt(rgba[1]).toString(16).padStart(2, "0");
      const g = parseInt(rgba[2]).toString(16).padStart(2, "0");
      const b = parseInt(rgba[3]).toString(16).padStart(2, "0");
      shadowColor = `#${r}${g}${b}`.toUpperCase();
      shadowOpacity = rgba[4] ? parseFloat(rgba[4]) : 1;
    }
  } else if (colorStr.startsWith("#")) {
    shadowColor = colorStr.toUpperCase();
    // 8-digit hex: last 2 chars are alpha
    if (shadowColor.length === 9) {
      const alpha = parseInt(shadowColor.slice(7, 9), 16) / 255;
      shadowColor = shadowColor.slice(0, 7);
      shadowOpacity = Math.round(alpha * 100) / 100;
    }
  }

  return {
    shadowColor,
    shadowOffset: { x, y },
    shadowRadius: blur,
    shadowOpacity,
  };
}

function isHexLike(value: string): boolean {
  return /^#[0-9a-fA-F]{3,8}$/.test(value);
}

function normalizeToHex(value: string): string {
  if (/^#[0-9a-fA-F]{3}$/.test(value)) {
    const [, r, g, b] = value;
    return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
  }
  return value.toUpperCase();
}

/** Convert rem/px/em strings to pixel numbers. Base: 16px = 1rem. */
function parseToPixels(value: string): number | null {
  const match = value.match(/^(-?\d+(?:\.\d+)?)\s*(px|rem|em)?$/);
  if (!match) return null;
  const num = parseFloat(match[1]);
  const unit = match[2] || "px";
  switch (unit) {
    case "px":
      return num;
    case "rem":
    case "em":
      return num * 16;
    default:
      return null;
  }
}
