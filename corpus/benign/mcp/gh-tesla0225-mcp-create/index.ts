import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { fileURLToPath } from "url";
import { dirname } from "path";
import {
  CallToolRequest,
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import { spawn, ChildProcess } from "child_process";
import * as fs from "fs/promises";
import * as path from "path";
import { v4 as uuidv4 } from "uuid";
import * as os from "os";

// Type definitions for tool arguments
interface CreateServerArgs {
  code: string;
  language: "typescript" | "javascript" | "python";
}

interface CreateServerFromTemplateArgs {
  language: "typescript" | "python";
  code?: string;
  dependencies?: Record<string, string>; // 例: { "axios": "^1.0.0" }
}

interface ExecuteToolArgs {
  serverId: string;
  toolName: string;
  args: Record<string, any>;
}

interface GetServerToolsArgs {
  serverId: string;
}

interface UpdateServerArgs {
  serverId: string;
  code: string;
}

interface DeleteServerArgs {
  serverId: string;
}

interface ConnectedServer {
  process: ChildProcess;
  client: Client;
  transport: StdioClientTransport;
  language: string;
  filePath: string;
}

// Get current file path and directory in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// コマンドの絶対パスを取得する関数を追加
async function getCommandPath(command: string): Promise<string> {
  try {
    // whichコマンドの代わりにJavaScriptで絶対パスを探す
    const possiblePaths = [
      "/usr/local/bin",
      "/usr/bin",
      "/bin",
      "/usr/local/sbin",
      "/usr/sbin",
      "/sbin",
    ];

    for (const dir of possiblePaths) {
      const fullPath = path.join(dir, command);
      try {
        await fs.access(fullPath, fs.constants.X_OK);
        console.error(`Found command ${command} at ${fullPath}`);
        return fullPath;
      } catch {
        // このパスにコマンドが存在しない場合は次を試す
      }
    }

    // コマンドが見つからない場合は元のコマンド名を返す
    console.error(
      `Command ${command} not found in standard paths, returning as is`
    );
    return command;
  } catch (error) {
    console.error(`Error resolving path for ${command}:`, error);
    return command;
  }
}

// Server manager class
class ServerManager {
  private servers: Map<string, ConnectedServer> = new Map();

  private templatesDir: string = path.join(__dirname, "templates");
  private serversDir: string = path.join(os.tmpdir(), "mcp-create-servers");

  constructor() {
    // Ensure servers directory exists
    this.initDirectories();
  }

  private async initDirectories() {
    try {
      await fs.mkdir(this.serversDir, { recursive: true });
      // 権限を明示的に設定（Docker内でも動作するように）
      await fs.chmod(this.serversDir, 0o777);
      console.error(`Created servers directory: ${this.serversDir}`);
    } catch (error) {
      console.error(`Error creating servers directory: ${error}`);
    }
  }

  // Create a new server from code
  async createServer(
    code: string, 
    language: string,
    dependencies?: Record<string, string>
  ): Promise<string> {
    const serverId = uuidv4();
    const serverDir = path.join(this.serversDir, serverId);

    try {
      // Create server directory
      await fs.mkdir(serverDir, { recursive: true });
      await fs.chmod(serverDir, 0o777); // 権限を追加

      // 依存関係がある場合はインストール（シンボリックリンクは作成しない）
      if (dependencies && Object.keys(dependencies).length > 0) {
        await this.installDependencies(serverDir, dependencies, language);
      } else {
        // 依存関係がない場合のみシンボリックリンクを作成
        try {
          await fs.symlink(
            "/app/node_modules",
            path.join(serverDir, "node_modules")
          );
          console.error(`Created symlink to node_modules in ${serverDir}`);
        } catch (error) {
          console.error(`Error creating symlink: ${error}`);
          // エラーがあっても続行する
        }
      }

      // Write server code to file
      let filePath: string;
      let command: string;
      let args: string[] = [];

      // 共通の環境変数設定
      const appNodeModules = path.resolve("/app/node_modules");
      const commonEnv = {
        ...process.env,
        PATH: process.env.PATH || "/usr/local/bin:/usr/bin:/bin",
        NODE_PATH: appNodeModules,
      };

      console.error(`Current PATH: ${process.env.PATH}`);
      console.error(`Current NODE_PATH: ${process.env.NODE_PATH}`);

      switch (language) {
        case "typescript":
          filePath = path.join(serverDir, "index.ts");
          const jsFilePath = path.join(serverDir, "index.js");
          const tsConfigPath = path.join(__dirname, "tsconfig.json");

          await fs.writeFile(filePath, code);

          // 絶対パスを取得して出力
          command = await getCommandPath("npx");
          console.error(`Using command path for npx: ${command}`);

          // TypeScriptをコンパイルする方法に変更
          await new Promise<void>((resolve, reject) => {
            const tscCommand = "npx";
            const tscArgs = [
              "tsc",
              "--allowJs",
              filePath,
              "--outDir",
              serverDir,
              "--target",
              "ES2020",
              "--module",
              "NodeNext",
              "--moduleResolution",
              "NodeNext",
              "--esModuleInterop",
              "--skipLibCheck",
              "--resolveJsonModule",
            ];


            console.error(
              `Compiling TypeScript: ${tscCommand} ${tscArgs.join(" ")}`
            );

            const compileProcess = spawn(tscCommand, tscArgs, {
              stdio: ["ignore", "pipe", "pipe"],
              shell: true,
              env: commonEnv,
              cwd: "/app", // アプリケーションのルートディレクトリを指定
            });

            compileProcess.stdout.on("data", (data) => {
              console.error(`TSC stdout: ${data}`);
            });

            compileProcess.stderr.on("data", (data) => {
              console.error(`TSC stderr: ${data}`);
            });

            compileProcess.on("exit", (code) => {
              if (code === 0) {
                console.error(`TypeScript compilation successful`);
                resolve();
              } else {
                console.error(
                  `TypeScript compilation failed with code ${code}`
                );
                reject(
                  new Error(`TypeScript compilation failed with code ${code}`)
                );
              }
            });
          });

          // コンパイルされたJavaScriptを実行
          command = await getCommandPath("node");
          args = [jsFilePath];
          break;

        case "javascript":
          filePath = path.join(serverDir, "index.js");
          await fs.writeFile(filePath, code);
          command = await getCommandPath("node");
          args = [filePath];
          break;

        case "python":
          filePath = path.join(serverDir, "server.py");
          await fs.writeFile(filePath, code);
          command = await getCommandPath("python");
          args = [filePath];
          break;

        default:
          throw new Error(`Unsupported language: ${language}`);
      }

      console.error(`Spawning process: ${command} ${args.join(" ")}`);

      // サーバープロセスを起動（パイプに変更）
      const childProcess = spawn(command, args, {
        stdio: ["pipe", "pipe", "pipe"], // inheritではなくpipeを使用
        shell: true,
        env: commonEnv,
        cwd: process.cwd(),
      });

      // 標準エラー出力のログ取得
      childProcess.stderr.on("data", (data) => {
        console.error(`Child process stderr: ${data}`);
      });

      // 標準出力のログ取得
      childProcess.stdout.on("data", (data) => {
        console.error(`Child process stdout: ${data}`);
      });

      // Create MCP client to communicate with the server
      const transport = new StdioClientTransport({
        command,
        args,
        env: commonEnv, // 同じ環境変数を使用
      });

      const client = new Client(
        {
          name: "mcp-create-client",
          version: "1.0.0",
        },
        {
          capabilities: {
            tools: {},
          },
        }
      );

      try {
        await client.connect(transport);
        console.error(`Connected to server ${serverId}`);
      } catch (error) {
        console.error(`Error connecting to server ${serverId}:`, error);
        childProcess.kill();
        throw error;
      }

      // Store server info
      this.servers.set(serverId, {
        process: childProcess,
        client,
        transport,
        language,
        filePath,
      });

      // Handle process exit
      childProcess.on("exit", (code) => {
        console.error(`Server ${serverId} exited with code ${code}`);
        this.servers.delete(serverId);
      });

      return serverId;
    } catch (error) {
      // Clean up on error
      console.error(`Error creating server:`, error);
      try {
        await fs.rm(serverDir, { recursive: true, force: true });
      } catch (cleanupError) {
        console.error(`Error cleaning up server directory: ${cleanupError}`);
      }

      throw error;
    }
  }

  // Create a server from template
//   async createServerFromTemplate(
//     language: string
//   ): Promise<{ serverId: string; message: string }> {
//     // Template code for different languages
//     let templateCode: string;

//     switch (language) {
//       case "typescript":
//         templateCode = `
// import { Server } from "@modelcontextprotocol/sdk/server/index.js";
// import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
// import { 
//   CallToolRequestSchema, 
//   ListToolsRequestSchema 
// } from "@modelcontextprotocol/sdk/types.js";

// const server = new Server({
//   name: "dynamic-test-server",
//   version: "1.0.0"
// }, {
//   capabilities: {
//     tools: {}
//   }
// });

// // Server implementation - 正しいスキーマ型を使用
// server.setRequestHandler(ListToolsRequestSchema, async () => {
//   return {
//     tools: [{
//       name: "echo",
//       description: "Echo back a message",
//       inputSchema: {
//         type: "object",
//         properties: {
//           message: { type: "string" }
//         },
//         required: ["message"]
//       }
//     }]
//   };
// });

// server.setRequestHandler(CallToolRequestSchema, async (request) => {
//   if (request.params.name === "echo") {
//     return {
//       content: [
//         {
//           type: "text",
//           text: \`Echo: \${request.params.arguments.message}\`
//         }
//       ]
//     };
//   }
//   throw new Error("Tool not found");
// });

// // Server startup
// const transport = new StdioServerTransport();
// server.connect(transport);
// `;
//         break;

//       case "python":
//         templateCode = `
// import asyncio
// from mcp.server import Server
// from mcp.server.stdio import stdio_server

// app = Server("dynamic-test-server")

// @app.list_tools()
// async def list_tools():
//     return [
//         {
//             "name": "echo",
//             "description": "Echo back a message",
//             "inputSchema": {
//                 "type": "object",
//                 "properties": {
//                     "message": {"type": "string"}
//                 },
//                 "required": ["message"]
//             }
//         }
//     ]

// @app.call_tool()
// async def call_tool(name, arguments):
//     if name == "echo":
//         return [{"type": "text", "text": f"Echo: {arguments.get('message')}"}]
//     raise ValueError(f"Tool not found: {name}")

// async def main():
//     async with stdio_server() as streams:
//         await app.run(
//             streams[0],
//             streams[1],
//             app.create_initialization_options()
//         )

// if __name__ == "__main__":
//     asyncio.run(main())
// `;
//         break;

//       default:
//         throw new Error(`Unsupported template language: ${language}`);
//     }

//     const serverId = await this.createServer(templateCode, language);
//     return {
//       serverId,
//       message: `Created server from ${language} template`,
//     };
//   }

  // 以下は他のメソッドも同様に修正することになりますが、
  // 主要な変更点は上記の通りです

  // 依存関係をインストールするメソッド
  async installDependencies(
    serverDir: string,
    dependencies: Record<string, string>,
    language: string
  ): Promise<void> {
    console.error(`Installing dependencies for ${language} in ${serverDir}`);
    
    switch (language) {
      case "typescript":
      case "javascript":
        await this.installNodeDependencies(serverDir, dependencies);
        break;
      case "python":
        await this.installPythonDependencies(serverDir, dependencies);
        break;
      default:
        throw new Error(`Unsupported language for dependencies: ${language}`);
    }
  }

  // Node.js (TypeScript/JavaScript) 用の依存関係インストール
  private async installNodeDependencies(
    serverDir: string,
    dependencies: Record<string, string>
  ): Promise<void> {
    try {
      // 既存のpackage.jsonを読み込む（存在する場合）
      let packageJson: any = {
        name: "mcp-dynamic-server",
        version: "1.0.0",
        type: "module",
        dependencies: {}
      };
      
      // アプリケーションのpackage.jsonを読み込む
      try {
        const appPackageJsonPath = path.join("/app", "package.json");
        const appPackageJsonContent = await fs.readFile(appPackageJsonPath, 'utf-8');
        const appPackageJson = JSON.parse(appPackageJsonContent);
        
        // 必要な依存関係をマージ
        if (appPackageJson.dependencies) {
          // 特に@modelcontextprotocol関連の依存関係をコピー
          Object.entries(appPackageJson.dependencies).forEach(([pkg, ver]) => {
            if (pkg.startsWith('@modelcontextprotocol') || pkg === 'mcp') {
              packageJson.dependencies[pkg] = ver;
            }
          });
        }
        
        console.error(`Merged dependencies from app package.json`);
      } catch (error) {
        console.error(`Error reading app package.json:`, error);
        // エラーがあっても続行
      }
      
      // ユーザー指定の依存関係をマージ
      Object.entries(dependencies).forEach(([pkg, ver]) => {
        packageJson.dependencies[pkg] = ver;
      });
      
      // package.jsonを書き込む
      await fs.writeFile(
        path.join(serverDir, "package.json"),
        JSON.stringify(packageJson, null, 2)
      );
      
      // npm install の実行
      const npmCommand = await getCommandPath("npm");
      await new Promise<void>((resolve, reject) => {
        const installProcess = spawn(
          npmCommand,
          ["install"],
          {
            stdio: ["ignore", "pipe", "pipe"],
            shell: true,
            env: { ...process.env },
            cwd: serverDir
          }
        );
        
        installProcess.stdout.on("data", (data) => {
          console.error(`NPM stdout: ${data}`);
        });
        
        installProcess.stderr.on("data", (data) => {
          console.error(`NPM stderr: ${data}`);
        });
        
        installProcess.on("exit", (code) => {
          if (code === 0) {
            console.error(`NPM install successful`);
            resolve();
          } else {
            console.error(`NPM install failed with code ${code}`);
            reject(new Error(`NPM install failed with code ${code}`));
          }
        });
      });
    } catch (error) {
      console.error(`Error installing Node.js dependencies:`, error);
      throw error;
    }
  }

  // Python 用の依存関係インストール
  private async installPythonDependencies(
    serverDir: string,
    dependencies: Record<string, string>
  ): Promise<void> {
    try {
      // requirements.txt の作成
      const requirementsContent = Object.entries(dependencies)
        .map(([pkg, ver]) => `${pkg}${ver}`)
        .join("\n");
      
      await fs.writeFile(
        path.join(serverDir, "requirements.txt"),
        requirementsContent
      );
      
      // pip install の実行
      const pipCommand = await getCommandPath("pip");
      await new Promise<void>((resolve, reject) => {
        const installProcess = spawn(
          pipCommand,
          ["install", "-r", "requirements.txt"],
          {
            stdio: ["ignore", "pipe", "pipe"],
            shell: true,
            env: { ...process.env },
            cwd: serverDir
          }
        );
        
        installProcess.stdout.on("data", (data) => {
          console.error(`PIP stdout: ${data}`);
        });
        
        installProcess.stderr.on("data", (data) => {
          console.error(`PIP stderr: ${data}`);
        });
        
        installProcess.on("exit", (code) => {
          if (code === 0) {
            console.error(`PIP install successful`);
            resolve();
          } else {
            console.error(`PIP install failed with code ${code}`);
            reject(new Error(`PIP install failed with code ${code}`));
          }
        });
      });
    } catch (error) {
      console.error(`Error installing Python dependencies:`, error);
      throw error;
    }
  }

  // Execute a tool on a server
  async executeToolOnServer(
    serverId: string,
    toolName: string,
    args: Record<string, any>
  ): Promise<any> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Call the tool on the server using the MCP client
      const result = await server.client.callTool({
        name: toolName,
        arguments: args,
      });

      return result;
    } catch (error) {
      console.error(`Error executing tool on server ${serverId}:`, error);
      throw error;
    }
  }

  // Get tools from a server
  async getServerTools(serverId: string): Promise<any> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Get tools from the server using the MCP client
      const tools = await server.client.listTools();
      return tools;
    } catch (error) {
      console.error(`Error getting tools from server ${serverId}:`, error);
      throw error;
    }
  }

  // Update a server
  async updateServer(
    serverId: string,
    code: string
  ): Promise<{ success: boolean; message: string }> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Update server code
      await fs.writeFile(server.filePath, code);

      // Close the client connection
      await server.transport.close();

      // Kill the server process
      server.process.kill();

      // Wait for process to exit
      await new Promise<void>((resolve) => {
        server.process.on("exit", () => {
          resolve();
        });
      });

      // Remove the server from the map
      this.servers.delete(serverId);

      // Create new server with updated code
      const newServerId = await this.createServer(code, server.language);

      return {
        success: true,
        message: `Server ${serverId} updated and restarted as ${newServerId}`,
      };
    } catch (error) {
      console.error(`Error updating server ${serverId}:`, error);
      throw error;
    }
  }

  // Delete a server
  async deleteServer(
    serverId: string
  ): Promise<{ success: boolean; message: string }> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Close the client connection
      await server.transport.close();

      // Kill server process
      server.process.kill();

      // Remove server from map
      this.servers.delete(serverId);

      // Delete server directory
      const serverDir = path.dirname(server.filePath);
      await fs.rm(serverDir, { recursive: true, force: true });

      return {
        success: true,
        message: `Server ${serverId} deleted`,
      };
    } catch (error) {
      console.error(`Error deleting server ${serverId}:`, error);
      throw error;
    }
  }

  // List all servers
  listServers(): string[] {
    return Array.from(this.servers.keys());
  }

  // Close all servers
  async closeAll(): Promise<void> {
    for (const [serverId, server] of this.servers.entries()) {
      try {
        await server.transport.close();
        server.process.kill();
        console.error(`Closed server ${serverId}`);
      } catch (error) {
        console.error(`Error closing server ${serverId}:`, error);
      }
    }

    this.servers.clear();
  }
}

// Tool definitions
// const createServerTool: Tool = {
//   name: "create-server",
//   description: "Create a new MCP server from code",
//   inputSchema: {
//     type: "object",
//     properties: {
//       code: {
//         type: "string",
//         description: "The server code",
//       },
//       language: {
//         type: "string",
//         enum: ["typescript", "javascript", "python"],
//         description: "The programming language of the server code",
//       },
//     },
//     required: ["code", "language"],
//   },
// };

const createServerFromTemplateTool: Tool = {
  name: "create-server-from-template",
  description: `Create a new MCP server from a template.
  
  以下のテンプレートコードをベースに、ユーザーの要求に合わせたサーバーを実装してください。
  言語に応じて適切なテンプレートを選択し、必要に応じて機能を追加・変更してください。
  
  TypeScriptテンプレート:
  \`\`\`typescript
  import { Server } from "@modelcontextprotocol/sdk/server/index.js";
  import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
  import { 
    CallToolRequestSchema, 
    ListToolsRequestSchema 
  } from "@modelcontextprotocol/sdk/types.js";

  const server = new Server({
    name: "dynamic-test-server",
    version: "1.0.0"
  }, {
    capabilities: {
      tools: {}
    }
  });

  // ここでツールを実装してください
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [{
        name: "echo",
        description: "Echo back a message",
        inputSchema: {
          type: "object",
          properties: {
            message: { type: "string" }
          },
          required: ["message"]
        }
      }]
    };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (request.params.name === "echo") {
      // TypeScriptの型を適切に扱うため、型アサーションを使用
      const message = request.params.arguments.message as string;
      // または any を使う: const message: any = request.params.arguments.message;
      
      return {
        content: [
          {
            type: "text",
            text: \`Echo: \${message}\`
          }
        ]
      };
    }
    throw new Error("Tool not found");
  });

  // Server startup
  const transport = new StdioServerTransport();
  server.connect(transport);
  \`\`\`
  
  Pythonテンプレート:
  \`\`\`python
  import asyncio
  from mcp.server import Server
  from mcp.server.stdio import stdio_server

  app = Server("dynamic-test-server")

  @app.list_tools()
  async def list_tools():
      return [
          {
              "name": "echo",
              "description": "Echo back a message",
              "inputSchema": {
                  "type": "object",
                  "properties": {
                      "message": {"type": "string"}
                  },
                  "required": ["message"]
              }
          }
      ]

  @app.call_tool()
  async def call_tool(name, arguments):
      if name == "echo":
          return [{"type": "text", "text": f"Echo: {arguments.get('message')}"}]
      raise ValueError(f"Tool not found: {name}")

  async def main():
      async with stdio_server() as streams:
          await app.run(
              streams[0],
              streams[1],
              app.create_initialization_options()
          )

  if __name__ == "__main__":
      asyncio.run(main())
  \`\`\`
  
  注意事項：
  - TypeScript実装時は、引数の型を適切に扱うために型アサーション（as string）を使用するか、
    明示的に型を宣言してください（例：const value: string = request.params.arguments.someValue）。
  - 複雑な型を扱う場合は、interface や type を定義して型安全性を確保することをお勧めします。
  
  ユーザーの要求に応じて上記のテンプレートを参考にカスタマイズしてください。その際、基本的な構造を維持しつつ、ツール名や機能を変更できます。`,
  inputSchema: {
    type: "object",
    properties: {
      language: {
        type: "string",
        enum: ["typescript", "python"],
        description: "The programming language for the template",
      },
      code: {
        type: "string",
        description:
          "カスタマイズしたサーバーコード。テンプレートを元に変更したコードを入力してください。省略した場合はデフォルトのテンプレートが使用されます。",
      },
      dependencies: {
        type: "object",
        description: "使用するライブラリとそのバージョン（例: { \"axios\": \"^1.0.0\" }）",
      },
    },
    required: ["language"],
  },
};

const executeToolTool: Tool = {
  name: "execute-tool",
  description: "Execute a tool on a server",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "The ID of the server",
      },
      toolName: {
        type: "string",
        description: "The name of the tool to execute",
      },
      args: {
        type: "object",
        description: "The arguments to pass to the tool",
      },
    },
    required: ["serverId", "toolName"],
  },
};

const getServerToolsTool: Tool = {
  name: "get-server-tools",
  description: "Get the tools available on a server",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "The ID of the server",
      },
    },
    required: ["serverId"],
  },
};

// const updateServerTool: Tool = {
//   name: "update-server",
//   description: `Update a server's code.まずupdate前のコードを読み、その内容からupdateの差分を考えてください。
//         その差分をもとに、update後のコードを作成してください。`,
//   inputSchema: {
//     type: "object",
//     properties: {
//       serverId: {
//         type: "string",
//         description: "The ID of the server",
//       },
//       code: {
//         type: "string",
//         description: `The new server code.
//         `,
//       },
//     },
//     required: ["serverId", "code"],
//   },
// };

const deleteServerTool: Tool = {
  name: "delete-server",
  description: "Delete a server",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "The ID of the server",
      },
    },
    required: ["serverId"],
  },
};

const listServersTool: Tool = {
  name: "list-servers",
  description: "List all running servers",
  inputSchema: {
    type: "object",
    properties: {},
  },
};

async function main() {
  try {
    console.error("Starting MCP Create Server...");
    const server = new Server(
      {
        name: "MCP Create Server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Create server manager
    const serverManager = new ServerManager();

    // Register tool handlers
    server.setRequestHandler(ListToolsRequestSchema, async () => {
      console.error("Received ListToolsRequest");
      return {
        tools: [
          createServerFromTemplateTool,
          executeToolTool,
          getServerToolsTool,
          deleteServerTool,
          listServersTool,
        ],
      };
    });

    server.setRequestHandler(
      CallToolRequestSchema,
      async (request: CallToolRequest) => {
        console.error("Received CallToolRequest:", request);
        try {
          if (!request.params.arguments) {
            throw new Error("No arguments provided");
          }

          switch (request.params.name) {
            case "create-server": {
              const args = request.params
                .arguments as unknown as CreateServerArgs;
              if (!args.code || !args.language) {
                throw new Error(
                  "Missing required arguments: code and language"
                );
              }

              const serverId = await serverManager.createServer(
                args.code,
                args.language
              );

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({ serverId }),
                  },
                ],
              };
            }

            case "create-server-from-template": {
              const args = request.params
                .arguments as unknown as CreateServerFromTemplateArgs;
              if (!args.language) {
                throw new Error("Missing required argument: language");
              }

              // LLMから提供されたカスタムコードがあればそれを使用し、なければデフォルトのテンプレートを使用
              let serverCode = args.code;

              // コードが提供されていない場合はデフォルトテンプレートを使用
              if (!serverCode) {
                // 既存のテンプレート選択ロジック
                switch (args.language) {
                  case "typescript":
                    serverCode = `/* TypeScriptテンプレート */`;
                    break;
                  case "python":
                    serverCode = `# Pythonテンプレート`;
                    break;
                  default:
                    throw new Error(
                      `Unsupported template language: ${args.language}`
                    );
                }
              }

              const result = await serverManager.createServer(
                serverCode,
                args.language,
                args.dependencies
              );

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({
                      serverId: result,
                      message: args.code
                        ? `Created server from custom code in ${args.language}`
                        : `Created server from ${args.language} template`,
                    }),
                  },
                ],
              };
            }

            case "execute-tool": {
              const args = request.params
                .arguments as unknown as ExecuteToolArgs;
              if (!args.serverId || !args.toolName) {
                throw new Error(
                  "Missing required arguments: serverId and toolName"
                );
              }

              const result = await serverManager.executeToolOnServer(
                args.serverId,
                args.toolName,
                args.args || {}
              );

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify(result),
                  },
                ],
              };
            }

            case "get-server-tools": {
              const args = request.params
                .arguments as unknown as GetServerToolsArgs;
              if (!args.serverId) {
                throw new Error("Missing required argument: serverId");
              }

              const tools = await serverManager.getServerTools(args.serverId);

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({ tools }),
                  },
                ],
              };
            }

            case "update-server": {
              const args = request.params
                .arguments as unknown as UpdateServerArgs;
              if (!args.serverId || !args.code) {
                throw new Error(
                  "Missing required arguments: serverId and code"
                );
              }

              const result = await serverManager.updateServer(
                args.serverId,
                args.code
              );

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify(result),
                  },
                ],
              };
            }

            case "delete-server": {
              const args = request.params
                .arguments as unknown as DeleteServerArgs;
              if (!args.serverId) {
                throw new Error("Missing required argument: serverId");
              }

              const result = await serverManager.deleteServer(args.serverId);

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify(result),
                  },
                ],
              };
            }

            case "list-servers": {
              const servers = serverManager.listServers();

              return {
                content: [
                  {
                    type: "text",
                    text: JSON.stringify({ servers }),
                  },
                ],
              };
            }

            default:
              throw new Error(`Unknown tool: ${request.params.name}`);
          }
        } catch (error) {
          console.error("Error executing tool:", error);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  error: error instanceof Error ? error.message : String(error),
                }),
              },
            ],
          };
        }
      }
    );

    // Set up transport and connect
    const transport = new StdioServerTransport();
    console.error("Connecting server to transport...");
    await server.connect(transport);

    console.error("MCP Create Server running on stdio");
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(`Failed to start server: ${errorMessage}`);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
