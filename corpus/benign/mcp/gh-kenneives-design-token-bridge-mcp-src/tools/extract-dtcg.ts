import type { DesignTokens, ColorToken, TypographyToken, ElevationToken, MotionToken } from "../types/tokens.js";

/**
 * W3C Design Tokens Community Group (DTCG) format.
 * Spec: https://design-tokens.github.io/community-group/format/
 *
 * Tokens use $value, $type, $description fields.
 * Groups can be nested. Aliases use "{path.to.token}" syntax.
 */

interface DTCGToken {
  $value: unknown;
  $type?: string;
  $description?: string;
}

/**
 * Extract design tokens from W3C DTCG format JSON.
 */
export function extractTokensFromDTCG(jsonString: string): DesignTokens {
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(jsonString);
  } catch {
    throw new Error("Invalid JSON: could not parse DTCG token file.");
  }

  // Flatten the nested token tree into a flat map
  const flatTokens = new Map<string, DTCGToken>();
  flattenTokens(data, [], flatTokens);

  if (flatTokens.size === 0) {
    throw new Error("No DTCG tokens found (no objects with $value).");
  }

  const tokens: DesignTokens = {};
  const colors: Record<string, ColorToken> = {};
  const typography: Record<string, TypographyToken> = {};
  const spacing: Record<string, number> = {};
  const radii: Record<string, number> = {};
  const elevation: Record<string, ElevationToken> = {};
  const motion: Record<string, MotionToken> = {};

  for (const [path, token] of flatTokens) {
    const resolvedValue = resolveAliases(token.$value, flatTokens);
    const type = token.$type ?? inferType(resolvedValue);
    const name = path.split(".").pop()!;

    switch (type) {
      case "color": {
        if (typeof resolvedValue === "string") {
          const hex = normalizeColor(resolvedValue);
          if (hex) {
            colors[name] = {
              value: hex,
              ...(token.$description ? { description: token.$description } : {}),
            };
          }
        }
        break;
      }
      case "dimension": {
        const px = parseDimension(resolvedValue);
        if (px !== null) {
          const lowerPath = path.toLowerCase();
          if (lowerPath.includes("radius") || lowerPath.includes("corner")) {
            radii[name] = px;
          } else {
            spacing[name] = px;
          }
        }
        break;
      }
      case "fontFamily":
      case "fontSize":
      case "fontWeight":
      case "typography": {
        if (type === "typography" && typeof resolvedValue === "object" && resolvedValue !== null) {
          const comp = resolvedValue as Record<string, unknown>;
          const typo: TypographyToken = {
            fontSize: parseDimension(comp.fontSize) ?? 16,
          };
          if (comp.fontFamily) typo.fontFamily = String(comp.fontFamily);
          if (comp.fontWeight) typo.fontWeight = Number(comp.fontWeight);
          if (comp.lineHeight) typo.lineHeight = parseDimension(comp.lineHeight) ?? undefined;
          if (comp.letterSpacing) typo.letterSpacing = parseDimension(comp.letterSpacing) ?? undefined;
          typography[name] = typo;
        } else if (type === "fontSize") {
          const px = parseDimension(resolvedValue);
          if (px !== null) typography[name] = { ...typography[name], fontSize: px };
        } else if (type === "fontWeight" && typeof resolvedValue === "number") {
          typography[name] = { ...typography[name], fontSize: typography[name]?.fontSize ?? 16, fontWeight: resolvedValue };
        } else if (type === "fontFamily" && typeof resolvedValue === "string") {
          typography[name] = { ...typography[name], fontSize: typography[name]?.fontSize ?? 16, fontFamily: resolvedValue };
        }
        break;
      }
      case "shadow": {
        const shadow = parseShadow(resolvedValue);
        if (shadow) elevation[name] = shadow;
        break;
      }
      case "duration": {
        const ms = parseDuration(resolvedValue);
        if (ms !== null) {
          motion[name] = { duration: ms, easing: "ease" };
        }
        break;
      }
      case "cubicBezier": {
        if (Array.isArray(resolvedValue) && resolvedValue.length === 4) {
          const [x1, y1, x2, y2] = resolvedValue;
          motion[name] = {
            duration: motion[name]?.duration ?? 300,
            easing: `cubic-bezier(${x1}, ${y1}, ${x2}, ${y2})`,
          };
        }
        break;
      }
    }
  }

  if (Object.keys(colors).length > 0) tokens.colors = colors;
  if (Object.keys(typography).length > 0) tokens.typography = typography;
  if (Object.keys(spacing).length > 0) tokens.spacing = spacing;
  if (Object.keys(radii).length > 0) tokens.radii = radii;
  if (Object.keys(elevation).length > 0) tokens.elevation = elevation;
  if (Object.keys(motion).length > 0) tokens.motion = motion;

  const hasContent = Object.values(tokens).some((v) => v !== undefined);
  if (!hasContent) {
    throw new Error("DTCG tokens found but none could be mapped to design tokens.");
  }

  return tokens;
}

function flattenTokens(
  obj: Record<string, unknown>,
  path: string[],
  result: Map<string, DTCGToken>,
  inheritedType?: string
): void {
  // Check if this node has a group-level $type
  const groupType = typeof obj.$type === "string" ? obj.$type : inheritedType;

  for (const [key, value] of Object.entries(obj)) {
    if (key.startsWith("$")) continue; // Skip meta fields

    if (typeof value === "object" && value !== null) {
      const record = value as Record<string, unknown>;
      if ("$value" in record) {
        // This is a token
        const token: DTCGToken = {
          $value: record.$value,
          $type: (record.$type as string) ?? groupType,
          $description: record.$description as string | undefined,
        };
        result.set([...path, key].join("."), token);
      } else {
        // This is a group — recurse
        flattenTokens(record, [...path, key], result, groupType);
      }
    }
  }
}

function resolveAliases(
  value: unknown,
  tokens: Map<string, DTCGToken>,
  depth = 0
): unknown {
  if (depth > 10) return value;
  if (typeof value === "string" && value.startsWith("{") && value.endsWith("}")) {
    const ref = value.slice(1, -1);
    const target = tokens.get(ref);
    if (target) {
      return resolveAliases(target.$value, tokens, depth + 1);
    }
  }
  return value;
}

function inferType(value: unknown): string | undefined {
  if (typeof value === "string") {
    if (/^#[0-9a-fA-F]{3,8}$/.test(value)) return "color";
    if (/^rgba?\(/.test(value)) return "color";
    if (/^\d+(\.\d+)?(px|rem|em)$/.test(value)) return "dimension";
    if (/^\d+(\.\d+)?ms$/.test(value)) return "duration";
  }
  if (typeof value === "object" && value !== null) {
    if ("color" in value && "offsetX" in value) return "shadow";
  }
  return undefined;
}

function normalizeColor(value: string): string | null {
  if (/^#[0-9a-fA-F]{3}$/.test(value)) {
    const [, r, g, b] = value;
    return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
  }
  if (/^#[0-9a-fA-F]{6,8}$/.test(value)) {
    return value.toUpperCase();
  }
  return null;
}

function parseDimension(value: unknown): number | null {
  if (typeof value === "number") return value;
  if (typeof value !== "string") return null;
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

function parseDuration(value: unknown): number | null {
  if (typeof value === "number") return value;
  if (typeof value !== "string") return null;
  const match = value.match(/^(\d+(?:\.\d+)?)\s*ms$/);
  if (match) return parseFloat(match[1]);
  const secMatch = value.match(/^(\d+(?:\.\d+)?)\s*s$/);
  if (secMatch) return parseFloat(secMatch[1]) * 1000;
  return null;
}

function parseShadow(value: unknown): ElevationToken | null {
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;

  const offsetX = parseDimension(v.offsetX) ?? 0;
  const offsetY = parseDimension(v.offsetY) ?? 0;
  const blur = parseDimension(v.blur) ?? 0;
  const color = typeof v.color === "string" ? normalizeColor(v.color) : "#000000";

  return {
    shadowColor: color ?? "#000000",
    shadowOffset: { x: offsetX, y: offsetY },
    shadowRadius: blur,
    shadowOpacity: 1,
  };
}
