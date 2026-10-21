import { type EntryType } from "@typesafe-ai/sdk";
import { evaluateJev } from "./jev.js";

/** Pseudo-tool meaning "no tool: answer the user now". */
export const RESPOND = "respond_to_user";

/** A Jev `choice` question takes at most 255 labels, `respond_to_user` included. */
export const MAX_OPTIONS = 255;

export interface ToolSpec {
  readonly name: string;
  readonly description?: string;
}

export interface Action {
  readonly step: number;
  readonly tool: string;
  readonly input: unknown;
  readonly result: string;
}

export interface RouterState {
  readonly user_request: string;
  readonly actions_taken: readonly Action[];
  readonly assistant_said: readonly string[];
}

export interface RouterDecision {
  readonly tool: string;
  readonly confidence: number;
  /** Probability (0-1) that every requested action is already done. */
  readonly done: number;
  /** True when the gate overrode a premature respond_to_user. */
  readonly gated: boolean;
  readonly top: readonly { name: string; p: number }[];
  readonly latencyMs: number;
  readonly state: RouterState;
  /** True when the tool list was cut to fit MAX_OPTIONS. */
  readonly truncated: boolean;
}

/** Normalized conversation turn. Every adapter lowers its own wire format to this. */
export type Turn =
  | { readonly role: "user"; readonly text: string }
  | {
      readonly role: "assistant";
      readonly text?: string;
      readonly calls?: readonly { id: string; tool: string; input: unknown }[];
    }
  | { readonly role: "tool"; readonly id: string; readonly tool?: string; readonly output: unknown };

const INSTRUCTIONS =
  "You are routing a coding agent. Given the user's request and the actions already taken (with their results), " +
  "which tool should the assistant call NEXT to make progress? Choose exactly one. " +
  "Follow the order implied by the request: read and search before editing, and honour conditions ('if…'). " +
  "Never repeat an action that already succeeded. If everything requested is done, choose respond_to_user.";

const DONE_INSTRUCTIONS =
  "Every single action the user asked for (each read, search, edit, command, commit…) already appears as a successful entry in actions_taken. " +
  "False if at least one requested action has not been carried out yet, or a needed lookup returned nothing useful.";

const RESPOND_CRITERION = {
  what:
    "No tool call is needed now: every part of the request has been carried out (results are already in actions_taken) " +
    "or nothing in the catalog applies. The assistant should write its final answer.",
  not_for: "Cases where a step of the request (a read, a search, an edit, a command) has not happened yet.",
};

export function doneThreshold(): number {
  return Number(process.env.DONE_THRESHOLD ?? 0.5);
}

export function minConfidence(): number {
  return Number(process.env.MIN_CONFIDENCE ?? 0.5);
}

function textOf(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((p) =>
        p && typeof p === "object" && "type" in p && (p as { type: string }).type === "text"
          ? String((p as { text?: unknown }).text ?? "")
          : "",
      )
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

export function clip(value: unknown, max = 600): string {
  const s = typeof value === "string" ? value : JSON.stringify(value);
  if (s === undefined) return "";
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

/** Turn a normalized message history into the compact JSON state Jev sees. */
export function buildState(turns: readonly Turn[]): RouterState {
  const userTexts: string[] = [];
  const assistantSaid: string[] = [];
  const actions: Action[] = [];
  const pending = new Map<string, { step: number; tool: string; input: unknown }>();
  let step = 0;

  for (const m of turns) {
    if (m.role === "user") {
      const t = textOf(m.text);
      if (t) userTexts.push(t);
    } else if (m.role === "assistant") {
      const t = textOf(m.text);
      if (t) assistantSaid.push(clip(t, 300));
      for (const call of m.calls ?? []) {
        step += 1;
        pending.set(call.id, { step, tool: call.tool, input: call.input });
      }
    } else {
      const call = pending.get(m.id) ?? { step: ++step, tool: m.tool ?? "unknown", input: undefined };
      actions.push({ ...call, result: clip(m.output) });
    }
  }

  return { user_request: userTexts.join("\n---\n"), actions_taken: actions, assistant_said: assistantSaid };
}

/** Cut the option list to MAX_OPTIONS (respond_to_user included), keeping order of appearance. */
export function limitOptions(options: readonly ToolSpec[]): { options: readonly ToolSpec[]; truncated: boolean } {
  if (options.length + 1 <= MAX_OPTIONS) return { options, truncated: false };
  console.warn(
    `[jev] ${options.length} tools exceeds the ${MAX_OPTIONS}-option limit; keeping the first ${MAX_OPTIONS - 1}.`,
  );
  return { options: options.slice(0, MAX_OPTIONS - 1), truncated: true };
}

/** Jev may answer respond_to_user while work remains; require agreement from the done-noul. */
export function gate(
  tool: string,
  done: number,
  ranked: readonly (readonly [string, number])[],
): { tool: string; gated: boolean } {
  if (tool === RESPOND && done < doneThreshold()) {
    const next = ranked.find(([name]) => name !== RESPOND);
    if (next) return { tool: next[0], gated: true };
  }
  return { tool, gated: false };
}

/**
 * Offline stand-in for Jev (`JEV_STUB=1`): the first tool that has not run yet.
 * Only for smoke-testing the plumbing without an API key.
 */
export function stubDecision(state: RouterState, options: readonly ToolSpec[], truncated: boolean): RouterDecision {
  const used = new Set(state.actions_taken.map((a) => a.tool));
  const next = options.find((o) => !used.has(o.name));
  const tool = next?.name ?? RESPOND;
  return {
    tool,
    confidence: 0.99,
    done: tool === RESPOND ? 1 : 0,
    gated: false,
    top: [{ name: tool, p: 0.99 }],
    latencyMs: 0,
    state,
    truncated,
  };
}

/** Ask Jev which tool to call next. */
export async function chooseNextTool(state: RouterState, allOptions: readonly ToolSpec[]): Promise<RouterDecision> {
  const { options, truncated } = limitOptions(allOptions);
  if (process.env.JEV_STUB === "1") return stubDecision(state, options, truncated);

  const criteria: Record<string, string> = {
    [RESPOND]: `${RESPOND_CRITERION.what} Not for: ${RESPOND_CRITERION.not_for}`,
    ...Object.fromEntries(options.map((o) => [o.name, o.description ?? o.name])),
  };

  const started = performance.now();
  const answer = await evaluateJev({
    state: JSON.parse(JSON.stringify(state)) as EntryType,
    criteria, instructions: INSTRUCTIONS, doneInstructions: DONE_INSTRUCTIONS,
  });
  const latencyMs = Math.round(performance.now() - started);

  const done = answer.done;
  const ranked = Object.entries(answer.probabilities as Record<string, number>).sort((a, b) => b[1] - a[1]);
  const top = ranked.slice(0, 5).map(([name, p]) => ({ name, p: Math.round(p * 1000) / 1000 }));
  const gated = gate(answer.choice, done, ranked);

  return { tool: gated.tool, confidence: answer.confidence, done, gated: gated.gated, top, latencyMs, state, truncated };
}
