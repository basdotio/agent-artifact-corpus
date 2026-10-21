import { getVercelClient } from "../vercel/client.js";
import { getVercelToken } from "../utils/config.js";
import { diagnoseBuildFailure } from "./diagnose.js";
import { gitStatus } from "./git.js";

export interface SmartDeployResult {
  success: boolean;
  deploymentId?: string;
  deploymentUrl?: string;
  status?: string;
  versionControlSummary?: {
    uncommittedChangesCount: number;
    changedFiles: string[];
    suggestedCommitMessage?: string;
    aiPromptSuggestion?: string;
  };
  // Populated only on failure
  failed?: boolean;
  failureLogs?: string[];
  diagnosis?: {
    errorType: string;
    file?: string;
    line?: number;
    issue: string;
    suggestion: string;
    relevantLogs?: string[];
  };
  aiInstruction?: string;
  error?: string;
}

/**
 * Smart Deploy: Deploys to Vercel, polls until terminal state,
 * inspects uncommitted git changes, and on failure automatically fetches logs + diagnoses the error
 * so the AI model can understand and fix it.
 *
 * Secret values are NEVER included in the response.
 */
export async function smartDeploy(
  projectPath: string,
  projectName: string,
  maxPollSeconds: number = 180
): Promise<SmartDeployResult> {
  try {
    const token = await getVercelToken();
    if (!token) {
      return {
        success: false,
        error: "Vercel not authenticated. Run 'npx deploy-mcp setup' first."
      };
    }

    const client = await getVercelClient();
    if (!client) {
      return { success: false, error: "Failed to initialize Vercel client." };
    }

    // 0. Inspect Git Status & Uncommitted Changes
    let versionControlSummary: SmartDeployResult["versionControlSummary"] = undefined;
    try {
      const gitRes = await gitStatus(projectPath);
      if (gitRes.hasRepository && gitRes.uncommittedChanges && gitRes.uncommittedChanges > 0) {
        versionControlSummary = {
          uncommittedChangesCount: gitRes.uncommittedChanges,
          changedFiles: gitRes.files || [],
          suggestedCommitMessage: gitRes.suggestedCommitMessage,
          aiPromptSuggestion: `Ask user: "I noticed you modified ${gitRes.files?.length || 0} file(s) (${(gitRes.files || []).slice(0, 3).join(", ")}). Should I commit these updates with message '${gitRes.suggestedCommitMessage}'?"`
        };
      }
    } catch {
      // Ignore git errors if directory isn't a git repo
    }

    // 1. Trigger the deployment
    let deploymentId: string;
    let deploymentUrl: string;
    try {
      const result = await client.deployProject(projectPath, projectName);
      deploymentId = result.deploymentId;
      deploymentUrl = result.url;
    } catch (err) {
      return {
        success: false,
        failed: true,
        versionControlSummary,
        error: err instanceof Error ? err.message : "Deployment trigger failed."
      };
    }

    // 2. Poll for terminal state (READY or ERROR)
    const pollInterval = 5000; // 5s
    const maxPolls = Math.ceil((maxPollSeconds * 1000) / pollInterval);
    let status = "BUILDING";

    for (let i = 0; i < maxPolls; i++) {
      await new Promise(r => setTimeout(r, pollInterval));
      try {
        const statusResult = await client.getDeploymentStatus(projectName);
        status = statusResult.status;
        if (statusResult.url) deploymentUrl = statusResult.url;
        if (status === "READY") break;
        if (status === "ERROR" || status === "CANCELLED") break;
      } catch {
        // Swallow poll errors, keep trying
      }
    }

    // 3. SUCCESS path
    if (status === "READY") {
      return {
        success: true,
        deploymentId,
        deploymentUrl,
        status: "READY",
        versionControlSummary
      };
    }

    // 4. FAILURE path — auto-fetch logs and diagnose
    let failureLogs: string[] = [];
    try {
      const events = await client.getDeploymentLogs(deploymentId);
      failureLogs = events
        .map((e: any) => e.text || JSON.stringify(e))
        .filter(Boolean);
    } catch {
      failureLogs = ["(Could not retrieve deployment logs)"];
    }

    const diagnosis = await diagnoseBuildFailure(failureLogs);

    // Build a rich AI instruction prompt
    const aiInstruction = buildAiInstruction(diagnosis, failureLogs, projectName);

    return {
      success: false,
      failed: true,
      deploymentId,
      status,
      failureLogs: failureLogs.slice(-50), // Last 50 lines for context
      diagnosis,
      versionControlSummary,
      aiInstruction
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Smart deploy failed unexpectedly."
    };
  }
}

/**
 * Builds a clear, actionable message for the AI model to act on.
 */
function buildAiInstruction(
  diagnosis: Awaited<ReturnType<typeof diagnoseBuildFailure>>,
  logs: string[],
  projectName: string
): string {
  const lines = [
    `❌ Deployment of "${projectName}" FAILED.`,
    ``,
    `🔍 Error Type: ${diagnosis.errorType}`,
    `📌 Issue: ${diagnosis.issue}`,
    `💡 Suggested Fix: ${diagnosis.suggestion}`,
    ``
  ];

  if (diagnosis.file) {
    lines.push(`📄 File: ${diagnosis.file}${diagnosis.line ? ` (line ${diagnosis.line})` : ""}`);
  }

  if (diagnosis.relevantLogs && diagnosis.relevantLogs.length > 0) {
    lines.push(``, `📋 Relevant Log Lines:`);
    diagnosis.relevantLogs.slice(0, 10).forEach(l => lines.push(`  ${l}`));
  }

  lines.push(
    ``,
    `🤖 AI Action Required:`,
    `  1. Inspect the file(s) mentioned above`,
    `  2. Apply the suggested fix`,
    `  3. Call smart_deploy again to redeploy`,
    ``,
    `⚠️  Do NOT expose any secret values when fixing this issue.`
  );

  return lines.join("\n");
}
