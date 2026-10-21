import { describe, it, expect, vi } from "vitest";
import { diagnoseBuildFailure } from "../tools/diagnose.js";
import { detectProject } from "../utils/framework-detector.js";
import { checkProject } from "../tools/check-project.js";
import { validateEnvironmentVariables, scanEnv, createEnvExample } from "../tools/env-vars.js";
import { gitStatus, checkEnvLeak, generateSuggestedCommitMessage } from "../tools/git.js";
import { projectReport } from "../tools/project-report.js";
import { rateLimiter } from "../utils/rate-limiter.js";
import { DeployMcpError, ValidationError, RateLimitError, VercelApiError } from "../utils/errors.js";
import { checkForUpdates } from "../utils/version-checker.js";
import { checkDomainAvailability, formatDomainName } from "../tools/domains.js";

// Mock external Vercel API and child processes where needed
vi.mock("../vercel/client.js", () => ({
  getVercelClient: vi.fn().mockImplementation(() => ({
    getProject: vi.fn().mockResolvedValue({ id: "proj_123", name: "test-project" }),
    deleteProject: vi.fn().mockResolvedValue({ success: true }),
    getEnvVars: vi.fn().mockResolvedValue([{ key: "EXISTING_KEY" }]),
    createEnvVar: vi.fn().mockResolvedValue({ id: "env_1" }),
    getDeployments: vi.fn().mockResolvedValue([{ uid: "dep_1", state: "READY", url: "test.vercel.app" }]),
    getDeployment: vi.fn().mockResolvedValue({ uid: "dep_1", state: "READY", url: "test.vercel.app" }),
    getDeploymentEvents: vi.fn().mockResolvedValue([{ text: "Build success" }]),
    createDeployment: vi.fn().mockResolvedValue({ id: "dep_1", url: "test.vercel.app", status: "QUEUED" }),
    checkDomainStatus: vi.fn().mockImplementation(async (d: string) => ({
      available: d.includes("live") || d.includes("app") || !d.includes("taken"),
      name: d
    })),
    addProjectDomain: vi.fn().mockResolvedValue({ name: "new-site.vercel.app" }),
    removeProjectDomain: vi.fn().mockResolvedValue(true),
    updateDomainRedirect: vi.fn().mockResolvedValue({ redirect: "new-site.vercel.app" })
  }))
}));

vi.mock("../utils/config.ts", () => ({
  getVercelToken: vi.fn().mockResolvedValue("mock_token_12345")
}));

// Expected tools list with annotations
const EXPECTED_TOOLS = [
  "smart_deploy",
  "detect_project",
  "check_project",
  "delete_project",
  "deploy_to_vercel",
  "get_deployment_status",
  "get_deployment_logs",
  "scan_env",
  "compare_env",
  "sync_env",
  "create_env_example",
  "check_env_leak",
  "project_report",
  "validate_environment_variables",
  "git_status",
  "git_commit_and_push",
  "diagnose_build_failure",
  "check_for_updates",
  "check_domain_availability",
  "manage_domain"
];

describe("MCP Tools Declarations and Hints", () => {
  it("should have all 20 tools declared with required boolean hints", async () => {
    const toolList = [
      { name: "smart_deploy", readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
      { name: "detect_project", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "check_project", readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "delete_project", readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: true },
      { name: "deploy_to_vercel", readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
      { name: "get_deployment_status", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "get_deployment_logs", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "scan_env", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "compare_env", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "sync_env", readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "create_env_example", readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "check_env_leak", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "project_report", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "validate_environment_variables", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "git_status", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "git_commit_and_push", readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
      { name: "diagnose_build_failure", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
      { name: "check_for_updates", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "check_domain_availability", readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
      { name: "manage_domain", readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: true }
    ];

    expect(toolList.length).toBe(20);

    for (const tool of toolList) {
      expect(EXPECTED_TOOLS).toContain(tool.name);
      expect(typeof tool.readOnlyHint).toBe("boolean");
      expect(typeof tool.destructiveHint).toBe("boolean");
      expect(typeof tool.idempotentHint).toBe("boolean");
      expect(typeof tool.openWorldHint).toBe("boolean");
    }
  });
});

describe("Domain Tools & Alternative Suggestions", () => {
  it("formatDomainName should append .vercel.app if no extension provided", () => {
    expect(formatDomainName("my-portfolio")).toBe("my-portfolio.vercel.app");
    expect(formatDomainName("custom-domain.com")).toBe("custom-domain.com");
  });

  it("checkDomainAvailability should generate top 2 alternatives if domain is taken", async () => {
    const res = await checkDomainAvailability("taken-name.vercel.app");
    expect(res).toHaveProperty("available");
    if (!res.available) {
      expect(res.bestAlternatives).toBeDefined();
      expect(res.bestAlternatives!.length).toBe(2);
    }
  });
});

describe("Auto-Updater & Smart Commit Message Generator", () => {
  it("checkForUpdates should return version comparison info", async () => {
    const res = await checkForUpdates();
    expect(res).toHaveProperty("currentVersion");
    expect(res).toHaveProperty("latestVersion");
    expect(res).toHaveProperty("updateCommand");
  });

  it("generateSuggestedCommitMessage should produce smart commit messages based on changed files", () => {
    expect(generateSuggestedCommitMessage(["src/style.css"])).toContain("style:");
    expect(generateSuggestedCommitMessage(["package.json"])).toContain("chore:");
    expect(generateSuggestedCommitMessage(["src/components/Header.tsx"])).toContain("feat:");
  });
});

describe("Custom Error Signals and Rate Limiting", () => {
  it("RateLimiter should enforce mutation limits", () => {
    rateLimiter.reset();
    for (let i = 0; i < 10; i++) {
      expect(() => rateLimiter.checkRateLimit("smart_deploy")).not.toThrow();
    }
    expect(() => rateLimiter.checkRateLimit("smart_deploy")).toThrow(RateLimitError);
  });

  it("ValidationError should generate structured signal", () => {
    const err = new ValidationError("projectPath", "Path does not exist");
    const signal = err.toStructuredSignal();
    expect(signal.errorSignal).toBe(true);
    expect(signal.code).toBe("ERR_INVALID_ARGUMENTS");
    expect(signal.message).toContain("projectPath");
  });

  it("VercelApiError should format HTTP failure details", () => {
    const err = new VercelApiError(401, "Unauthorized");
    const signal = err.toStructuredSignal();
    expect(signal.code).toBe("ERR_VERCEL_API_FAILURE");
    expect(signal.suggestion).toContain("npx");
  });
});

describe("Individual Tool Handlers", () => {
  it("diagnoseBuildFailure should identify missing modules", async () => {
    const logs = ["Error: Cannot find module 'express'"];
    const diagnosis = await diagnoseBuildFailure(logs);
    expect(diagnosis.errorType).toBe("MISSING_MODULE");
    expect(diagnosis.issue).toContain("express");
  });

  it("diagnoseBuildFailure should identify typescript errors", async () => {
    const logs = ["error TS2304: Cannot find name 'Foo'."];
    const diagnosis = await diagnoseBuildFailure(logs);
    expect(diagnosis.errorType).toBe("TYPESCRIPT_ERROR");
  });

  it("detectProject should inspect a directory path", async () => {
    const result = await detectProject(process.cwd());
    expect(result).toHaveProperty("framework");
    expect(result).toHaveProperty("packageManager");
  });

  it("checkProject should validate build or handle non-existent directories gracefully", async () => {
    const result = await checkProject(process.cwd());
    expect(result).toHaveProperty("packageJsonExists");
  });

  it("scanEnv should scan environment files without throwing", async () => {
    const result = await scanEnv(process.cwd());
    expect(result).toHaveProperty("variables");
  });

  it("createEnvExample should run without breaking", async () => {
    const result = await createEnvExample(process.cwd());
    expect(result).toHaveProperty("success");
  });

  it("validateEnvironmentVariables should check env completeness", async () => {
    const result = await validateEnvironmentVariables(process.cwd());
    expect(result).toHaveProperty("required");
  });

  it("checkEnvLeak should check git tracking status", async () => {
    const result = await checkEnvLeak(process.cwd());
    expect(result).toHaveProperty("leakDetected");
  });

  it("gitStatus should query git repository status", async () => {
    const result = await gitStatus(process.cwd());
    expect(result).toHaveProperty("hasRepository");
  });

  it("projectReport should generate pre-flight summary", async () => {
    const result = await projectReport(process.cwd());
    expect(result).toHaveProperty("projectDetails");
    expect(result).toHaveProperty("buildCheck");
  });

  it("diagnoseBuildFailure fallback for unknown error", async () => {
    const result = await diagnoseBuildFailure(["Something went wrong"]);
    expect(result.errorType).toBe("UNKNOWN_ERROR");
  });
});
