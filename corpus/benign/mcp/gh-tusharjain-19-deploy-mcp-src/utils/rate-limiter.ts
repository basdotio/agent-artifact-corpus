import { RateLimitError } from "./errors.js";

interface ToolLimitConfig {
  maxRequests: number;
  windowMs: number;
}

const DEFAULT_MUTATION_LIMIT: ToolLimitConfig = { maxRequests: 10, windowMs: 60_000 };
const DEFAULT_READ_LIMIT: ToolLimitConfig = { maxRequests: 30, windowMs: 60_000 };

const MUTATION_TOOLS = new Set([
  "smart_deploy",
  "deploy_to_vercel",
  "delete_project",
  "sync_env",
  "create_env_example",
  "git_commit_and_push"
]);

class ToolRateLimiter {
  private callHistory: Map<string, number[]> = new Map();

  public checkRateLimit(toolName: string): void {
    const config = MUTATION_TOOLS.has(toolName)
      ? DEFAULT_MUTATION_LIMIT
      : DEFAULT_READ_LIMIT;

    const now = Date.now();
    const windowStart = now - config.windowMs;

    let timestamps = this.callHistory.get(toolName) || [];
    // Prune timestamps older than window
    timestamps = timestamps.filter(t => t > windowStart);

    if (timestamps.length >= config.maxRequests) {
      const oldest = timestamps[0];
      const resetInSeconds = Math.max(1, Math.ceil((oldest + config.windowMs - now) / 1000));
      throw new RateLimitError(toolName, resetInSeconds);
    }

    timestamps.push(now);
    this.callHistory.set(toolName, timestamps);
  }

  public reset(): void {
    this.callHistory.clear();
  }
}

export const rateLimiter = new ToolRateLimiter();
