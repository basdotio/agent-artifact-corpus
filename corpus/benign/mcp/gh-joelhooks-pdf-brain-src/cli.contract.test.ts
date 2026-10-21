import { describe, expect, test } from "bun:test";
import { mkdtempSync, rmSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { Client } from "@modelcontextprotocol/sdk/client";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

function runCli(
  argv: string[],
  opts?: { env?: Record<string, string | undefined> },
): { exitCode: number; stdout: string; stderr: string } {
  const env: Record<string, string> = {
    ...process.env,
    ...(opts?.env ?? {}),
  } as any;

  const proc = Bun.spawnSync([process.execPath, "run", "src/cli.ts", ...argv], {
    env,
    stdout: "pipe",
    stderr: "pipe",
  });

  return {
    exitCode: proc.exitCode ?? 0,
    stdout: new TextDecoder().decode(proc.stdout),
    stderr: new TextDecoder().decode(proc.stderr),
  };
}

function withTempLibraryPath<T>(fn: (libraryPath: string) => T): T {
  const dir = mkdtempSync(join(tmpdir(), "pdf-brain-cli-contract-"));
  try {
    return fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

async function withTempLibraryPathAsync<T>(
  fn: (libraryPath: string) => Promise<T>,
): Promise<T> {
  const dir = mkdtempSync(join(tmpdir(), "pdf-brain-cli-contract-"));
  try {
    return await fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

describe("CLI JSON Envelope Contract", () => {
  test("stats emits a single JSON envelope with nextActions when not --quiet", () =>
    withTempLibraryPath((libraryPath) => {
      const res = runCli(["stats", "--format", "json"], {
        env: {
          PDF_LIBRARY_PATH: libraryPath,
          // Avoid touching any real local Ollama instance during tests.
          OLLAMA_HOST: "http://127.0.0.1:1",
        },
      });

      expect(res.exitCode).toBe(0);
      expect(res.stdout.trim().startsWith("{")).toBe(true);

      const obj = JSON.parse(res.stdout);
      expect(obj.ok).toBe(true);
      expect(obj.command).toBe("stats");
      expect(obj.protocolVersion).toBe(1);
      expect(obj.result).toBeDefined();
      expect(obj.result.libraryPath).toBe(libraryPath);
      expect(obj.result.documents).toBe(0);
      expect(obj.result.chunks).toBe(0);
      expect(obj.result.embeddings).toBe(0);

      // Agent mode: nextActions should exist by default (unless --quiet)
      expect(Array.isArray(obj.nextActions)).toBe(true);
      expect(obj.nextActions.length).toBeGreaterThan(0);
    }));

  test("stats with --quiet omits nextActions", () =>
    withTempLibraryPath((libraryPath) => {
      const res = runCli(["stats", "--format", "json", "--quiet"], {
        env: {
          PDF_LIBRARY_PATH: libraryPath,
          OLLAMA_HOST: "http://127.0.0.1:1",
        },
      });

      expect(res.exitCode).toBe(0);
      const obj = JSON.parse(res.stdout);
      expect(obj.ok).toBe(true);
      expect(obj.command).toBe("stats");
      expect("nextActions" in obj).toBe(false);
    }));

  test("invalid --format returns a structured error envelope and non-zero exit code", () =>
    withTempLibraryPath((libraryPath) => {
      const res = runCli(["--format", "wat", "stats"], {
        env: {
          PDF_LIBRARY_PATH: libraryPath,
          OLLAMA_HOST: "http://127.0.0.1:1",
        },
      });

      expect(res.exitCode).not.toBe(0);
      const obj = JSON.parse(res.stdout);
      expect(obj.ok).toBe(false);
      expect(obj.protocolVersion).toBe(1);
      expect(obj.error).toBeDefined();
      expect(obj.error.code).toBe("INVALID_FLAG");
    }));

  test("rechunk flag validation: --max-docs requires a numeric value", () =>
    withTempLibraryPath((libraryPath) => {
      const res = runCli(["rechunk", "--max-docs", "--format", "json"], {
        env: {
          PDF_LIBRARY_PATH: libraryPath,
          OLLAMA_HOST: "http://127.0.0.1:1",
        },
      });

      expect(res.exitCode).not.toBe(0);
      const obj = JSON.parse(res.stdout);
      expect(obj.ok).toBe(false);
      expect(obj.error.code).toBe("INVALID_ARGS");
      expect(String(obj.error.message)).toContain("--max-docs");
    }));

  test("capabilities is self-describing and includes JSON Schemas", () =>
    withTempLibraryPath((libraryPath) => {
      const res = runCli(["capabilities", "--format", "json", "--quiet"], {
        env: {
          PDF_LIBRARY_PATH: libraryPath,
          OLLAMA_HOST: "http://127.0.0.1:1",
        },
      });

      expect(res.exitCode).toBe(0);
      const obj = JSON.parse(res.stdout);
      expect(obj.ok).toBe(true);
      expect(obj.command).toBe("capabilities");
      expect(obj.protocolVersion).toBe(1);

      const result = obj.result;
      expect(result).toBeDefined();
      expect(result.protocolVersion).toBe(1);
      expect(typeof result.pdfBrainVersion).toBe("string");

      // Command list invariants (agent discovery depends on these names)
      const commandNames = new Set(
        (result.commands as Array<any>).map((c) => String(c.name)),
      );
      expect(commandNames.has("search")).toBe(true);
      expect(commandNames.has("search-pack")).toBe(true);
      expect(commandNames.has("chunk")).toBe(true);
      expect(commandNames.has("doc")).toBe(true);
      expect(commandNames.has("page")).toBe(true);
      expect(commandNames.has("stats")).toBe(true);
      expect(commandNames.has("rechunk")).toBe(true);
      expect(commandNames.has("reindex")).toBe(true);
      expect(commandNames.has("mcp")).toBe(true);
      expect(commandNames.has("serve")).toBe(true);

      // Schema invariants (agents can validate/parses these)
      expect(result.schemas).toBeDefined();
      expect(result.schemas.Document).toBeDefined();
      expect(result.schemas.PDFChunk).toBeDefined();
      expect(result.schemas.SearchResult).toBeDefined();
      expect(result.schemas.Config).toBeDefined();

      // Lightweight stability assertions: required field names shouldn't drift.
      const docSchema = result.schemas.Document as any;
      expect(docSchema.type).toBe("object");
      expect(Array.isArray(docSchema.required)).toBe(true);
      expect(docSchema.required).toContain("id");
      expect(docSchema.required).toContain("title");
      expect(docSchema.required).toContain("path");
      expect(docSchema.required).toContain("tags");
    }));

  test("config show text output includes database backend details", () =>
    withTempLibraryPath((libraryPath) => {
      const configPath = join(libraryPath, "config.json");
      const res = runCli(["config", "show", "--format", "text"], {
        env: {
          PDF_LIBRARY_PATH: libraryPath,
          PDF_BRAIN_CONFIG: configPath,
          OLLAMA_HOST: "http://127.0.0.1:1",
        },
      });

      expect(res.exitCode).toBe(0);
      expect(res.stdout).toContain("Database:");
      expect(res.stdout).toContain("libsql");
      expect(res.stdout).toContain("Qdrant:");
    }));
});

describe("MCP Tool Output Contract", () => {
  test(
    "mcp tools return structuredContent matching the agent envelope schema",
    async () =>
      withTempLibraryPathAsync(async (libraryPath) => {
        const transport = new StdioClientTransport({
          command: process.execPath,
          args: ["run", "src/cli.ts", "mcp", "--quiet"],
          cwd: process.cwd(),
          stderr: "pipe",
          env: {
            ...process.env,
            PDF_LIBRARY_PATH: libraryPath,
            // Avoid hitting any real local Ollama instance during tests.
            OLLAMA_HOST: "http://127.0.0.1:1",
            // Keep noise down if something logs unexpectedly.
            PDF_BRAIN_LOG_LEVEL: "silent",
          } as any,
        });

        const client = new Client({
          name: "pdf-brain-contract-test",
          version: "0.0.0",
        });

        try {
          await client.connect(transport);

          const tools = await client.listTools();
          const toolNames = new Set(tools.tools.map((t) => t.name));
          expect(toolNames.has("capabilities")).toBe(true);
          expect(toolNames.has("stats")).toBe(true);
          expect(toolNames.has("search")).toBe(true);

          const call = await client.callTool({ name: "stats", arguments: {} });
          expect(Boolean(call.isError)).toBe(false);
          expect(call.structuredContent).toBeDefined();

          const envelope: any = call.structuredContent;
          expect(envelope.ok).toBe(true);
          expect(envelope.command).toBe("stats");
          expect(envelope.protocolVersion).toBe(1);
          expect(envelope.result).toBeDefined();
          expect(envelope.result.libraryPath).toBe(libraryPath);
        } finally {
          try {
            await client.close();
          } catch {
            // ignore
          }
          try {
            await transport.close();
          } catch {
            // ignore
          }
        }
      }),
    { timeout: 20000 },
  );
});
