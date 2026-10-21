import { z } from "zod";

const hexColor = z
  .string()
  .regex(/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/, "Must be a valid hex color (#RGB, #RRGGBB, or #RRGGBBAA)");

const colorToken = z.object({
  value: hexColor,
  description: z.string().optional(),
  category: z
    .enum([
      "primary",
      "secondary",
      "tertiary",
      "neutral",
      "error",
      "surface",
      "background",
      "custom",
    ])
    .optional(),
});

const typographyToken = z.object({
  fontFamily: z.string().optional(),
  fontSize: z.number().positive("fontSize must be positive"),
  lineHeight: z.number().positive("lineHeight must be positive").optional(),
  fontWeight: z
    .number()
    .int()
    .min(1, "fontWeight minimum is 1")
    .max(1000, "fontWeight maximum is 1000")
    .optional(),
  letterSpacing: z.number().optional(),
});

const elevationToken = z.object({
  shadowColor: hexColor,
  shadowOffset: z.object({
    x: z.number(),
    y: z.number(),
  }),
  shadowRadius: z.number().min(0, "shadowRadius cannot be negative"),
  shadowOpacity: z
    .number()
    .min(0, "shadowOpacity minimum is 0")
    .max(1, "shadowOpacity maximum is 1"),
});

const motionToken = z.object({
  duration: z.number().positive("duration must be positive"),
  easing: z.string().min(1, "easing cannot be empty"),
});

export const designTokensSchema = z
  .object({
    colors: z.record(z.string(), colorToken).optional(),
    typography: z.record(z.string(), typographyToken).optional(),
    spacing: z
      .record(z.string(), z.number().min(0, "spacing cannot be negative"))
      .optional(),
    radii: z
      .record(z.string(), z.number().min(0, "radii cannot be negative"))
      .optional(),
    elevation: z.record(z.string(), elevationToken).optional(),
    motion: z.record(z.string(), motionToken).optional(),
  })
  .refine(
    (tokens) =>
      tokens.colors !== undefined ||
      tokens.typography !== undefined ||
      tokens.spacing !== undefined ||
      tokens.radii !== undefined ||
      tokens.elevation !== undefined ||
      tokens.motion !== undefined,
    "Token object must contain at least one token category"
  );

export type DesignTokensInput = z.input<typeof designTokensSchema>;
export type DesignTokensOutput = z.output<typeof designTokensSchema>;

// Re-export individual schemas for tools that validate subsets
export {
  hexColor,
  colorToken,
  typographyToken,
  elevationToken,
  motionToken,
};
