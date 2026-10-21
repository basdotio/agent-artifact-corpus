import type { DesignTokens, ColorToken } from "../types/tokens.js";

/**
 * Figma Variables REST API response shape (simplified).
 * We handle the actual structure from Figma's GET /v1/files/:key/variables/local
 */
interface FigmaVariablesExport {
  variables?: Record<string, FigmaVariable>;
  variableCollections?: Record<string, FigmaVariableCollection>;
}

interface FigmaVariable {
  id: string;
  name: string;
  resolvedType: "COLOR" | "FLOAT" | "STRING" | "BOOLEAN";
  valuesByMode: Record<string, FigmaValue>;
  description?: string;
}

interface FigmaVariableCollection {
  id: string;
  name: string;
  modes: { modeId: string; name: string }[];
  defaultModeId: string;
}

type FigmaValue =
  | { r: number; g: number; b: number; a: number } // COLOR
  | number // FLOAT
  | string // STRING
  | boolean // BOOLEAN
  | { type: "VARIABLE_ALIAS"; id: string }; // alias

/**
 * Extract design tokens from a Figma Variables export JSON string.
 */
export function extractTokensFromFigmaVariables(jsonString: string): DesignTokens {
  let data: FigmaVariablesExport;
  try {
    data = JSON.parse(jsonString);
  } catch {
    throw new Error("Invalid JSON: could not parse Figma variables export.");
  }

  // Handle both direct format and nested under meta.variables
  const raw = data as any;
  const variables: Record<string, FigmaVariable> =
    data.variables ?? raw.meta?.variables ?? {};
  const collections: Record<string, FigmaVariableCollection> =
    data.variableCollections ?? raw.meta?.variableCollections ?? {};

  if (Object.keys(variables).length === 0) {
    throw new Error("No variables found in the Figma export.");
  }

  // Find the default mode ID (first collection's default, or first mode)
  let defaultModeId: string | undefined;
  for (const collection of Object.values(collections)) {
    defaultModeId = collection.defaultModeId;
    break;
  }

  const tokens: DesignTokens = {};
  const colors: Record<string, ColorToken> = {};
  const spacing: Record<string, number> = {};
  const radii: Record<string, number> = {};

  for (const variable of Object.values(variables)) {
    // Resolve the value for the default mode
    const modeId =
      defaultModeId ?? Object.keys(variable.valuesByMode)[0];
    let value = variable.valuesByMode[modeId];

    // Resolve aliases
    value = resolveAlias(value, variables, modeId, 10);

    // Clean up variable name: "Colors/Primary" → "primary", "Spacing/xs" → "xs"
    const name = normalizeVariableName(variable.name);

    switch (variable.resolvedType) {
      case "COLOR": {
        if (isColorValue(value)) {
          const hex = figmaColorToHex(value as { r: number; g: number; b: number; a: number });
          const category = inferColorCategory(variable.name);
          colors[name] = {
            value: hex,
            ...(variable.description ? { description: variable.description } : {}),
            ...(category ? { category } : {}),
          };
        }
        break;
      }
      case "FLOAT": {
        if (typeof value === "number") {
          const lowerName = variable.name.toLowerCase();
          if (lowerName.includes("radius") || lowerName.includes("corner")) {
            radii[name] = value;
          } else {
            // Default FLOAT to spacing
            spacing[name] = value;
          }
        }
        break;
      }
      // STRING and BOOLEAN are not directly mappable to our token schema
    }
  }

  if (Object.keys(colors).length > 0) tokens.colors = colors;
  if (Object.keys(spacing).length > 0) tokens.spacing = spacing;
  if (Object.keys(radii).length > 0) tokens.radii = radii;

  const hasContent = Object.values(tokens).some((v) => v !== undefined);
  if (!hasContent) {
    throw new Error("Figma variables found but none could be mapped to design tokens.");
  }

  return tokens;
}

function resolveAlias(
  value: FigmaValue,
  variables: Record<string, FigmaVariable>,
  modeId: string,
  maxDepth: number
): FigmaValue {
  if (maxDepth <= 0) return value;
  if (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    value.type === "VARIABLE_ALIAS"
  ) {
    const target = variables[value.id];
    if (target) {
      const targetValue =
        target.valuesByMode[modeId] ?? Object.values(target.valuesByMode)[0];
      return resolveAlias(targetValue, variables, modeId, maxDepth - 1);
    }
  }
  return value;
}

function isColorValue(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    "r" in value &&
    "g" in value &&
    "b" in value
  );
}

function figmaColorToHex(color: { r: number; g: number; b: number; a?: number }): string {
  // Figma colors are 0-1 float range
  const r = Math.round(color.r * 255)
    .toString(16)
    .padStart(2, "0");
  const g = Math.round(color.g * 255)
    .toString(16)
    .padStart(2, "0");
  const b = Math.round(color.b * 255)
    .toString(16)
    .padStart(2, "0");
  return `#${r}${g}${b}`.toUpperCase();
}

function normalizeVariableName(name: string): string {
  return name
    .split("/")
    .pop()! // Take last segment: "Colors/Primary" → "Primary"
    .replace(/\s+/g, "-") // Spaces to hyphens
    .replace(/([a-z])([A-Z])/g, "$1-$2") // camelCase to kebab
    .toLowerCase();
}

function inferColorCategory(
  name: string
): ColorToken["category"] | undefined {
  const lower = name.toLowerCase();
  if (lower.includes("primary")) return "primary";
  if (lower.includes("secondary")) return "secondary";
  if (lower.includes("tertiary")) return "tertiary";
  if (lower.includes("neutral") || lower.includes("gray") || lower.includes("grey"))
    return "neutral";
  if (lower.includes("error") || lower.includes("danger") || lower.includes("destructive"))
    return "error";
  if (lower.includes("surface")) return "surface";
  if (lower.includes("background") || lower.includes("bg")) return "background";
  return undefined;
}
