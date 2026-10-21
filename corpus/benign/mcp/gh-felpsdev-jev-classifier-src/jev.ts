import { TypeSafeClient, choice, noul, type EntryType } from "@typesafe-ai/sdk";

const PROVIDERS = {
  typesafe: { key: "TYPESAFE_API_KEY", model: "jev-latest", endpoint: "https://api.typesafe.ai/v1/systemone" },
  openrouter: { key: "OPENROUTER_API_KEY", model: "~typesafe/jev-latest", endpoint: "https://openrouter.ai/api/alpha/decisions" },
  vercel: { key: "AI_GATEWAY_API_KEY", model: "typesafe-ai/jev", endpoint: "https://ai-gateway.vercel.sh/v4/ai/evaluation-model" },
} as const;

export function jevConfig(env: NodeJS.ProcessEnv = process.env) {
  const provider = env.JEV_PROVIDER || "typesafe";
  if (!Object.hasOwn(PROVIDERS, provider)) throw new Error("JEV_PROVIDER must be typesafe, openrouter, or vercel.");
  const defaults = PROVIDERS[provider as keyof typeof PROVIDERS];
  return { provider, apiKey: env.JEV_API_KEY || env[defaults.key], keyVariable: defaults.key,
    model: env.JEV_MODEL || defaults.model, endpoint: defaults.endpoint };
}

/** Public diagnostics deliberately exclude credentials. Configured does not mean authenticated. */
export function jevStatus() {
  try {
    const config = jevConfig();
    return { jevProvider: config.provider, jevModel: config.model, jevConfigured: Boolean(config.apiKey) };
  } catch {
    return { jevProvider: "invalid", jevConfigured: false };
  }
}

export interface EvaluationInput {
  state: EntryType;
  criteria: Record<string, string>;
  instructions: string;
  doneInstructions: string;
}

type Config = ReturnType<typeof jevConfig>;
export interface Evaluation {
  choice: string;
  probabilities: Record<string, number>;
  confidence: number;
  done: number;
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid Jev evaluation response.");
  return value as Record<string, unknown>;
}

function probability(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new Error("Invalid Jev probability.");
  }
  return value;
}

/** Missing distributions cannot safely support the done gate; fail open at the proxy. */
function normalize(value: unknown, input: EvaluationInput, provider: string): Evaluation {
  const answers = object(object(value).answers);
  const next = object(answers.next_tool);
  const done = object(answers.done);
  if (next.type !== "choice" || typeof next.choice !== "string" || !Object.hasOwn(input.criteria, next.choice)
      || done.type !== (provider === "vercel" ? "boolean" : "noul")) {
    throw new Error("Invalid Jev answer type or tool choice.");
  }
  const distribution = object(next.probabilities);
  const labels = Object.keys(input.criteria);
  if (Object.keys(distribution).length !== labels.length || labels.some(name => !Object.hasOwn(distribution, name))) {
    throw new Error("Jev returned an incomplete tool probability distribution.");
  }
  const probabilities = Object.fromEntries(labels.map(name => [name, probability(distribution[name])]));
  // Some gateways omit native confidence. Use the chosen option's probability in that case.
  const metadata = object(value).providerMetadata as { typesafe?: { confidence?: { next_tool?: number } } } | undefined;
  const confidence = probability(next.confidence ?? metadata?.typesafe?.confidence?.next_tool ?? probabilities[next.choice]);
  return { choice: next.choice, probabilities, confidence,
    done: probability(provider === "vercel" ? done.probability : done.noul) };
}

/** Classifier transport only: never receives the coding agent's headers or credentials. */
export async function evaluateJev(input: EvaluationInput, config: Config = jevConfig(), request: typeof fetch = fetch): Promise<Evaluation> {
  if (!config.apiKey) throw new Error(`Set ${config.keyVariable} or JEV_API_KEY for JEV_PROVIDER=${config.provider} (or JEV_STUB=1 for an offline test).`);
  if (config.provider === "typesafe") {
    const client = new TypeSafeClient({ apiKey: config.apiKey });
    const result = await client.systemOne({ model: config.model, state: input.state,
      questions: { next_tool: choice(input.instructions, input.criteria), done: noul(input.doneInstructions) } });
    return normalize(result, input, config.provider);
  }
  const vercel = config.provider === "vercel";
  const headers: Record<string, string> = { "content-type": "application/json", authorization: `Bearer ${config.apiKey}` };
  if (vercel) Object.assign(headers, {
    "ai-gateway-protocol-version": "0.0.1",
    "ai-model-id": config.model, "ai-evaluation-model-specification-version": "4", "ai-gateway-auth-method": "api-key",
  });
  const response = await request(config.endpoint, {
    method: "POST", headers, redirect: "error", signal: AbortSignal.timeout(30_000),
    body: JSON.stringify({ ...(!vercel ? { model: config.model } : {}), state: input.state,
      questions: {
        next_tool: { type: "choice", instructions: input.instructions, criteria: input.criteria },
        done: { type: vercel ? "boolean" : "noul", instructions: input.doneInstructions },
      } }),
  });
  if (!response.ok) {
    await response.body?.cancel();
    // Provider error bodies can echo request content; keep credentials and state out of logs.
    const hint = response.status === 401 || response.status === 403 ? "Check the selected provider's key in setup."
      : response.status === 402 ? "Check your provider balance or billing limits."
      : response.status === 404 ? `Check Jev model availability for ${config.model}; restore the provider default in setup.`
      : response.status === 400 || response.status === 422 ? "The gateway rejected the evaluation request. Run doctor --check to test a minimal request."
      : response.status === 429 || response.status >= 500 ? "The provider is busy or unavailable. Try again shortly."
      : "Run doctor --check to verify the classifier connection.";
    throw new Error(`Jev ${config.provider} returned HTTP ${response.status}. ${hint}`);
  }
  return normalize(await response.json(), input, config.provider);
}
