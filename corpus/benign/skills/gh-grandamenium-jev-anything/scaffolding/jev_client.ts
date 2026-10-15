/**
 * Minimal Jev client for OpenRouter (TypeScript, uses global fetch, no deps).
 *
 * Jev is TypeSafe's System One decision model: send a `state` plus typed
 * `questions` (noul / choice / score), get typed answers with probabilities and
 * confidence. See ../references/02-openrouter-decisions-api.md.
 *
 * Auth: set OPENROUTER_API_KEY (get a key at https://openrouter.ai/keys).
 *
 * NOTE: the raw endpoint path varies across OpenRouter docs; it is a single const
 * below. If a call 404s, switch to ALT_ENDPOINT or use the official
 * @typesafe-ai/sdk (which handles the path). Verify at
 * https://openrouter.ai/typesafe/jev-1.13
 */

const MODEL = "typesafe/jev-1.13";
const ENDPOINT = "https://openrouter.ai/api/alpha/decisions";
// const ALT_ENDPOINT = "https://openrouter.ai/api/v1/systemone";

export type Question =
  | { type: "noul"; instructions: string; criteria?: Record<string, string> }
  | { type: "choice"; instructions: string; criteria: Record<string, string> }
  | { type: "score"; instructions: string; criteria: string[] };

export const noul = (instructions: string): Question => ({ type: "noul", instructions });

export const choice = (instructions: string, options: Record<string, string>): Question => {
  const n = Object.keys(options).length;
  if (n < 1 || n > 255) throw new Error("choice needs 1..255 options");
  return { type: "choice", instructions, criteria: options };
};

export const score = (instructions: string, levels: string[]): Question => {
  if (levels.length < 2 || levels.length > 10) {
    throw new Error("score needs 2..10 rubric levels, lowest first");
  }
  return { type: "score", instructions, criteria: levels };
};

export interface JevResponse {
  model: string;
  answers: Record<string, any>;
  usage: { input_tokens: number; output_tokens: number; cost?: number };
}

export async function decide(
  state: string,
  questions: Record<string, Question>,
  opts: { apiKey?: string; endpoint?: string } = {}
): Promise<JevResponse> {
  const apiKey = opts.apiKey ?? process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error("Set OPENROUTER_API_KEY (see .env.example)");

  const res = await fetch(opts.endpoint ?? ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ model: MODEL, state, questions }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(
      `Jev call failed (HTTP ${res.status}). If 404, try ALT_ENDPOINT or @typesafe-ai/sdk. Body: ${detail}`
    );
  }
  return (await res.json()) as JevResponse;
}

// Non-authoritative helper: keep thresholds and actions in YOUR code.
export function confident(answer: any, threshold = 0.8): boolean {
  if (answer.type === "noul") {
    const p = answer.noul as number;
    return Math.max(p, 1 - p) >= threshold;
  }
  return (answer.confidence ?? 0) >= threshold;
}
