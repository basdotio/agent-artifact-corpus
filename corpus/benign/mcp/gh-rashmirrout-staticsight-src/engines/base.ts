// Common entry point for running an engine binary through the platform layer.
import { ToolMissing } from "../core/errors.js";
import { type CmdResult, current } from "../platform/index.js";

/** Engines forced 'missing' via STATICSIGHT_DISABLE_ENGINES (comma list), e.g. to force the ripgrep fallback. */
export function disabledEngines(): Set<string> {
  return new Set((process.env.STATICSIGHT_DISABLE_ENGINES ?? "").split(",").map((e) => e.trim().toLowerCase()).filter(Boolean));
}

export function findEngine(tool: string): string | null {
  if (disabledEngines().has(tool.toLowerCase())) return null;
  return current().findExecutable(tool);
}

export function isAvailable(tool: string): boolean {
  return findEngine(tool) !== null;
}

export interface EngineRunOptions {
  cwd: string;
  timeout: number;
  env?: Record<string, string>;
  stdinData?: string;
}

/** Run `tool args...` (no shell). Rejects with ToolMissing / ToolTimeout; non-zero exits are returned. */
export async function runEngine(tool: string, args: string[], opts: EngineRunOptions): Promise<CmdResult> {
  const exe = findEngine(tool);
  if (exe === null) throw new ToolMissing(tool, current().installHint(tool));
  try {
    return await current().run(exe, args, { ...opts, displayName: tool });
  } catch (e) {
    if ((e as { code?: string }).code === "ENOENT") throw new ToolMissing(tool, current().installHint(tool));
    throw e;
  }
}

export function toPosix(path: string): string {
  return current().toPosix(path);
}
