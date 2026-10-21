import { chmod, mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export async function readJson<T>(path: string): Promise<T | null> {
  try {
    return JSON.parse(await readFile(path, "utf8")) as T;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw error;
  }
}

export async function writePrivateJson(path: string, value: unknown): Promise<void> {
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  try {
    await rename(temporary, path);
  } catch (error) {
    if (!["EEXIST", "EPERM"].includes((error as NodeJS.ErrnoException).code ?? "")) throw error;
    await rm(path, { force: true });
    await rename(temporary, path);
  }
  if (process.platform !== "win32") await chmod(path, 0o600);
}

export async function writePrivateText(path: string, value: string): Promise<void> {
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  await writeFile(path, value, { mode: 0o600 });
  if (process.platform !== "win32") await chmod(path, 0o600);
}
