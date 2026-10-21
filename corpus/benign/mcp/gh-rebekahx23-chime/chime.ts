/**
 * MIT
 * Minimal v0: one tool chimee with OS-native sound or bell fallback.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { spawn } from "node:child_process";
import process from "node:process";
import which from "which";

const isMac = process.platform === "darwin";
const isWin = process.platform === "win32";

function bellFallback() {
  try {
    // ASCII bell
    process.stdout.write("\x07");
  } catch {
    // ignore
  }
}

async function hasBin(bin: string): Promise<boolean> {
  try {
    await which(bin);
    return true;
  } catch {
    return false;
  }
}

/**
 * Plays a short chime and ALWAYS resolves to a non-empty status string.
 * Never throws; never blocks on playback.
 */
export async function dingOnce(): Promise<string> {
  if (process.env.GEMINI_CHIME_MUTE === "1") {
    return "muted";
  }

  // macOS
  if (isMac && (await hasBin("afplay"))) {
    const child = spawn("afplay", ["/System/Library/Sounds/Glass.aiff"], {
      stdio: "ignore",
      detached: true
    });
    child.unref();
    return "afplay";
  }

  // Windows
  if (isWin) {
    const child = spawn("PowerShell", ["-Command", "[console]::Beep(1000,300)"], {
      stdio: "ignore",
      detached: true
    });
    child.unref();
    return "powershell-beep";
  }

  // Linux / other
  if (await hasBin("paplay")) {
    const child = spawn("paplay", ["/usr/share/sounds/freedesktop/stereo/complete.oga"], {
      stdio: "ignore",
      detached: true
    });
    // if paplay errors, still fine—we already return a status
    child.on("error", bellFallback);
    child.unref();
    return "paplay";
  }

  if (await hasBin("aplay")) {
    const child = spawn("aplay", ["/usr/share/sounds/alsa/Front_Center.wav"], {
      stdio: "ignore",
      detached: true
    });
    child.on("error", bellFallback);
    child.unref();
    return "aplay";
  }

  // Fallback bell
  bellFallback();
  return "terminal-bell";
}

const server = new McpServer({ name: 'chime', version: '0.1.8' });

server.registerTool(
  'chime',
  {
    description: 'Play a simple completion chime. You should output a period after calling this.',
    inputSchema: z.object({}).shape, // ← no inputs
  },
  async () => {
    await dingOnce();
    return { content: [{ type: 'text', text: '"✨ chime"' }] };
  }
);

// Start stdio transport
server.connect(new StdioServerTransport());

// Optional: log unhandled errors to stderr (so host can surface them)
process.on("uncaughtException", (err) => {
  console.error("[mcp] uncaughtException:", err);
});
process.on("unhandledRejection", (reason) => {
  console.error("[mcp] unhandledRejection:", reason);
});
