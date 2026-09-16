/**
 * Basic Agent SDK Runner — minimal example
 *
 * Demonstrates: query(), AbortSignal, result handling, type guards
 */
import { readFileSync } from "node:fs";
import { query, isResultMessage, type SDKMessage } from "./types";

interface RunnerOptions {
  prompt: string;
  systemPrompt: string;
  workingDirectory: string;
  outputFilePath: string;
  abortSignal?: AbortSignal;
}

interface RunnerResult {
  code: string;
  costUsd?: number;
}

const SDK_MODEL = "claude-sonnet-4-5-20250929" as const;
const SDK_MAX_TURNS = 50;
const SDK_MAX_BUDGET_USD = 2;

async function runAgent(options: RunnerOptions): Promise<RunnerResult> {
  const abortController = new AbortController();

  if (options.abortSignal) {
    options.abortSignal.addEventListener("abort", () => abortController.abort());
  }

  const messageStream: AsyncIterable<SDKMessage> = query({
    prompt: options.prompt,
    options: {
      model: SDK_MODEL,
      systemPrompt: options.systemPrompt,
      allowedTools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
      permissionMode: "bypassPermissions",
      maxTurns: SDK_MAX_TURNS,
      maxBudgetUsd: SDK_MAX_BUDGET_USD,
      cwd: options.workingDirectory,
      abortController,
    },
  });

  for await (const message of messageStream) {
    if (isResultMessage(message)) {
      const code = readFileSync(options.outputFilePath, "utf8");
      return { code, costUsd: message.total_cost_usd };
    }
  }

  return { code: "" };
}

export { runAgent };
