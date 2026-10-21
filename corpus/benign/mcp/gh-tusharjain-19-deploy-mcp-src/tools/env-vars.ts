import fs from "fs";
import path from "path";
import { fileExists, readFile } from "../utils/filesystem.js";
import { getVercelClient } from "../vercel/client.js";

// Basic Env Parsing (Doesn't rely on dotenv for MVP)
function parseEnvContent(content: string): Record<string, string> {
  const result: Record<string, string> = {};
  const lines = content.split('\n');
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#')) {
      const match = trimmed.match(/^([a-zA-Z_][a-zA-Z0-9_]*)=(.*)$/);
      if (match) {
        result[match[1]] = match[2];
      }
    }
  }
  return result;
}

export interface EnvScanResult {
  variables: {
    key: string;
    classification: "Public" | "Client-visible" | "Secret";
  }[];
  message: string;
}

export async function scanEnv(projectPath: string): Promise<EnvScanResult> {
  const envFiles = ['.env', '.env.local', '.env.production', '.env.development'];
  const allVars: Record<string, string> = {};
  let detected = 0;

  for (const file of envFiles) {
    const filePath = path.join(projectPath, file);
    if (await fileExists(filePath)) {
      const content = await readFile(filePath);
      const parsed = parseEnvContent(content);
      for (const [k, v] of Object.entries(parsed)) {
        allVars[k] = v;
      }
    }
  }

  const variables = Object.keys(allVars).map(key => {
    let classification: "Public" | "Client-visible" | "Secret" = "Secret";
    const kUpper = key.toUpperCase();
    if (kUpper.startsWith("NEXT_PUBLIC_")) classification = "Public";
    else if (kUpper.startsWith("VITE_")) classification = "Public";
    else if (kUpper.includes("ANON_KEY")) classification = "Client-visible";
    
    return { key, classification };
  });

  return {
    variables,
    message: `${variables.length} environment variables detected. Values hidden for security.`
  };
}

export interface EnvDiffResult {
  diff: {
    key: string;
    local: "Exists" | "Missing";
    vercel: "Exists" | "Missing";
    conflict: boolean;
  }[];
  summary: {
    missingInVercel: number;
    configuredInVercel: number;
    conflicts: number;
  };
}

export async function compareEnv(projectPath: string, projectName: string): Promise<EnvDiffResult> {
  // Read local vars
  const envFiles = ['.env', '.env.local', '.env.production', '.env.development'];
  const localVars: Record<string, string> = {};

  for (const file of envFiles) {
    const filePath = path.join(projectPath, file);
    if (await fileExists(filePath)) {
      const content = await readFile(filePath);
      const parsed = parseEnvContent(content);
      for (const [k, v] of Object.entries(parsed)) {
        localVars[k] = v;
      }
    }
  }

  // Read vercel vars
  const client = await getVercelClient();
  if (!client) throw new Error("Vercel client not authenticated");

  // We need the projectId. Let's get it by name.
  // The SDK doesn't expose getProject directly without private, but we can do a hack or we assume we can fetch it.
  // In `client.ts` we added `getEnvironmentVariables(projectId)`. Let's fetch project first.
  const projects = await client["request"]("GET", "/v9/projects");
  const project = projects.projects.find((p: any) => p.name === projectName);
  
  if (!project) {
    throw new Error(`Project ${projectName} not found on Vercel`);
  }

  const vercelVarsRaw = await client.getEnvironmentVariables(project.id);
  const vercelKeys = new Set(vercelVarsRaw.map(v => v.key));

  const diff: EnvDiffResult["diff"] = [];
  
  const allKeys = new Set([...Object.keys(localVars), ...vercelKeys]);

  for (const key of allKeys) {
    const hasLocal = key in localVars;
    const hasVercel = vercelKeys.has(key);
    
    // We can't strictly detect conflict without knowing Vercel's decrypted value (which is impossible)
    // But we mark it as "conflict" meaning "It exists locally AND in Vercel. Be careful overwriting it."
    const conflict = hasLocal && hasVercel;

    diff.push({
      key,
      local: hasLocal ? "Exists" : "Missing",
      vercel: hasVercel ? "Exists" : "Missing",
      conflict
    });
  }

  const missingInVercel = diff.filter(d => d.local === "Exists" && d.vercel === "Missing").length;
  const configuredInVercel = diff.filter(d => d.vercel === "Exists").length;
  const conflicts = diff.filter(d => d.conflict).length;

  return {
    diff,
    summary: { missingInVercel, configuredInVercel, conflicts }
  };
}

export async function syncEnv(
  projectPath: string, 
  projectName: string, 
  keysToSync: string[],
  overwrite: boolean = false
): Promise<{ success: boolean; synced: string[]; skipped: string[]; error?: string }> {
  try {
    const envFiles = ['.env', '.env.local', '.env.production', '.env.development'];
    const localVars: Record<string, string> = {};

    for (const file of envFiles) {
      const filePath = path.join(projectPath, file);
      if (await fileExists(filePath)) {
        const content = await readFile(filePath);
        const parsed = parseEnvContent(content);
        for (const [k, v] of Object.entries(parsed)) {
          localVars[k] = v;
        }
      }
    }

    const client = await getVercelClient();
    if (!client) throw new Error("Vercel client not authenticated");

    const projects = await client["request"]("GET", "/v9/projects");
    const project = projects.projects.find((p: any) => p.name === projectName);
    if (!project) throw new Error(`Project ${projectName} not found on Vercel`);

    const vercelVarsRaw = await client.getEnvironmentVariables(project.id);
    const vercelKeys = new Set(vercelVarsRaw.map(v => v.key));

    const synced: string[] = [];
    const skipped: string[] = [];

    for (const key of keysToSync) {
      if (!localVars[key]) {
        skipped.push(key);
        continue;
      }
      if (vercelKeys.has(key) && !overwrite) {
        skipped.push(key);
        continue;
      }

      await client.createEnvironmentVariable(project.id, key, localVars[key]);
      synced.push(key);
    }

    return { success: true, synced, skipped };
  } catch (err) {
    return { success: false, synced: [], skipped: [], error: err instanceof Error ? err.message : String(err) };
  }
}

export async function createEnvExample(projectPath: string): Promise<{ success: boolean; message: string }> {
  try {
    const envFiles = ['.env', '.env.local'];
    const localVars: Record<string, string> = {};

    for (const file of envFiles) {
      const filePath = path.join(projectPath, file);
      if (await fileExists(filePath)) {
        const content = await readFile(filePath);
        const parsed = parseEnvContent(content);
        for (const [k, v] of Object.entries(parsed)) {
          localVars[k] = v;
        }
      }
    }

    if (Object.keys(localVars).length === 0) {
      return { success: false, message: "No local environment variables found to create .env.example from." };
    }

    const exampleContent = Object.keys(localVars).map(key => `${key}=`).join("\n") + "\n";
    const examplePath = path.join(projectPath, ".env.example");
    
    fs.writeFileSync(examplePath, exampleContent, "utf-8");
    return { success: true, message: "Created .env.example with redacted values." };
  } catch (err) {
    return { success: false, message: err instanceof Error ? err.message : String(err) };
  }
}

// Keep the old validateEnvironmentVariables for backward compatibility during this upgrade
export interface EnvValidationResult {
  required: string[];
  missing: string[];
  configured: string[];
}
export async function validateEnvironmentVariables(
  projectPath: string
): Promise<EnvValidationResult> {
  const result: EnvValidationResult = { required: [], missing: [], configured: [] };
  // Stubbed for compatibility
  return result;
}
