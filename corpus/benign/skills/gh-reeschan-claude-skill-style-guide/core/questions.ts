import type { Question } from "./types.ts";
import { get } from "./guards.ts";

export const JEV_MODEL = "jev-1.13.0";

export const HUES = {
  red: 25,
  orange: 55,
  amber: 75,
  yellow: 100,
  lime: 125,
  green: 145,
  teal: 180,
  cyan: 210,
  blue: 255,
  indigo: 275,
  violet: 300,
  pink: 350,
} as const;

export const ESTIMATE_QUESTIONS: Record<string, Question> = {
  brand_hue: {
    type: "choice",
    instructions: "Which single hue best fits this product as its main brand color?",
    criteria: {
      red: "Energetic, urgent, bold. Food, sale, entertainment.",
      orange: "Friendly, lively, affordable. Consumer apps, community.",
      amber: "Warm, crafted, earthy. Cafes, handmade goods, autumn.",
      yellow: "Bright, cheerful, attention-grabbing. Kids, caution, optimism.",
      lime: "Fresh, playful, unconventional. Youth, sports, eco.",
      green: "Natural, healthy, growth, safe. Wellness, finance gains, sustainability.",
      teal: "Clean, calm, clinical. Healthcare, hygiene, modern utilities.",
      cyan: "Light, airy, technical. Water, cloud services, cool freshness.",
      blue: "Trustworthy, stable, professional. Business software, banking.",
      indigo: "Deep, quiet, traditional, intellectual. Indigo dye, night, formal tools.",
      violet: "Creative, imaginative, luxurious. Games, music, beauty.",
      pink: "Soft, romantic, playful. Cosmetics, sweets, lifestyle.",
    },
  },
  neutral_tint: {
    type: "choice",
    instructions: "What tint should the grays used for backgrounds and text have?",
    criteria: {
      pure: "Completely neutral gray with no color. Technical, minimal, monochrome.",
      warm: "Slightly warm gray, like paper or sand. Cozy, human, traditional.",
      cool: "Slightly cool bluish gray. Crisp, digital, corporate.",
      brand: "Gray tinted slightly toward the brand color. Cohesive and distinctive.",
    },
  },
  accent_scheme: {
    type: "choice",
    instructions: "If a second accent color is used, how should it relate to the brand color?",
    criteria: {
      analogous: "A neighboring hue. Harmonious and quiet.",
      complementary: "The opposite hue. Strong contrast, eye-catching calls to action.",
      triadic: "A hue one third around the color wheel. Colorful and playful.",
    },
  },
  base_mode: {
    type: "choice",
    instructions: "Should the default appearance be light or dark?",
    criteria: {
      light: "Light background with dark text. Documents, business, daytime use.",
      dark: "Dark background with light text. Games, media, developer tools, night use.",
    },
  },
  font_mood: {
    type: "choice",
    instructions: "Which typeface character best fits this product?",
    criteria: {
      geometric: "Clean shapes built from circles and straight lines. Modern, neutral.",
      humanist: "Soft, readable, slightly handwritten proportions. Warm and approachable.",
      rounded: "Rounded stroke ends. Friendly, casual, child-safe.",
      serif: "Serif letterforms. Editorial, classic, authoritative.",
      mincho: "Japanese Mincho or brush-influenced forms. Traditional Japanese, elegant, literary.",
      tech: "Angular, mechanical, or monospace-like. Futuristic, gaming, engineering.",
    },
  },
  shadow: {
    type: "choice",
    instructions: "How should raised elements such as cards be separated from the background?",
    criteria: {
      none: "No shadow, only borders. Flat and minimal.",
      soft: "Soft blurred shadow. Gentle depth, modern.",
      hard: "Solid offset shadow with no blur. Bold, retro, playful.",
    },
  },
  use_accent: {
    type: "noul",
    instructions: "This product's design should use a second accent color in addition to its main brand color.",
    criteria: {
      "1": "A second color is useful, for example to highlight calls to action or to feel lively.",
      "0": "A single brand color is enough. A second color would feel busy or off-brand.",
    },
  },
  chroma: {
    type: "score",
    instructions: "How vivid should the colors be?",
    criteria: ["Nearly gray, very muted", "Muted, dusty", "Moderate", "Vivid", "Neon, maximum saturation"],
  },
  contrast: {
    type: "score",
    instructions: "How strong should the contrast between text and background be?",
    criteria: ["Very soft, low contrast", "Soft", "Standard", "Crisp", "Maximum, stark black and white"],
  },
  radius: {
    type: "score",
    instructions: "How rounded should corners be?",
    criteria: ["Square, sharp corners", "Slightly rounded", "Moderately rounded", "Clearly rounded", "Pill-shaped, fully rounded"],
  },
  density: {
    type: "score",
    instructions: "How much whitespace should the layout have?",
    criteria: ["Very dense, data-heavy", "Compact", "Standard", "Spacious", "Very airy, lots of whitespace"],
  },
  formality: {
    type: "score",
    instructions: "How formal should the overall impression be?",
    criteria: ["Very playful and casual", "Casual", "Balanced", "Formal", "Very formal, institutional"],
  },
};

export const ESTIMATE_KEYS: string[] = [
  "brand_hue",
  "neutral_tint",
  "accent_scheme",
  "base_mode",
  "font_mood",
  "shadow",
  "use_accent",
  "chroma",
  "contrast",
  "radius",
  "density",
  "formality",
];

export function estimateQuestions(skip: string[]): Record<string, Question> {
  const out: Record<string, Question> = {};
  for (const key of ESTIMATE_KEYS) {
    if (!skip.includes(key)) out[key] = get(ESTIMATE_QUESTIONS, key);
  }
  return out;
}

export const THRESHOLDS = {
  choice: { brand_hue: 0.5, neutral_tint: 0.5, accent_scheme: 0.5, base_mode: 0.6, font_mood: 0.5, shadow: 0.5, font_pair: 0.4 },
  noulUncertain: { use_accent: [0.35, 0.65] },
  scoreLow: { chroma: 0.5, contrast: 0.5, radius: 0.5, density: 0.5, formality: 0.5 },
};
