import { getVercelClient } from "../vercel/client.js";

export interface LogResult {
  success: boolean;
  logs?: string[];
  error?: string;
  errorMessage?: string;
}

export async function getDeploymentLogs(
  projectName: string
): Promise<LogResult> {
  try {
    const client = await getVercelClient();
    if (!client) {
      return { success: false, error: "Vercel not authenticated" };
    }

    // Get the latest deployment ID for the project first
    const status = await client.getDeploymentStatus(projectName);
    if (!status || !status.id) {
      return { success: false, error: "No deployment found for this project." };
    }

    const events = await client.getDeploymentLogs(status.id);
    
    // Parse the events to extract text messages
    const logs = events.map(e => e.text || JSON.stringify(e));

    // Simple heuristic to extract the first error message if one exists
    const errorMessage = logs.find(log => log.toLowerCase().includes("error:"));

    return {
      success: true,
      logs: logs.slice(-100), // Return last 100 lines for brevity
      error: errorMessage ? "BUILD_ERROR" : undefined,
      errorMessage: errorMessage
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Log check failed"
    };
  }
}
