import { detectProject } from "../utils/framework-detector.js";
import { gitStatus, checkEnvLeak } from "./git.js";
import { checkProject } from "./check-project.js";
import { scanEnv, compareEnv } from "./env-vars.js";
import { scanForLargeFiles, LargeFile } from "../utils/scanner.js";

export interface ProjectReportResult {
  projectDetails: any;
  git: any;
  buildCheck: any;
  environment: {
    scan: any;
    diff: any;
  };
  largeFiles: LargeFile[];
}

export async function projectReport(
  projectPath: string,
  projectName?: string
): Promise<ProjectReportResult> {
  const [project, git, build, envScan, leakCheck, largeFiles] = await Promise.all([
    detectProject(projectPath),
    gitStatus(projectPath),
    checkProject(projectPath),
    scanEnv(projectPath),
    checkEnvLeak(projectPath),
    scanForLargeFiles(projectPath)
  ]);

  let envDiff = null;
  if (projectName) {
    try {
      envDiff = await compareEnv(projectPath, projectName);
    } catch (e) {
      // Ignore if vercel fetch fails (e.g., project not deployed yet)
    }
  }

  return {
    projectDetails: project,
    git: {
      ...git,
      leakDetected: leakCheck.leakDetected,
      leakedFiles: leakCheck.trackedFiles
    },
    buildCheck: build,
    environment: {
      scan: envScan,
      diff: envDiff
    },
    largeFiles
  };
}
