import { getVercelClient } from "../vercel/client.js";
import { getVercelToken } from "../utils/config.js";

export interface DeploymentResult {
  success: boolean;
  deploymentId?: string;
  deploymentUrl?: string;
  status?: string;
  error?: string;
}

export async function deployToVercel(
  projectPath: string,
  projectName: string
): Promise<DeploymentResult> {
  try {
    // Check if token exists
    const token = await getVercelToken();
    if (!token) {
      return {
        success: false,
        error: "Vercel not authenticated. Run 'npx deploy-mcp setup' first."
      };
    }

    // Get Vercel client
    const client = await getVercelClient();
    if (!client) {
      return {
        success: false,
        error: "Failed to initialize Vercel client"
      };
    }

    // Deploy
    const result = await client.deployProject(projectPath, projectName);

    return {
      success: true,
      deploymentId: result.deploymentId,
      deploymentUrl: result.url
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Deployment failed"
    };
  }
}

export async function getDeploymentStatus(
  projectName: string
): Promise<DeploymentResult> {
  try {
    const client = await getVercelClient();
    if (!client) {
      return {
        success: false,
        error: "Vercel not authenticated"
      };
    }

    const result = await client.getDeploymentStatus(projectName);

    return {
      success: true,
      status: result.status,
      deploymentUrl: result.url
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Status check failed"
    };
  }
}
