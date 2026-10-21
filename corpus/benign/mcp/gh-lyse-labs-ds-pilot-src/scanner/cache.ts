import { statSync } from "fs";
import { resolve } from "path";
import { globSync } from "glob";
import { scanComponents, type ComponentInfo } from "./components.js";
import { parseTokens, type Token } from "./tokens.js";

export interface ScannerCache {
  getComponents(): ComponentInfo[];
  getTokens(): Token[];
}

interface Fingerprint {
  fileCount: number;
  maxMtime: number;
  dirMtime: number;
  tokensMtime: number;
}

const COMPONENT_GLOB = "**/*.{tsx,ts,jsx,js,vue}";

export function createScannerCache(componentsDir: string, tokensFile?: string): ScannerCache {
  const absDir = resolve(componentsDir);
  const absTokens = tokensFile ? resolve(tokensFile) : undefined;

  let components: ComponentInfo[] = [];
  let tokens: Token[] = [];
  let lastFingerprint: Fingerprint | null = null;

  function currentFingerprint(): Fingerprint {
    let maxMtime = 0;
    let fileCount = 0;
    const files = globSync(COMPONENT_GLOB, { cwd: absDir, absolute: true });
    for (const f of files) {
      try {
        const mtime = statSync(f).mtimeMs;
        if (mtime > maxMtime) maxMtime = mtime;
        fileCount++;
      } catch {}
    }

    let dirMtime = 0;
    try {
      dirMtime = statSync(absDir).mtimeMs;
    } catch {}

    let tokensMtime = 0;
    if (absTokens) {
      try {
        tokensMtime = statSync(absTokens).mtimeMs;
      } catch {}
    }

    return { fileCount, maxMtime, dirMtime, tokensMtime };
  }

  function sameAsLast(current: Fingerprint): boolean {
    if (!lastFingerprint) return false;
    return (
      current.fileCount === lastFingerprint.fileCount &&
      current.maxMtime === lastFingerprint.maxMtime &&
      current.dirMtime === lastFingerprint.dirMtime &&
      current.tokensMtime === lastFingerprint.tokensMtime
    );
  }

  function refreshIfStale(): void {
    const current = currentFingerprint();
    if (sameAsLast(current)) return;
    components = scanComponents(absDir);
    tokens = absTokens ? parseTokens(absTokens) : [];
    lastFingerprint = current;
  }

  return {
    getComponents() {
      refreshIfStale();
      return components;
    },
    getTokens() {
      refreshIfStale();
      return tokens;
    },
  };
}
