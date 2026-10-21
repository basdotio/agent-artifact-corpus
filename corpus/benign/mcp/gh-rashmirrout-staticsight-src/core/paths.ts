// Workspace path confinement: every file argument must resolve inside WORKSPACE_ROOT.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { basename, isAbsolute, join, relative, resolve, sep } from "node:path";
import { current as currentPlatform } from "../platform/index.js";
import { InvalidArgument, StaticSightError } from "./errors.js";

export class FileMissing extends StaticSightError {
  constructor(message: string, hint?: string) {
    super(message, hint);
    this.title = "File not found";
  }
}

function realpathLoose(p: string): string {
  try {
    return realpathSync.native(p);
  } catch {
    // resolve the deepest existing parent so symlinked parents are still honoured
    const parent = resolve(p, "..");
    if (parent === p) return p;
    return join(realpathLoose(parent), basename(p));
  }
}

export function resolveInWorkspace(root: string, filePath: string, mustExist = true): [string, string] {
  if (!filePath || !String(filePath).trim()) {
    throw new InvalidArgument("`file_path` is empty.", "Pass a path relative to the workspace root, e.g. `src/router.cpp`.");
  }
  const raw = String(filePath).trim();
  const candidate = isAbsolute(raw) ? raw : join(root, raw);
  const real = realpathLoose(resolve(candidate));
  const rootReal = realpathLoose(root);
  const rel = relative(rootReal, real);
  if (rel.startsWith("..") || isAbsolute(rel) || (rel === "" && real !== rootReal)) {
    throw new InvalidArgument(`\`${raw}\` is outside the workspace (WORKSPACE_ROOT).`, "Only files inside WORKSPACE_ROOT can be inspected.");
  }
  const relPosix = rel.split(sep).join("/") || ".";
  let isFile = false;
  try {
    isFile = statSync(real).isFile();
  } catch {
    isFile = false;
  }
  if (mustExist && !isFile) {
    throw new FileMissing(
      `\`${relPosix}\` does not exist (it may have been deleted or renamed).`,
      "Check the path with get_diff_scopes, or pass a path relative to the workspace root.",
    );
  }
  return [real, relPosix];
}

/**
 * Decode source bytes: honours UTF-8/UTF-16 BOMs (common in MSVC repos), else UTF-8 with replacement.
 * The BOM is removed so that line-1 patterns such as `#include` still match.
 */
export function decodeSource(data: Uint8Array): string {
  if (data.length >= 3 && data[0] === 0xef && data[1] === 0xbb && data[2] === 0xbf) return new TextDecoder("utf-8").decode(data.subarray(3));
  if (data.length >= 2 && data[0] === 0xff && data[1] === 0xfe) return new TextDecoder("utf-16le").decode(data.subarray(2));
  if (data.length >= 2 && data[0] === 0xfe && data[1] === 0xff) {
    const even = (data.length - 2) & ~1;
    const swapped = Buffer.from(data.subarray(2, 2 + even));
    swapped.swap16();
    return new TextDecoder("utf-16le").decode(swapped) + (data.length - 2 > even ? "\uFFFD" : "");
  }
  return new TextDecoder("utf-8").decode(data);
}

export function readLines(path: string): string[] {
  let data: Buffer;
  try {
    data = readFileSync(path);
  } catch (e) {
    const err = e as NodeJS.ErrnoException;
    if (err.code === "EISDIR") throw new InvalidArgument(`\`${basename(path)}\` is a directory, not a file.`);
    throw new FileMissing(`\`${basename(path)}\` no longer exists.`);
  }
  return splitLines(decodeSource(data));
}

/** Lines without terminators (CRLF-safe); a trailing newline does not produce an empty last line. */
export function splitLines(text: string): string[] {
  const lines = text.split("\n");
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  return lines.map((ln) => (ln.endsWith("\r") ? ln.slice(0, -1) : ln));
}

/** fnmatch semantics ('*' also matches '/'); case-insensitive on case-insensitive platforms. */
export function matchesGlob(relPath: string, pattern: string): boolean {
  if (!pattern) return true;
  const plat = currentPlatform();
  const pat = pattern.replace(/\\/g, "/");
  const base = relPath.split("/").pop() ?? relPath;
  return plat.fnmatch(relPath, pat) || plat.fnmatch(relPath, pat.replace(/\/+$/, "") + "/*") || plat.fnmatch(base, pat);
}
