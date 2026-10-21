import { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import { z } from "zod";
import { detectProject } from "./utils/framework-detector.js";
import { checkProject } from "./tools/check-project.js";
import { deployToVercel, getDeploymentStatus } from "./tools/deploy.js";
import { getDeploymentLogs } from "./tools/logs.js";
import { validateEnvironmentVariables, scanEnv, compareEnv, syncEnv, createEnvExample } from "./tools/env-vars.js";
import { gitStatus, gitCommitAndPush, checkEnvLeak } from "./tools/git.js";
import { diagnoseBuildFailure } from "./tools/diagnose.js";
import { projectReport } from "./tools/project-report.js";
import { smartDeploy } from "./tools/smart-deploy.js";
import { deleteProject } from "./tools/delete-project.js";
import { rateLimiter } from "./utils/rate-limiter.js";
import { DeployMcpError, ValidationError } from "./utils/errors.js";
import { checkForUpdates } from "./utils/version-checker.js";
import { checkDomainAvailability, manageDomain } from "./tools/domains.js";

const server = new McpServer({
  name: "deploy-mcp",
  version: "1.0.0"
});

server.server.setRequestHandler(
  "tools/list",
  async () => {
    return {
      tools: [
        {
          name: "smart_deploy",
          description: "Deploy to Vercel with auto-polling. On failure, automatically fetches logs and diagnoses the error so the AI can fix it and redeploy.",
          inputSchema: {
            type: "object",
            properties: {
              projectPath: { type: "string", description: "Absolute path to the project" },
              projectName: { type: "string", description: "Vercel project name" },
              maxPollSeconds: { type: "number", description: "Max seconds to wait for deployment (default 180)" }
            },
            required: ["projectPath", "projectName"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: false,
          openWorldHint: true
        },
        {
          name: "detect_project",
          description: "Detect framework and build configuration",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "check_project",
          description: "Validate project can be deployed",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "delete_project",
          description: "Permanently delete a Vercel project. Triggers a secure native OS prompt that the user MUST manually click to approve.",
          inputSchema: {
            type: "object",
            properties: { projectName: { type: "string" } },
            required: ["projectName"]
          } as any,
          readOnlyHint: false,
          destructiveHint: true,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "deploy_to_vercel",
          description: "Deploy project to Vercel",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" }, projectName: { type: "string" } },
            required: ["projectPath", "projectName"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: false,
          openWorldHint: true
        },
        {
          name: "get_deployment_status",
          description: "Check deployment status",
          inputSchema: {
            type: "object",
            properties: { projectName: { type: "string" } },
            required: ["projectName"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "get_deployment_logs",
          description: "Get deployment logs for a project",
          inputSchema: {
            type: "object",
            properties: { projectName: { type: "string" } },
            required: ["projectName"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "scan_env",
          description: "Scan local environment variables (redacted for security)",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "compare_env",
          description: "Compare local environment variables against Vercel",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" }, projectName: { type: "string" } },
            required: ["projectPath", "projectName"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "sync_env",
          description: "Safely sync missing environment variables to Vercel",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" }, projectName: { type: "string" }, keysToSync: { type: "array", items: { type: "string" } }, overwrite: { type: "boolean" } },
            required: ["projectPath", "projectName", "keysToSync"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "create_env_example",
          description: "Automatically generate a .env.example file",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "check_env_leak",
          description: "Check if .env files are accidentally tracked by Git",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "project_report",
          description: "Get a comprehensive pre-flight project report",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" }, projectName: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "validate_environment_variables",
          description: "Validate required environment variables for a project",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "git_status",
          description: "Check the git status of a project",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" } },
            required: ["projectPath"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "git_commit_and_push",
          description: "Commit and push changes to git",
          inputSchema: {
            type: "object",
            properties: { projectPath: { type: "string" }, message: { type: "string" } },
            required: ["projectPath", "message"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: false,
          openWorldHint: true
        },
        {
          name: "diagnose_build_failure",
          description: "Diagnose a build failure from logs",
          inputSchema: {
            type: "object",
            properties: { logs: { type: "array", items: { type: "string" } } },
            required: ["logs"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: false
        },
        {
          name: "check_for_updates",
          description: "Check npm registry for Deploy MCP server updates and new features",
          inputSchema: {
            type: "object",
            properties: {}
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "check_domain_availability",
          description: "Check if a domain or alias is available on Vercel. If unavailable, returns the top 2 best available alternative suggestions.",
          inputSchema: {
            type: "object",
            properties: { domainName: { type: "string" } },
            required: ["domainName"]
          } as any,
          readOnlyHint: true,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        },
        {
          name: "manage_domain",
          description: "Assign a new domain to a Vercel project, with options to remove or redirect (308) the old domain.",
          inputSchema: {
            type: "object",
            properties: {
              projectName: { type: "string" },
              newDomain: { type: "string" },
              oldDomain: { type: "string" },
              oldDomainAction: { type: "string", enum: ["remove", "redirect"] }
            },
            required: ["projectName", "newDomain"]
          } as any,
          readOnlyHint: false,
          destructiveHint: false,
          idempotentHint: true,
          openWorldHint: true
        }
      ]
    };
  }
);

server.server.setRequestHandler(
  "tools/call",
  async (request) => {
    const { name, arguments: args } = request as any;

    try {
      // 1. Enforce rate limits
      rateLimiter.checkRateLimit(name);

      // Helper for path/string validation
      const requireStringParam = (paramName: string, val: any): string => {
        if (typeof val !== "string" || val.trim().length === 0) {
          throw new ValidationError(paramName, `Must be a non-empty string.`);
        }
        return val.trim();
      };

      if (name === "smart_deploy") {
        const { projectPath, projectName, maxPollSeconds } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const validName = requireStringParam("projectName", projectName);
        const result = await smartDeploy(validPath, validName, maxPollSeconds);
        const text = result.failed && result.aiInstruction
          ? result.aiInstruction + "\n\n--- Full Result ---\n" + JSON.stringify(result, null, 2)
          : JSON.stringify(result, null, 2);
        return { content: [{ type: "text", text }] };
      }

      if (name === "detect_project") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await detectProject(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "check_project") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await checkProject(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "delete_project") {
        const { projectName } = args || {};
        const validName = requireStringParam("projectName", projectName);
        const result = await deleteProject(validName);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "deploy_to_vercel") {
        const { projectPath, projectName } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const validName = requireStringParam("projectName", projectName);
        const result = await deployToVercel(validPath, validName);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "get_deployment_status") {
        const { projectName } = args || {};
        const validName = requireStringParam("projectName", projectName);
        const result = await getDeploymentStatus(validName);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "get_deployment_logs") {
        const { projectName } = args || {};
        const validName = requireStringParam("projectName", projectName);
        const result = await getDeploymentLogs(validName);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "scan_env") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await scanEnv(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "compare_env") {
        const { projectPath, projectName } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const validName = requireStringParam("projectName", projectName);
        const result = await compareEnv(validPath, validName);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "sync_env") {
        const { projectPath, projectName, keysToSync, overwrite } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const validName = requireStringParam("projectName", projectName);
        if (!Array.isArray(keysToSync)) {
          throw new ValidationError("keysToSync", "Must be an array of string key names.");
        }
        const result = await syncEnv(validPath, validName, keysToSync, overwrite);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "create_env_example") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await createEnvExample(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "check_env_leak") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await checkEnvLeak(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "project_report") {
        const { projectPath, projectName } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await projectReport(validPath, projectName);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "validate_environment_variables") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await validateEnvironmentVariables(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "git_status") {
        const { projectPath } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const result = await gitStatus(validPath);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "git_commit_and_push") {
        const { projectPath, message } = args || {};
        const validPath = requireStringParam("projectPath", projectPath);
        const validMsg = requireStringParam("message", message);
        const result = await gitCommitAndPush(validPath, validMsg);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "diagnose_build_failure") {
        const { logs } = args || {};
        if (!Array.isArray(logs)) {
          throw new ValidationError("logs", "Must be an array of log string lines.");
        }
        const result = await diagnoseBuildFailure(logs);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "check_for_updates") {
        const result = await checkForUpdates();
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "check_domain_availability") {
        const { domainName } = args || {};
        const validDomain = requireStringParam("domainName", domainName);
        const result = await checkDomainAvailability(validDomain);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      if (name === "manage_domain") {
        const { projectName, newDomain, oldDomain, oldDomainAction } = args || {};
        const validProject = requireStringParam("projectName", projectName);
        const validNewDomain = requireStringParam("newDomain", newDomain);
        const action = oldDomainAction === "remove" ? "remove" : "redirect";
        const result = await manageDomain(validProject, validNewDomain, oldDomain, action);
        return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
      }

      throw new ValidationError("toolName", `Unknown tool: ${name}`);
    } catch (err: any) {
      if (err instanceof DeployMcpError) {
        return {
          content: [{ type: "text", text: JSON.stringify(err.toStructuredSignal(), null, 2) }],
          isError: true
        };
      }
      const genericError = new DeployMcpError(
        "ERR_INTERNAL_FAILURE",
        err instanceof Error ? err.message : String(err),
        "Review tool arguments and check system logs."
      );
      return {
        content: [{ type: "text", text: JSON.stringify(genericError.toStructuredSignal(), null, 2) }],
        isError: true
      };
    }
  }
);

export async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("\x1b[38;2;0;229;255m\x1b[1m🚀 Deploy MCP server running on stdio\x1b[0m");
}

main().catch(console.error);
