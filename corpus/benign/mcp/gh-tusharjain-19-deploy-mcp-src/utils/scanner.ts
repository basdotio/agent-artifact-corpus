import fs from "fs";
import path from "path";

export interface LargeFile {
  path: string;
  sizeBytes: number;
  sizeFormatted: string;
}

const IGNORED_DIRS = ["node_modules", ".git", ".next", "dist", "build"];
const VERCEL_MAX_SIZE_BYTES = 50 * 1024 * 1024; // 50MB

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export async function scanForLargeFiles(
  dir: string,
  thresholdBytes: number = VERCEL_MAX_SIZE_BYTES
): Promise<LargeFile[]> {
  const largeFiles: LargeFile[] = [];

  async function scan(currentDir: string) {
    try {
      const entries = await fs.promises.readdir(currentDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name);
        
        if (entry.isDirectory()) {
          if (!IGNORED_DIRS.includes(entry.name)) {
            await scan(fullPath);
          }
        } else if (entry.isFile()) {
          try {
            const stats = await fs.promises.stat(fullPath);
            if (stats.size > thresholdBytes) {
              largeFiles.push({
                path: fullPath,
                sizeBytes: stats.size,
                sizeFormatted: formatBytes(stats.size)
              });
            }
          } catch {
            // Ignore stat errors for individual files (e.g. symlinks)
          }
        }
      }
    } catch (error) {
      // Ignore directory read errors
    }
  }

  await scan(dir);
  
  // Sort by size descending
  return largeFiles.sort((a, b) => b.sizeBytes - a.sizeBytes);
}
