/**
 * Deploy MCP Terminal Aesthetics & Brand Color System
 * Signature Brand Palette:
 * - Burnt Orange: #D5380C (rgb: 213, 56, 12)
 * - Warm Ivory: #FAF6EE (rgb: 250, 246, 238)
 * - Brand Gold: #F1B333 (rgb: 241, 179, 51)
 * - Soft Black: #101010 (rgb: 16, 16, 16)
 */

// Basic ANSI escape codes
const RESET = "\x1b[0m";
const BOLD = "\x1b[1m";
const DIM = "\x1b[2m";
const ITALIC = "\x1b[3m";
const UNDERLINE = "\x1b[4m";

// Brand RGB Color Palette (Strict Signature Colors)
export const BRAND_ORANGE_RGB = { r: 213, g: 56, b: 12 };
export const BRAND_IVORY_RGB = { r: 250, g: 246, b: 238 };
export const BRAND_GOLD_RGB = { r: 241, g: 179, b: 51 };
export const BRAND_DARK_RGB = { r: 20, g: 20, b: 20 };

// RGB Truecolor helpers
export function rgb(r: number, g: number, b: number, text: string): string {
  return `\x1b[38;2;${r};${g};${b}m${text}${RESET}`;
}

export function bgRgb(r: number, g: number, b: number, text: string): string {
  return `\x1b[48;2;${r};${g};${b}m${text}${RESET}`;
}

export const c = {
  reset: (s: string) => `${RESET}${s}`,
  bold: (s: string) => `${BOLD}${s}${RESET}`,
  dim: (s: string) => `${DIM}${s}${RESET}`,
  italic: (s: string) => `${ITALIC}${s}${RESET}`,
  underline: (s: string) => `${UNDERLINE}${s}${RESET}`,

  // Solid Signature Brand Colors
  brand: (s: string) => `\x1b[38;2;213;56;12m\x1b[1m${s}${RESET}`,
  brandOrange: (s: string) => `\x1b[38;2;213;56;12m\x1b[1m${s}${RESET}`,
  brandGold: (s: string) => `\x1b[38;2;241;179;51m\x1b[1m${s}${RESET}`,
  brandIvory: (s: string) => `\x1b[38;2;250;246;238m\x1b[1m${s}${RESET}`,

  // Brand-safe Aliases (No blue/cyan)
  cyan: (s: string) => `\x1b[38;2;250;246;238m${s}${RESET}`,
  brightCyan: (s: string) => `\x1b[38;2;213;56;12m\x1b[1m${s}${RESET}`,
  blue: (s: string) => `\x1b[38;2;250;246;238m\x1b[1m${s}${RESET}`,
  magenta: (s: string) => `\x1b[38;2;241;179;51m${s}${RESET}`,
  green: (s: string) => `\x1b[38;2;16;185;129m${s}${RESET}`,
  yellow: (s: string) => `\x1b[38;2;241;179;51m${s}${RESET}`,
  red: (s: string) => `\x1b[38;2;239;68;68m${s}${RESET}`,
  white: (s: string) => `\x1b[38;2;250;246;238m\x1b[1m${s}${RESET}`,
  gray: (s: string) => `\x1b[38;2;150;140;130m${s}${RESET}`,

  // Compound Badges & Highlights
  badge: (label: string, bgR = 213, bgG = 56, bgB = 12) => 
    `\x1b[48;2;${bgR};${bgG};${bgB}m\x1b[38;2;250;246;238m\x1b[1m ${label} ${RESET}`,
  
  code: (s: string) => `\x1b[38;2;241;179;51m${s}${RESET}`,
  highlight: (s: string) => `\x1b[38;2;213;56;12m\x1b[1m${s}${RESET}`,
  success: (s: string) => `\x1b[38;2;16;185;129m\x1b[1m${s}${RESET}`,
  warn: (s: string) => `\x1b[38;2;241;179;51m\x1b[1m${s}${RESET}`,
  error: (s: string) => `\x1b[38;2;213;56;12m\x1b[1m${s}${RESET}`,
};

/**
 * Signature Brand Burnt Orange (#D5380C) styling for ASCII banners.
 */
export function cyanMagentaGradient(text: string): string {
  return text
    .split("\n")
    .map(line => `\x1b[38;2;213;56;12m\x1b[1m${line}${RESET}`)
    .join("\n");
}

/**
 * Signature Brand styling for header lines.
 */
export function lineGradient(text: string): string {
  return `\x1b[38;2;213;56;12m\x1b[1m${text}${RESET}`;
}
