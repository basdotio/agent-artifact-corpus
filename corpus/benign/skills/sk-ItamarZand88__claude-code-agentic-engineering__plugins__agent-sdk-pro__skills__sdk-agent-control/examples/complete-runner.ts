/**
 * Complete Agent SDK Runner — production-ready example
 *
 * Demonstrates:
 * - Injectable class with DI
 * - Conditional hook composition
 * - AbortSignal forwarding
 * - Full message iteration
 * - Metadata prepend
 * - Cost/duration tracking
 */

import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { inject, injectable } from "inversify";

// Config service (your DI container)
import type { ConfigService } from "@/context/config/config.service";

// Single point of contact for SDK
import {
  query,
  isResultMessage,
  type SDKMessage,
  type SDKResultMessage,
} from "./types";

// Constants
import {
  SDK_MODEL,
  SDK_MAX_BUDGET_USD,
  SDK_MAX_TURNS,
  SDK_PERMISSION_MODE,
  SDK_ALLOWED_TOOLS,
  isSdkVerboseLogging,
} from "./agent-sdk.const";

// Hooks
import {
  envProtectionHook,
  createFileRestrictionHook,
  createLintFixHook,
  createTypecheckHook,
  testPruneHook,
} from "./hooks";

interface RunParams {
  userPrompt: string;
  systemPrompt: string;
  workingDirectory: string;
  outputFilePath: string;
  abortSignal?: AbortSignal;
}

interface RunResult {
  code: string;
  costUsd?: number;
  durationMs?: number;
  numTurns?: number;
}

@injectable()
export class AgentSdkRunner {
  constructor(
    @inject(ConfigService) private readonly config: ConfigService,
  ) {}

  async run(params: RunParams): Promise<RunResult> {
    const abortController = new AbortController();

    if (params.abortSignal) {
      params.abortSignal.addEventListener("abort", () => abortController.abort());
    }

    // Resolve model + budget from config (with safe defaults)
    const model = this.config.getAgentModel() ?? SDK_MODEL;
    const budget = this.config.getAgentBudget() ?? SDK_MAX_BUDGET_USD;

    // Build hooks dynamically — some may be unavailable (return null)
    const fileRestrictionHook = createFileRestrictionHook(params.outputFilePath);
    const lintFixHook = createLintFixHook(params.workingDirectory, params.outputFilePath);
    const typecheckHook = createTypecheckHook(params.workingDirectory, params.outputFilePath);

    const postEditHooks: NonNullable<typeof lintFixHook>[] = [
      ...(lintFixHook ? [lintFixHook] : []),
      ...(typecheckHook ? [typecheckHook] : []),
    ];

    // Augment prompt with file instruction (Edit-only pattern)
    const augmentedPrompt = [
      params.userPrompt,
      "",
      "---",
      `IMPORTANT: A file has been pre-created at: ${params.outputFilePath}`,
      "Use the Edit tool to modify this file. Do NOT create new files with Write.",
    ].join("\n");

    const messageStream: AsyncIterable<SDKMessage> = query({
      prompt: augmentedPrompt,
      options: {
        model,
        systemPrompt: params.systemPrompt,
        allowedTools: [...SDK_ALLOWED_TOOLS],
        permissionMode: SDK_PERMISSION_MODE,
        maxTurns: SDK_MAX_TURNS,
        maxBudgetUsd: budget,
        cwd: params.workingDirectory,
        abortController,
        hooks: {
          PreToolUse: [
            { matcher: "Write|Edit", hooks: [fileRestrictionHook] },
            { matcher: "Read", hooks: [envProtectionHook] },
          ],
          PostToolUse: [
            { matcher: "Bash", hooks: [testPruneHook] },
            ...(postEditHooks.length > 0 ? [{ matcher: "Write|Edit", hooks: postEditHooks }] : []),
          ],
        },
      },
    });

    for await (const message of messageStream) {
      if (isSdkVerboseLogging) {
        console.log("[SDK]", message.type);
      }

      if (isResultMessage(message)) {
        return this.buildResult(message, params.outputFilePath);
      }
    }

    // Fallback: stream ended without result message
    const code = existsSync(params.outputFilePath)
      ? readFileSync(params.outputFilePath, "utf8")
      : "";
    return { code };
  }

  private buildResult(result: SDKResultMessage, outputFilePath: string): RunResult {
    const code = existsSync(outputFilePath)
      ? readFileSync(outputFilePath, "utf8")
      : "";

    if (code) {
      const metadata = this.buildMetadataComment(result);
      writeFileSync(outputFilePath, metadata + code, "utf8");
    }

    return {
      code: code ? this.buildMetadataComment(result) + code : code,
      costUsd: result.total_cost_usd,
      durationMs: result.duration_ms,
      numTurns: result.num_turns,
    };
  }

  private buildMetadataComment(result: SDKResultMessage): string {
    return [
      "/**",
      " * @generated Agent SDK",
      ` * @duration ${(result.duration_ms / 1000).toFixed(1)}s`,
      ` * @cost $${result.total_cost_usd.toFixed(4)}`,
      ` * @turns ${result.num_turns}`,
      " */",
      "",
    ].join("\n");
  }
}
