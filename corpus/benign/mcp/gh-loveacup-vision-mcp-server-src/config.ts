import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import type { VisionConfig } from "./types.js";

function loadConfigFile(): Partial<VisionConfig> {
  const candidates = [
    resolve(process.cwd(), "config.json"),
    resolve(process.cwd(), "vision-mcp.config.json"),
  ];
  for (const path of candidates) {
    if (existsSync(path)) {
      try {
        return JSON.parse(readFileSync(path, "utf-8"));
      } catch {
        // ignore malformed config files
      }
    }
  }
  return {};
}

export function loadConfig(): VisionConfig {
  const file = loadConfigFile();

  const baseUrl =
    process.env.VISION_BASE_URL ||
    file.baseUrl ||
    "";
  const model =
    process.env.VISION_MODEL ||
    file.model ||
    "Qwen3-VL-32B";
  const apiKey =
    process.env.VISION_API_KEY ||
    file.apiKey ||
    "";
  const maxTokens = Number(
    process.env.VISION_MAX_TOKENS || file.maxTokens || 4096
  );
  const temperature = Number(
    process.env.VISION_TEMPERATURE || file.temperature || 0.7
  );

  if (!baseUrl) {
    throw new Error(
      "VISION_BASE_URL is required. Set it via environment variable or config.json."
    );
  }

  return { baseUrl, model, apiKey, maxTokens, temperature };
}
