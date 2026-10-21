// OS selection. current() is chosen once from the OS identity; tests may override it with use().
import { Platform } from "./base.js";
import { PosixPlatform } from "./posix.js";
import { WindowsPlatform } from "./windows.js";

export type { CmdResult, RunOptions } from "./base.js";
export { Platform, PosixPlatform, WindowsPlatform };

let active: Platform | null = null;

export function detect(): Platform {
  return process.platform === "win32" ? new WindowsPlatform() : new PosixPlatform();
}

export function current(): Platform {
  if (active === null) active = detect();
  return active;
}

/** Override the active platform (tests); null restores auto-detection. */
export function use(p: Platform | null): void {
  active = p;
}
