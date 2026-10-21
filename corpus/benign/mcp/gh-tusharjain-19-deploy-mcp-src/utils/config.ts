import fs from "fs";
import path from "path";
import os from "os";

const CONFIG_DIR = path.join(os.homedir(), ".deploy-mcp");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");

export interface Config {
  vercelToken?: string;
  vercelTeamId?: string;
  projects: Record<string, string>; // projectPath -> vercelProjectId
}

async function ensureConfigDir() {
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
}

export async function loadConfig(): Promise<Config> {
  await ensureConfigDir();
  
  if (!fs.existsSync(CONFIG_FILE)) {
    return { projects: {} };
  }

  try {
    const content = fs.readFileSync(CONFIG_FILE, "utf-8");
    return JSON.parse(content);
  } catch {
    return { projects: {} };
  }
}

export async function saveConfig(config: Config): Promise<void> {
  await ensureConfigDir();
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
}

export async function getVercelToken(): Promise<string | null> {
  const config = await loadConfig();
  return config.vercelToken || null;
}

export async function setVercelToken(token: string): Promise<void> {
  const config = await loadConfig();
  config.vercelToken = token;
  await saveConfig(config);
}
