import { readJsonFile, fileExists } from "./filesystem.js";
import path from "path";

export interface ProjectDetection {
  framework: string | null;
  packageManager: "npm" | "yarn" | "pnpm" | "bun";
  nodeVersion: string | null;
  buildCommand: string | null;
  detected: boolean;
  error?: string;
}

export async function detectProject(
  projectPath: string
): Promise<ProjectDetection> {
  try {
    const packageJsonPath = path.join(projectPath, "package.json");
    
    // Check if package.json exists
    if (!(await fileExists(packageJsonPath))) {
      return {
        framework: null,
        packageManager: "npm",
        nodeVersion: null,
        buildCommand: null,
        detected: false,
        error: "No package.json found"
      };
    }

    const packageJson = await readJsonFile(packageJsonPath);
    const dependencies = {
      ...packageJson.dependencies,
      ...packageJson.devDependencies
    };

    // Detect framework
    let framework: string | null = null;

    if (dependencies["next"]) {
      framework = "Next.js";
    } else if (dependencies["react"] && dependencies["vite"]) {
      framework = "React + Vite";
    } else if (dependencies["vue"]) {
      framework = "Vue 3";
    } else if (dependencies["astro"]) {
      framework = "Astro";
    } else if (dependencies["remix"]) {
      framework = "Remix";
    } else if (dependencies["svelte"]) {
      framework = "Svelte";
    } else if (dependencies["react"]) {
      framework = "React (CRA)";
    } else {
      framework = "Static HTML/CSS/JS";
    }

    // Detect package manager
    let packageManager: "npm" | "yarn" | "pnpm" | "bun" = "npm";
    if (await fileExists(path.join(projectPath, "yarn.lock"))) {
      packageManager = "yarn";
    } else if (await fileExists(path.join(projectPath, "pnpm-lock.yaml"))) {
      packageManager = "pnpm";
    } else if (await fileExists(path.join(projectPath, "bun.lockb"))) {
      packageManager = "bun";
    }

    // Get build command
    const buildCommand = packageJson.scripts?.build || "npm run build";

    // Get Node version requirement
    const nodeVersion = packageJson.engines?.node || null;

    return {
      framework,
      packageManager,
      nodeVersion,
      buildCommand,
      detected: true
    };
  } catch (error) {
    return {
      framework: null,
      packageManager: "npm",
      nodeVersion: null,
      buildCommand: null,
      detected: false,
      error: error instanceof Error ? error.message : "Unknown error"
    };
  }
}
