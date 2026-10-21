import { getVercelToken } from "../utils/config.js";

const VERCEL_API_BASE = "https://api.vercel.com";

export interface VercelDeployment {
  uid: string;
  name: string;
  url: string;
  state: "BUILDING" | "READY" | "ERROR" | "CANCELLED";
  createdAt: number;
}

export class VercelClient {
  private token: string;

  constructor(token: string) {
    this.token = token;
  }

  private async request(
    method: string,
    path: string,
    body?: any
  ): Promise<any> {
    const url = `${VERCEL_API_BASE}${path}`;
    
    const response = await fetch(url, {
      method,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json"
      },
      body: body ? JSON.stringify(body) : undefined
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Vercel API error: ${error.message || response.statusText}`);
    }

    return response.json();
  }

  async deployProject(
    projectPath: string,
    projectName: string
  ): Promise<{ deploymentId: string; url: string }> {
    try {
      // Create or get project
      const project = await this.ensureProject(projectName);

      // Deploy using Vercel CLI wrapper
      // For MVP, we'll use the CLI as this is simpler than Git integration
      const { execSync } = await import("child_process");
      
      const deployResult = execSync(
        `cd "${projectPath}" && vercel --prod --token=${this.token} --yes`,
        { encoding: "utf-8" }
      );

      // Parse deployment URL from output
      const urlMatch = deployResult.match(
        /https:\/\/[a-zA-Z0-9\-\.]+\.vercel\.app/
      );
      const deploymentUrl = urlMatch ? urlMatch[0] : "";

      return {
        deploymentId: project.id,
        url: deploymentUrl
      };
    } catch (error) {
      throw new Error(
        `Deployment failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  }

  async getDeploymentStatus(
    projectName: string
  ): Promise<{ status: string; url: string; id: string }> {
    try {
      const project = await this.getProject(projectName);
      
      if (!project) {
        return { status: "NOT_FOUND", url: "", id: "" };
      }

      // Get latest deployment
      const deployments = await this.request(
        "GET",
        `/v6/deployments?projectId=${project.id}`
      );

      if (!deployments.deployments || deployments.deployments.length === 0) {
        return { status: "NO_DEPLOYMENTS", url: "", id: "" };
      }

      const latest = deployments.deployments[0];
      return {
        status: latest.state,
        url: `https://${latest.url}`,
        id: latest.uid
      };
    } catch (error) {
      throw new Error(
        `Status check failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  }

  async getDeploymentLogs(
    deploymentId: string
  ): Promise<any[]> {
    try {
      // For Vercel API, getting logs often requires specific endpoints.
      // Usually it's /v2/deployments/:id/events
      const response = await this.request(
        "GET",
        `/v2/deployments/${deploymentId}/events`
      );
      
      return response || [];
    } catch (error) {
      throw new Error(
        `Log fetch failed: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  }

  async getEnvironmentVariables(projectId: string): Promise<any[]> {
    try {
      const response = await this.request(
        "GET",
        `/v9/projects/${projectId}/env`
      );
      return response.envs || [];
    } catch (error) {
      throw new Error(`Failed to fetch environment variables: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async createEnvironmentVariable(
    projectId: string,
    key: string,
    value: string,
    target: string[] = ["production", "preview", "development"]
  ): Promise<any> {
    try {
      const response = await this.request(
        "POST",
        `/v10/projects/${projectId}/env`,
        {
          key,
          value,
          target,
          type: "encrypted" // or "system" / "plain" but encrypted is standard for secrets
        }
      );
      return response;
    } catch (error) {
      throw new Error(`Failed to create environment variable: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async deleteProject(projectId: string): Promise<boolean> {
    try {
      await this.request("DELETE", `/v9/projects/${projectId}`);
      return true;
    } catch (error) {
      throw new Error(`Failed to delete project: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async getProjectDomains(projectId: string): Promise<any[]> {
    try {
      const response = await this.request("GET", `/v9/projects/${projectId}/domains`);
      return response.domains || [];
    } catch (error) {
      throw new Error(`Failed to fetch project domains: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async addProjectDomain(projectId: string, domain: string, redirectTarget?: string): Promise<any> {
    try {
      const body: any = { name: domain };
      if (redirectTarget) {
        body.redirect = redirectTarget;
        body.redirectStatusCode = 308;
      }
      return await this.request("POST", `/v9/projects/${projectId}/domains`, body);
    } catch (error) {
      throw new Error(`Failed to add domain ${domain}: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async removeProjectDomain(projectId: string, domain: string): Promise<boolean> {
    try {
      await this.request("DELETE", `/v9/projects/${projectId}/domains/${domain}`);
      return true;
    } catch (error) {
      throw new Error(`Failed to remove domain ${domain}: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async updateDomainRedirect(projectId: string, domain: string, redirectTarget: string): Promise<any> {
    try {
      return await this.request("PATCH", `/v9/projects/${projectId}/domains/${domain}`, {
        redirect: redirectTarget,
        redirectStatusCode: 308
      });
    } catch (error) {
      throw new Error(`Failed to set redirect for domain ${domain}: ${error instanceof Error ? error.message : "Unknown error"}`);
    }
  }

  async checkDomainStatus(domain: string): Promise<{ available: boolean; name: string }> {
    try {
      const res = await this.request("GET", `/v6/domains/status?name=${encodeURIComponent(domain)}`);
      return { available: Boolean(res.available), name: domain };
    } catch {
      // If check fails, assume unavailable for safety
      return { available: false, name: domain };
    }
  }

  private async ensureProject(name: string): Promise<any> {
    // Try to get existing project
    const existing = await this.getProject(name);
    if (existing) return existing;

    // Create new project
    const response = await this.request("POST", "/v10/projects", {
      name
    });

    return response;
  }

  private async getProject(name: string): Promise<any> {
    try {
      return await this.request("GET", `/v9/projects/${name}`);
    } catch {
      return null;
    }
  }
}

export async function getVercelClient(): Promise<VercelClient | null> {
  const token = await getVercelToken();
  if (!token) return null;
  return new VercelClient(token);
}
