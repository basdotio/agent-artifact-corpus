import type { DesignTokens } from "../types/tokens.js";

export interface ContrastResult {
  pair: string;
  foreground: string;
  background: string;
  ratio: number;
  aa: { normalText: boolean; largeText: boolean };
  aaa: { normalText: boolean; largeText: boolean };
}

export interface ContrastReport {
  level: "AA" | "AAA";
  total: number;
  passing: number;
  failing: number;
  results: ContrastResult[];
}

/**
 * Validate contrast ratios between color pairs in design tokens.
 */
export function validateContrast(
  tokens: DesignTokens,
  level: "AA" | "AAA" = "AA"
): ContrastReport {
  if (!tokens.colors || Object.keys(tokens.colors).length < 2) {
    return { level, total: 0, passing: 0, failing: 0, results: [] };
  }

  const results: ContrastResult[] = [];

  // Check semantic pairs (primary/onPrimary, surface/onSurface, etc.)
  const pairs = findSemanticPairs(tokens.colors);

  // If no semantic pairs found, check all fg/bg combinations
  if (pairs.length === 0) {
    const entries = Object.entries(tokens.colors);
    for (let i = 0; i < entries.length; i++) {
      for (let j = i + 1; j < entries.length; j++) {
        pairs.push({
          name: `${entries[i][0]}/${entries[j][0]}`,
          fg: entries[i][1].value,
          bg: entries[j][1].value,
        });
      }
    }
  }

  for (const pair of pairs) {
    const ratio = contrastRatio(pair.fg, pair.bg);
    results.push({
      pair: pair.name,
      foreground: pair.fg,
      background: pair.bg,
      ratio: Math.round(ratio * 100) / 100,
      aa: {
        normalText: ratio >= 4.5,
        largeText: ratio >= 3,
      },
      aaa: {
        normalText: ratio >= 7,
        largeText: ratio >= 4.5,
      },
    });
  }

  const passing = results.filter((r) => {
    if (level === "AA") return r.aa.normalText;
    return r.aaa.normalText;
  }).length;

  return {
    level,
    total: results.length,
    passing,
    failing: results.length - passing,
    results,
  };
}

function findSemanticPairs(
  colors: Record<string, { value: string }>
): { name: string; fg: string; bg: string }[] {
  const pairs: { name: string; fg: string; bg: string }[] = [];
  const entries = Object.entries(colors);

  // Look for "on" prefix pairs: primary/onPrimary, surface/onSurface
  for (const [bgName, bgToken] of entries) {
    const onName = `on-${bgName}`;
    const onNameCamel = `on${bgName.charAt(0).toUpperCase()}${bgName.slice(1)}`;

    for (const [fgName, fgToken] of entries) {
      if (fgName === onName || fgName === onNameCamel) {
        pairs.push({
          name: `${fgName} on ${bgName}`,
          fg: fgToken.value,
          bg: bgToken.value,
        });
      }
    }
  }

  // Common pairs: text on surface, text on background
  const textColors = entries.filter(([n]) =>
    n.match(/^(text|foreground|fg|on-surface|on-background)$/i)
  );
  const bgColors = entries.filter(([n]) =>
    n.match(/^(surface|background|bg|canvas)$/i)
  );

  for (const [fgName, fgToken] of textColors) {
    for (const [bgName, bgToken] of bgColors) {
      const pairName = `${fgName} on ${bgName}`;
      if (!pairs.some((p) => p.name === pairName)) {
        pairs.push({ name: pairName, fg: fgToken.value, bg: bgToken.value });
      }
    }
  }

  return pairs;
}

/**
 * Calculate WCAG contrast ratio between two hex colors.
 * Returns a value between 1 and 21.
 */
function contrastRatio(hex1: string, hex2: string): number {
  const l1 = relativeLuminance(hex1);
  const l2 = relativeLuminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

function relativeLuminance(hex: string): number {
  let h = hex.replace("#", "");
  if (h.length === 3) {
    h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
  }
  const r = linearize(parseInt(h.slice(0, 2), 16) / 255);
  const g = linearize(parseInt(h.slice(2, 4), 16) / 255);
  const b = linearize(parseInt(h.slice(4, 6), 16) / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function linearize(c: number): number {
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}
