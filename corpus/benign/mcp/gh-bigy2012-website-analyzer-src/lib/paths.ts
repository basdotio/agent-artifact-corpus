import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

/** Project root (…/website-analyzer-mcp), whether running from src/ or dist/ */
export const PACKAGE_ROOT = path.resolve(here, '../..');

export function defaultOutputDir(): string {
  if (process.env.WEBSITE_ANALYZER_OUTPUT) {
    return path.resolve(process.env.WEBSITE_ANALYZER_OUTPUT);
  }
  return path.join(PACKAGE_ROOT, 'output');
}

export function resolveOutputDir(outputDir?: string): string {
  if (!outputDir) return defaultOutputDir();
  return path.isAbsolute(outputDir) ? outputDir : path.resolve(PACKAGE_ROOT, outputDir);
}
