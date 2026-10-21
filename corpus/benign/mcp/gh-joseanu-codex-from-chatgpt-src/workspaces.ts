import { realpath, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

export const DEFAULT_WORKSPACE_ROOT = path.join(os.homedir(), "workspace");

export class WorkspaceValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WorkspaceValidationError";
  }
}

function configuredRoot(root = process.env.CODEX_WORKSPACE_ROOT ?? DEFAULT_WORKSPACE_ROOT): string {
  if (!path.isAbsolute(root) || root.includes("\0") || root.split(path.sep).some((part) => part === "..")) {
    throw new WorkspaceValidationError("CODEX_WORKSPACE_ROOT debe ser una ruta absoluta sin segmentos '..'.");
  }
  return root;
}

/** Resolves an existing directory under the canonical, administrative workspace root. */
export async function validateWorkspace(input: string, rootInput?: string): Promise<string> {
  if (typeof input !== "string" || input.length === 0) {
    throw new WorkspaceValidationError("workspace debe ser una ruta no vacía.");
  }
  if (input.includes("\0")) {
    throw new WorkspaceValidationError("workspace contiene un byte NUL inválido.");
  }
  if (!path.isAbsolute(input)) {
    throw new WorkspaceValidationError("workspace debe ser una ruta absoluta.");
  }
  if (input.split(path.sep).some((part) => part === "..")) {
    throw new WorkspaceValidationError("workspace no puede contener segmentos '..'.");
  }

  const rootInputValue = configuredRoot(rootInput);
  let root: string;
  let candidate: string;
  try {
    root = await realpath(rootInputValue);
    if (!(await stat(root)).isDirectory()) throw new Error("la raíz no es un directorio");
    candidate = await realpath(path.resolve(input));
    if (!(await stat(candidate)).isDirectory()) throw new Error("el workspace no es un directorio");
  } catch {
    throw new WorkspaceValidationError(`workspace no existe o no puede resolverse: ${input}`);
  }

  const relative = path.relative(root, candidate);
  const escapesRoot = relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative);
  if (escapesRoot) {
    throw new WorkspaceValidationError(`workspace debe estar dentro de ${rootInputValue}: ${input}`);
  }
  return candidate;
}
