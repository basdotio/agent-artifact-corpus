import { spawn } from "child_process";
import path from "path";
import { fileExists } from "../utils/filesystem.js";

export interface GitStatusResult {
  hasRepository: boolean;
  branch?: string;
  uncommittedChanges?: number;
  files?: string[];
  suggestedCommitMessage?: string;
}

async function runGitCommand(args: string[], cwd: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("git", args, { cwd });
    let output = "";
    
    child.stdout.on("data", data => { output += data.toString(); });
    
    child.on("close", code => {
      if (code === 0) resolve(output.trim());
      else reject(new Error(`Git command failed with code ${code}`));
    });
    
    child.on("error", err => reject(err));
  });
}

export function generateSuggestedCommitMessage(files: string[]): string {
  if (files.length === 0) return "feat: update website";

  const lowerFiles = files.map(f => f.toLowerCase());

  if (lowerFiles.some(f => f.includes("package.json") || f.includes("package-lock.json"))) {
    return "chore: update project configuration and dependencies";
  }
  if (lowerFiles.some(f => f.endsWith(".css") || f.endsWith(".scss") || f.includes("style") || f.includes("layout"))) {
    return "style: update website styling and UI layout";
  }
  if (lowerFiles.some(f => f.endsWith(".tsx") || f.endsWith(".jsx") || f.endsWith(".vue") || f.endsWith(".html"))) {
    return "feat: update website pages and UI components";
  }
  return `feat: update ${files.slice(0, 3).map(f => path.basename(f)).join(", ")}`;
}

export async function gitStatus(projectPath: string): Promise<GitStatusResult> {
  try {
    const gitPath = path.join(projectPath, ".git");
    if (!(await fileExists(gitPath))) {
      return { hasRepository: false };
    }

    const branch = await runGitCommand(["rev-parse", "--abbrev-ref", "HEAD"], projectPath);
    const statusOutput = await runGitCommand(["status", "--porcelain"], projectPath);
    
    const files = statusOutput.split('\n').filter(Boolean).map(line => line.substring(3));
    const suggestedCommitMessage = generateSuggestedCommitMessage(files);

    return {
      hasRepository: true,
      branch,
      uncommittedChanges: files.length,
      files,
      suggestedCommitMessage
    };
  } catch (error) {
    return { hasRepository: false };
  }
}

export async function gitCommitAndPush(
  projectPath: string,
  message: string
): Promise<{ success: boolean; commitHash?: string; error?: string }> {
  try {
    // Stage all changed files
    await runGitCommand(["add", "."], projectPath);
    
    // Commit
    await runGitCommand(["commit", "-m", message], projectPath);
    
    // Get commit hash
    const commitHash = await runGitCommand(["rev-parse", "--short", "HEAD"], projectPath);
    
    // Push
    await runGitCommand(["push"], projectPath);
    
    return { success: true, commitHash };
  } catch (error) {
    return { 
      success: false, 
      error: error instanceof Error ? error.message : "Git operation failed" 
    };
  }
}

export async function checkEnvLeak(projectPath: string): Promise<{ leakDetected: boolean; trackedFiles: string[] }> {
  try {
    const gitPath = path.join(projectPath, ".git");
    if (!(await fileExists(gitPath))) {
      return { leakDetected: false, trackedFiles: [] };
    }

    const output = await runGitCommand(["ls-files"], projectPath);
    const files = output.split('\n').filter(Boolean);
    
    const trackedEnvs = files.filter(f => f === '.env' || f.startsWith('.env.') && f !== '.env.example');
    
    return {
      leakDetected: trackedEnvs.length > 0,
      trackedFiles: trackedEnvs
    };
  } catch (error) {
    return { leakDetected: false, trackedFiles: [] };
  }
}
