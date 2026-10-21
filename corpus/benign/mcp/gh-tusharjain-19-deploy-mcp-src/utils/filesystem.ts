import fs from "fs";
import path from "path";

export async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fs.promises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

export async function readJsonFile(filePath: string): Promise<any> {
  const content = await fs.promises.readFile(filePath, "utf-8");
  return JSON.parse(content);
}

export async function readFile(filePath: string): Promise<string> {
  return fs.promises.readFile(filePath, "utf-8");
}

export function resolveProjectPath(projectPath: string): string {
  return path.resolve(process.cwd(), projectPath);
}
