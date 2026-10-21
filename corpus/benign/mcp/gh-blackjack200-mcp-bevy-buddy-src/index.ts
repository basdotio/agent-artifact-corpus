import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { readFileSync, readdirSync, statSync, Dirent } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { homedir } from "node:os";
import toml from "toml";
import { z } from "zod";

interface CargoToml {
  dependencies?: Record<string, string | { version?: string; path?: string }>;
}

interface ExampleNode {
  name: string;
  path: string;
  children?: ExampleNode[];
  isFile: boolean;
}

function getBevyVersion(): string | null {
  const cargoPath = join(process.cwd(), "Cargo.toml");
  const cargoToml: CargoToml = toml.parse(readFileSync(cargoPath, "utf-8"));
  const dep = cargoToml.dependencies?.bevy;

  if (typeof dep === "string") return dep.replace(/["^~]/g, "");
  if (typeof dep === "object" && dep.path) return dep.path;
  if (typeof dep === "object" && dep.version)
    return dep.version.replace(/["^~]/g, "");
  return null;
}

function findBevySourceDir(bevyVersion: string | null): string | null {
  if (!bevyVersion) return null;

  if (bevyVersion.startsWith(".")) {
    return join(process.cwd(), bevyVersion);
  }

  const cargoSrc = join(homedir(), ".cargo/registry/src");
  const registries: string[] = readdirSync(cargoSrc);
  for (const reg of registries) {
    const bevyDir = join(cargoSrc, reg, `bevy-${bevyVersion}`);
    try {
      if (statSync(bevyDir).isDirectory()) return bevyDir;
    } catch {}
  }
  return null;
}

function buildExampleTree(dir: string, baseDir = dir): ExampleNode[] {
  const entries: Dirent[] = readdirSync(dir, { withFileTypes: true });
  return entries
    .filter((e) => e.isDirectory() || e.name.endsWith(".rs"))
    .map((e) => {
      const absPath = join(dir, e.name);
      const relPath = absPath.replace(baseDir + "/", "");
      if (e.isDirectory()) {
        return {
          name: e.name,
          path: relPath,
          isFile: false,
          children: buildExampleTree(absPath, baseDir),
        };
      } else {
        return { name: e.name, path: relPath, isFile: true };
      }
    });
}

function formatTree(nodes: ExampleNode[], indent = 0): string {
  return nodes
    .map((n) => {
      const prefix = " ".repeat(indent * 2);
      if (n.isFile) {
        return `${prefix}- ${n.name}`;
      } else {
        return `${prefix}+ ${n.name}\n${formatTree(n.children ?? [], indent + 1)}`;
      }
    })
    .join("\n");
}

function readExampleFile(filePath: string, maxLines = 200): string {
  try {
    const content = readFileSync(filePath, "utf-8");
    return content.split("\n").slice(0, maxLines).join("\n");
  } catch (e: any) {
    return `Error reading file: ${e.message}`;
  }
}

const package_json = JSON.parse(
  readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "../package.json"),
    "utf-8",
  ),
);
const { name, version } = package_json;

const SYSTEM_PROMPT = `
  You are a **Rust assistant specialized in the Bevy game engine**.
  Your knowledge source is **only the local Bevy examples** accessible via the \`bevy-examples\` tool.
  Follow these strict rules:

  1. **Source restriction**
     You must **only** use and infer from the local Bevy examples.
     Do **not** rely on any built-in or general Bevy knowledge from training data.

  2. **Authoritative source**
     Treat the local Bevy examples as the **sole authoritative reference** for Bevy API usage, structure, and coding patterns.

  3. **Missing info rule**
     If something is **not found** in the local Bevy examples, reply exactly with:

     > "Not found in local Bevy examples"

  4. **Token efficiency (strict)**

     * Whenever you need to inspect an example, you **must first** call \`bevy-example-absolute-path\` to obtain its absolute path.
     * Then read **only the necessary sections** of that file.
     * You may **not** use \`bevy-example-file\` unless \`bevy-example-absolute-path\` fails or the file path is unavailable.
     * This is a hard rule, not a preference.
`;

const server = new McpServer({
  name,
  version,
  SYSTEM_PROMPT,
  capabilities: {
    resources: {
      subscribe: true,
      listChanged: true,
    },
  },
});

server.registerTool(
  "bevy-examples",
  {
    description: "Bevy example file tree",
  },
  () => {
    const ver = getBevyVersion();
    const srcDir = findBevySourceDir(ver);
    if (!srcDir) {
      return {
        content: [
          {
            type: "text",
            text: `Bevy version: ${ver ?? "unknown"}\nNo examples found.`,
          },
        ],
      };
    }
    const examplesDir = join(srcDir, "examples");
    const tree = buildExampleTree(examplesDir);
    const formatted = formatTree(tree);

    return {
      content: [
        {
          type: "text",
          text: `Bevy version: ${ver ?? "unknown"}\nExamples:\n${formatted}`,
        },
      ],
    };
  },
);

server.registerTool(
  "bevy-example-read",
  {
    description: "Read a specific Bevy example file",
    inputSchema: { path: z.string().nonempty().describe("path") },
  },
  ({ path }) => {
    const ver = getBevyVersion();
    const srcDir = findBevySourceDir(ver);
    if (!srcDir) {
      return {
        content: [
          {
            type: "text",
            text: `Error: Could not locate Bevy source for version ${ver ?? "unknown"}`,
          },
        ],
      };
    }

    const examplesDir = join(srcDir, "examples");
    const absPath = join(examplesDir, path);

    return {
      content: [
        {
          type: "text",
          text: `\`\`\`rust\n${readExampleFile(absPath)}\n\`\`\``,
        },
      ],
    };
  },
);
server.registerTool(
  "bevy-example-absolute-path",
  {
    description: "Get a specific Bevy example file absolute path",
    inputSchema: { path: z.string().nonempty().describe("path") },
  },
  ({ path }) => {
    const ver = getBevyVersion();
    const srcDir = findBevySourceDir(ver);
    if (!srcDir) {
      return {
        content: [
          {
            type: "text",
            text: `Error: Could not locate Bevy source for version ${ver ?? "unknown"}`,
          },
        ],
      };
    }

    const examplesDir = join(srcDir, "examples");
    const absPath = join(examplesDir, path);

    return {
      content: [
        {
          type: "text",
          text: absPath,
        },
      ],
    };
  },
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Weather MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
