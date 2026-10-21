import { execFile, spawn } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync, openSync, closeSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import { randomBytes } from "node:crypto";
import { setTimeout as delay } from "node:timers/promises";
import { configDirectory } from "./settings.js";
import { readHealth } from "./diagnostics.js";
import { executable } from "./agents.js";

const execute = promisify(execFile);
const cli = fileURLToPath(new URL("./cli.js", import.meta.url));
export const psQuote = (value: string) => `'${value.replaceAll("'", "''")}'`;

/** Paths and flags only. Credentials are never placed in a command line or startup shortcut. */
export function windowScript(args: string[], cwd = process.cwd(), directory = configDirectory(), node = process.execPath, entry = cli): string {
  return `$host.UI.RawUI.WindowTitle = 'jev-classifier gateway'; $env:JEV_CONFIG_HOME = ${psQuote(directory)}; Set-Location -LiteralPath ${psQuote(cwd)}; & ${psQuote(node)} ${[entry, ...args].map(psQuote).join(" ")}; if ($LASTEXITCODE -ne 0) { Read-Host 'Gateway exited with an error. Press Enter to close' }`;
}
export function encodedScript(script: string): string { return Buffer.from(script, "utf16le").toString("base64"); }
export const shQuote = (value: string) => `'${value.replaceAll("'", "'\"'\"'")}'`;

async function detached(file: string, args: string[], env = process.env, stdio: "ignore" | ["ignore", number, number] = "ignore"): Promise<void> {
  const child = spawn(file, args, { detached: true, stdio, env });
  await new Promise<void>((resolve, reject) => { child.once("spawn", resolve); child.once("error", reject); });
  child.unref();
}

/** A log viewer can close independently; the managed gateway stays available. */
export async function openLogWindow(): Promise<void> {
  const args = [cli, "logs", "--follow", "--global"];
  if (process.platform === "darwin" && !process.env.SSH_CONNECTION) {
    const command = `JEV_CONFIG_HOME=${shQuote(configDirectory())} ${[process.execPath, ...args].map(shQuote).join(" ")}`;
    // JSON string escaping is also valid for these AppleScript string literals.
    await execute("osascript", ["-e", `tell application "Terminal" to do script ${JSON.stringify(command)}`, "-e", 'tell application "Terminal" to activate'], { timeout: 5000 });
  } else if (process.platform === "linux" && (process.env.DISPLAY || process.env.WAYLAND_DISPLAY)) {
    for (const [terminal, prefix] of [["x-terminal-emulator", "-e"], ["gnome-terminal", "--"], ["konsole", "-e"], ["xterm", "-e"]]) {
      const file = executable(terminal!);
      if (file) { await detached(file, [prefix!, process.execPath, ...args], { ...process.env, JEV_CONFIG_HOME: configDirectory() }); return; }
    }
  }
}

export async function startGateway(port: number, args: string[]): Promise<{ reused: boolean; pid: number }> {
  try { const health = await readHealth(port); return { reused: true, pid: health.pid }; } catch { /* bind will report occupied ports */ }
  if (process.platform === "win32") {
    const script = windowScript(["serve", "--foreground", ...args]);
    await execute("powershell.exe", ["-NoProfile", "-EncodedCommand", encodedScript(
      `Start-Process -FilePath (Join-Path $PSHOME 'powershell.exe') -WindowStyle Normal -ArgumentList @('-NoLogo','-NoProfile','-EncodedCommand','${encodedScript(script)}')`,
    )], { windowsHide: true });
  } else {
    mkdirSync(configDirectory(), { recursive: true, mode: 0o700 });
    const output = openSync(join(configDirectory(), "gateway-console.log"), "a", 0o600);
    try { await detached(process.execPath, [cli, "serve", "--foreground", ...args], process.env, ["ignore", output, output]); }
    finally { closeSync(output); }
  }
  for (let i = 0; i < 30; i++) {
    try {
      const health = await readHealth(port);
      if (process.platform !== "win32") await openLogWindow().catch(() => {});
      return { reused: false, pid: health.pid };
    } catch { await delay(250); }
  }
  throw new Error(`Gateway did not become ready on port ${port}. Check its window or run logs; another application may be using this port.`);
}

interface Runtime { pid: number; token: string; instanceId: string; port: number }
const runtimeFile = (port: number) => join(configDirectory(), `gateway-${port}.json`);
export function newRuntime(port: number): Runtime {
  return { pid: process.pid, port, instanceId: randomBytes(16).toString("hex"), token: randomBytes(32).toString("hex") };
}
export function saveRuntime(runtime: Runtime): void {
  mkdirSync(configDirectory(), { recursive: true, mode: 0o700 });
  writeFileSync(runtimeFile(runtime.port), JSON.stringify(runtime), { mode: 0o600 });
}
export function removeRuntime(runtime: Runtime): void {
  try {
    const current = JSON.parse(readFileSync(runtimeFile(runtime.port), "utf8")) as Runtime;
    if (current.instanceId === runtime.instanceId) rmSync(runtimeFile(runtime.port));
  } catch { /* already removed */ }
}
export async function stopGateway(port: number): Promise<void> {
  const health = await readHealth(port);
  let runtime: Runtime;
  try { runtime = JSON.parse(readFileSync(runtimeFile(port), "utf8")); }
  catch { throw new Error("This gateway is not managed by this configuration. Close it in its own terminal."); }
  if (runtime.instanceId !== health.instanceId || runtime.pid !== health.pid) throw new Error("Gateway ownership changed. Close it in its own terminal.");
  const result = await fetch(`http://127.0.0.1:${port}/__jev/stop`, { method: "POST", headers: { authorization: `Bearer ${runtime.token}` }, signal: AbortSignal.timeout(3000), redirect: "error" });
  if (!result.ok) throw new Error("The gateway refused the stop request.");
  await result.text();
}

export function startupPath(platform: NodeJS.Platform = process.platform, env = process.env, home = homedir()): string {
  if (platform === "darwin") return join(home, "Library", "LaunchAgents", "ai.jev.classifier.plist");
  if (platform === "linux") return join(env.XDG_CONFIG_HOME || join(home, ".config"), "autostart", "jev-classifier.desktop");
  if (platform !== "win32") throw new Error("Automatic startup supports Windows, macOS and Linux desktop sessions.");
  if (!env.APPDATA) throw new Error("Windows APPDATA is unavailable.");
  return join(env.APPDATA, "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "jev-classifier.lnk");
}
export function startupStatus(): boolean { return ["win32", "darwin", "linux"].includes(process.platform) && existsSync(startupPath()); }

const xml = (value: string) => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
// Desktop Exec has its own escaping, applied before the desktop file's string unescaping.
const desktopArgument = (value: string) => '"' + value.replaceAll("%", "%%").replace(/[\\"`$]/g, c => "\\" + c).replaceAll("\\", "\\\\").replaceAll("\n", "\\n").replaceAll("\r", "\\r") + '"';
export function startupContents(platform: "darwin" | "linux", directory = configDirectory(), node = process.execPath, entry = cli): string {
  // launchd owns a foreground process for the full lifetime of a login session.
  const args = [node, entry, "serve", ...(platform === "darwin" ? ["--foreground"] : []), "--global", "--startup-launch"];
  if (platform === "darwin") return `<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>\n<key>Label</key><string>ai.jev.classifier</string>\n<key>ProgramArguments</key><array>${args.map(a => `<string>${xml(a)}</string>`).join("")}</array>\n<key>WorkingDirectory</key><string>${xml(directory)}</string>\n<key>EnvironmentVariables</key><dict><key>JEV_CONFIG_HOME</key><string>${xml(directory)}</string></dict>\n<key>RunAtLoad</key><true/>\n<key>StandardErrorPath</key><string>${xml(join(directory, "startup.log"))}</string>\n</dict></plist>\n`;
  return `[Desktop Entry]\nType=Application\nName=jev-classifier\nComment=Start the local Jev gateway at desktop sign-in\nExec=${["/usr/bin/env", `JEV_CONFIG_HOME=${directory}`, ...args].map(desktopArgument).join(" ")}\nTerminal=false\nX-GNOME-Autostart-enabled=true\n`;
}
export async function setStartup(enabled: boolean): Promise<void> {
  const file = startupPath();
  if (!enabled) { rmSync(file, { force: true }); return; }
  // A per-user shortcut needs no administrator privileges and reads saved preferences at login.
  const directory = configDirectory();
  mkdirSync(directory, { recursive: true });
  mkdirSync(dirname(file), { recursive: true });
  if (process.platform === "darwin" || process.platform === "linux") {
    // Registration takes effect on the next graphical sign-in; do not launch or stop a live session here.
    writeFileSync(file, startupContents(process.platform), { mode: 0o600 });
    return;
  }
  const script = windowScript(["serve", "--foreground", "--global", "--startup-launch"], directory, directory);
  const target = resolve(process.env.SystemRoot || "C:/Windows", "System32/WindowsPowerShell/v1.0/powershell.exe");
  await execute("powershell.exe", ["-NoProfile", "-EncodedCommand", encodedScript(
    `$ErrorActionPreference = 'Stop'; $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut(${psQuote(file)}); $shortcut.TargetPath = ${psQuote(target)}; $shortcut.Arguments = ${psQuote(`-NoLogo -NoProfile -EncodedCommand ${encodedScript(script)}`)}; $shortcut.WorkingDirectory = ${psQuote(directory)}; $shortcut.Description = 'jev-classifier gateway'; $shortcut.WindowStyle = 1; $shortcut.Save()`,
  )], { windowsHide: true });
}
