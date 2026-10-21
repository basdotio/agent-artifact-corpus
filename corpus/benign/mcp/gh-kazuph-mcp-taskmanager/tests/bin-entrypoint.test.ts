import { spawn } from "node:child_process";
import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

// npm installs bin entries as symlinks (node_modules/.bin, the npx cache).
// v1.1.0 shipped an entrypoint guard that compared path.resolve(argv[1])
// against the real module path, so the server silently never started when
// launched through a symlink. This test reproduces that exact launch shape.

const distEntry = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../dist/index.js"
);

let tmpDir: string;
let symlinkPath: string;

function runServerOnce(
  entry: string,
  taskFile: string
): Promise<{ stdoutLines: string[]; stderr: string }> {
  return new Promise((resolve, reject) => {
    const p = spawn("node", [entry], {
      env: { ...process.env, TASK_MANAGER_FILE_PATH: taskFile },
    });
    let out = "";
    let err = "";
    p.stdout.on("data", (d) => {
      out += d.toString();
    });
    p.stderr.on("data", (d) => {
      err += d.toString();
    });
    p.on("error", reject);
    p.stdin.write(
      `${JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2024-11-05",
          capabilities: {},
          clientInfo: { name: "bin-test", version: "1.0" },
        },
      })}\n`
    );
    setTimeout(() => {
      p.stdin.write(
        `${JSON.stringify({
          jsonrpc: "2.0",
          id: 2,
          method: "tools/list",
          params: {},
        })}\n`
      );
    }, 300);
    setTimeout(() => {
      p.kill();
      resolve({ stdoutLines: out.trim().split("\n").filter(Boolean), stderr: err });
    }, 900);
  });
}

describe("bin entrypoint", () => {
  beforeAll(async () => {
    tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "mcp-tm-bin-"));
    symlinkPath = path.join(tmpDir, "mcp-taskmanager");
    await fs.symlink(distEntry, symlinkPath);
  });

  afterAll(async () => {
    await fs.rm(tmpDir, { recursive: true, force: true });
  });

  it("starts the server when launched through a symlink (npx-style)", async () => {
    const { stdoutLines, stderr } = await runServerOnce(
      symlinkPath,
      path.join(tmpDir, "via-symlink", "tasks.json")
    );
    expect(stderr).toContain("Task Manager MCP Server running");
    const tools = stdoutLines
      .map((l) => {
        try {
          return JSON.parse(l);
        } catch {
          return null;
        }
      })
      .find((m) => m && m.id === 2);
    expect(tools?.result?.tools?.length).toBe(10);
  });

  it("starts the server when launched via the direct path", async () => {
    const { stderr } = await runServerOnce(
      distEntry,
      path.join(tmpDir, "direct", "tasks.json")
    );
    expect(stderr).toContain("Task Manager MCP Server running");
  });
});
