import { designTokensSchema } from "../schemas/universal-token-schema.js";
import type { DesignTokens } from "../types/tokens.js";

export interface ValidationResult {
  valid: boolean;
  tokens?: DesignTokens;
  errors?: string[];
}

/**
 * Validate and parse a design tokens object against the universal schema.
 * Returns the parsed tokens if valid, or an array of error messages if not.
 */
export function validateTokens(input: unknown): ValidationResult {
  const result = designTokensSchema.safeParse(input);

  if (result.success) {
    return { valid: true, tokens: result.data as DesignTokens };
  }

  const errors = result.error.issues.map((issue) => {
    const path = issue.path.length > 0 ? issue.path.join(".") : "(root)";
    return `${path}: ${issue.message}`;
  });

  return { valid: false, errors };
}

/**
 * Parse a JSON string into design tokens, validating along the way.
 * Handles JSON parse errors as well as schema validation errors.
 */
export function parseTokensFromString(jsonString: string): ValidationResult {
  let parsed: unknown;
  try {
    parsed = JSON.parse(jsonString);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { valid: false, errors: [`Invalid JSON: ${msg}`] };
  }
  return validateTokens(parsed);
}

/**
 * Normalize a 3-digit hex color to 6-digit.
 * e.g. "#F0A" -> "#FF00AA"
 */
export function normalizeHexColor(hex: string): string {
  if (/^#[0-9a-fA-F]{3}$/.test(hex)) {
    const [, r, g, b] = hex;
    return `#${r}${r}${g}${g}${b}${b}`.toUpperCase();
  }
  return hex.toUpperCase();
}

/**
 * Sanitize tokens by normalizing hex colors and clamping values.
 */
export function sanitizeTokens(tokens: DesignTokens): DesignTokens {
  const result = { ...tokens };

  if (result.colors) {
    const sanitized: typeof result.colors = {};
    for (const [name, token] of Object.entries(result.colors)) {
      sanitized[name] = {
        ...token,
        value: normalizeHexColor(token.value),
      };
    }
    result.colors = sanitized;
  }

  if (result.elevation) {
    const sanitized: typeof result.elevation = {};
    for (const [name, token] of Object.entries(result.elevation)) {
      sanitized[name] = {
        ...token,
        shadowColor: normalizeHexColor(token.shadowColor),
        shadowOpacity: Math.max(0, Math.min(1, token.shadowOpacity)),
      };
    }
    result.elevation = sanitized;
  }

  return result;
}
