/**
 * Universal Design Token schema types.
 * This is the canonical intermediate format that all extractors produce
 * and all generators consume.
 */

export interface ColorToken {
  value: string; // hex color, e.g. "#6750A4"
  description?: string;
  category?:
    | "primary"
    | "secondary"
    | "tertiary"
    | "neutral"
    | "error"
    | "surface"
    | "background"
    | "custom";
}

export interface TypographyToken {
  fontFamily?: string;
  fontSize: number; // px
  lineHeight?: number; // px
  fontWeight?: number; // 100-900
  letterSpacing?: number; // px
}

export interface ElevationToken {
  shadowColor: string; // hex
  shadowOffset: { x: number; y: number };
  shadowRadius: number;
  shadowOpacity: number; // 0-1
}

export interface MotionToken {
  duration: number; // ms
  easing: string; // e.g. "ease-in-out", "cubic-bezier(0.4, 0, 0.2, 1)"
}

export interface DesignTokens {
  colors?: Record<string, ColorToken>;
  typography?: Record<string, TypographyToken>;
  spacing?: Record<string, number>; // px values
  radii?: Record<string, number>; // px values
  elevation?: Record<string, ElevationToken>;
  motion?: Record<string, MotionToken>;
}
