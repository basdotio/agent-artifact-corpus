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
import { z } from "zod";

// Type definitions for tool arguments
interface CreateServerArgs {
  code: string;
  language: "typescript" | "javascript" | "python";
}

interface CreateServerFromTemplateArgs {
  language: "typescript" | "python";
  code?: string;
  dependencies?: Record<string, string>; // Exemple: { "axios": "^1.0.0" }
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
  process: ChildProcess | null; // Le processus peut être null si géré par le transport
  client: Client;
  transport: StdioClientTransport;
  language: string;
  filePath: string;
}

// Get current file path and directory in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Utility to convert JSON Schema to Zod Schema and validate
function createZodSchemaFromJsonSchema(jsonSchema: any): z.ZodType<any> {
  if (!jsonSchema || typeof jsonSchema !== 'object') {
    return z.any();
  }

  switch (jsonSchema.type) {
    case 'string':
      return z.string();
    case 'number':
      return z.number();
    case 'boolean':
      return z.boolean();
    case 'array':
      const itemSchema = jsonSchema.items ? createZodSchemaFromJsonSchema(jsonSchema.items) : z.any();
      return z.array(itemSchema);
    case 'object':
      if (jsonSchema.properties) {
        const shape: Record<string, z.ZodType<any>> = {};
        
        // Create Zod properties
        for (const [key, propSchema] of Object.entries(jsonSchema.properties)) {
          shape[key] = createZodSchemaFromJsonSchema(propSchema as any);
        }
        
        let objectSchema = z.object(shape);
        
        // Handle required fields
        if (jsonSchema.required && Array.isArray(jsonSchema.required)) {
          // Zod object is strict by default, but we can make it optional
          const optionalShape: Record<string, z.ZodType<any>> = {};
          
          for (const [key, zodType] of Object.entries(shape)) {
            if (jsonSchema.required.includes(key)) {
              optionalShape[key] = zodType; // Required
            } else {
              optionalShape[key] = zodType.optional(); // Optional
            }
          }
          
          objectSchema = z.object(optionalShape);
        }
        
        return objectSchema;
      }
      return z.record(z.any());
    default:
      return z.any();
  }
}

// Function to validate MCP parameters against an inputSchema
function validateMcpParameters(args: any, inputSchema: any): { isValid: boolean; error?: string } {
  try {
    const zodSchema = createZodSchemaFromJsonSchema(inputSchema);
    zodSchema.parse(args);
    return { isValid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const issues = error.issues.map(issue => {
        if (issue.code === 'invalid_type' && issue.received === 'undefined') {
          return `Missing required parameter: '${issue.path.join('.')}'`;
        }
        return `Parameter '${issue.path.join('.')}': ${issue.message}`;
      });
      return { isValid: false, error: issues.join(', ') };
    }
    return { isValid: false, error: String(error) };
  }
}

// Function to get the absolute path of a command
async function getCommandPath(command: string): Promise<string | string[]> {
  try {
    // Handle special cases for Python commands
    if (command === "pip") {
      // Use python3 -m pip instead of direct pip
      console.error(`Using python3 -m pip instead of pip`);
      return ["python3", "-m", "pip"];
    }

    // In Docker, commands are usually in /usr/bin or /usr/local/bin
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
        // If command doesn't exist in this path, try the next one
      }
    }

    // Special checks for common commands
    if (command === "python3") {
      // Check if python3 exists in PATH
      try {
        await fs.access("/usr/bin/python3", fs.constants.X_OK);
        console.error("Found python3 at /usr/bin/python3");
        return "/usr/bin/python3";
      } catch {
        console.error("python3 not found, using command as is");
        return "python3";
      }
    }

    // If command is not found, return the original name
    console.error(
      `Command ${command} not found in standard paths, returning as is`
    );
    return command;
  } catch (error) {
    console.error(`Error resolving path for ${command}:`, error);
    return command;
  }
}

// Server management class
class ServerManager {
  private servers: Map<string, ConnectedServer> = new Map();

  private templatesDir: string = path.join(__dirname, "templates");
  private serversDir: string = path.join(os.tmpdir(), "mcp-create-servers");
  private dataDir: string = "/app/data/servers"; // Persistent data directory
  private savedServersFile: string = "/app/data/saved_servers.json";

  constructor() {
    // Ensure server directories exist
    this.initDirectories();
  }

  private async initDirectories() {
    try {
      await fs.mkdir(this.serversDir, { recursive: true });
      // Explicitly set permissions (to work in Docker)
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
      await fs.chmod(serverDir, 0o777); // Add permissions

      // Install dependencies if any (don't create symbolic link)
      if (dependencies && Object.keys(dependencies).length > 0) {
        await this.installDependencies(serverDir, dependencies, language);
      } else {
        // Create symbolic link only if no dependencies
        try {
          await fs.symlink(
            "/app/node_modules",
            path.join(serverDir, "node_modules")
          );
          console.error(`Created symlink to node_modules in ${serverDir}`);
        } catch (error) {
          console.error(`Error creating symlink: ${error}`);
          // Continue even on error
        }
      }

      // Write server code to file
      let filePath: string;
      let command: string;
      let args: string[] = [];

      // Configure common environment variables
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

          // Get and display absolute path
          const npxCommand = await getCommandPath("npx");
          command = Array.isArray(npxCommand) ? npxCommand[0] : npxCommand;
          console.error(`Using command path for npx: ${command}`);

          // Modified method to compile TypeScript
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
              cwd: "/app", // Spécifier le répertoire racine de l'application
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

          // Execute compiled JavaScript
          const nodeCommand = await getCommandPath("node");
          command = Array.isArray(nodeCommand) ? nodeCommand[0] : nodeCommand;
          args = [jsFilePath];
          break;

        case "javascript":
          filePath = path.join(serverDir, "index.js");
          await fs.writeFile(filePath, code);
          const nodeJSCommand = await getCommandPath("node");
          command = Array.isArray(nodeJSCommand) ? nodeJSCommand[0] : nodeJSCommand;
          args = [filePath];
          break;

        case "python":
          filePath = path.join(serverDir, "server.py");
          await fs.writeFile(filePath, code);
          const pythonCommand = await getCommandPath("python3");
          command = Array.isArray(pythonCommand) ? pythonCommand[0] : pythonCommand;
          args = [filePath];
          break;

        default:
          throw new Error(`Unsupported language: ${language}`);
      }

      console.error(`Creating MCP transport: ${command} ${args.join(" ")}`);

      // Créer un client MCP pour communiquer avec le serveur
      // Le transport gère lui-même le spawn du processus
      const transport = new StdioClientTransport({
        command,
        args,
        env: commonEnv, // Utiliser les mêmes variables d'environnement
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
        // Fermer le transport en cas d'erreur
        try {
          await transport.close();
        } catch (closeError) {
          console.error(`Error closing transport: ${closeError}`);
        }
        throw error;
      }

      // Stocker les informations du serveur
      this.servers.set(serverId, {
        process: null, // Le processus est géré par le transport
        client,
        transport,
        language,
        filePath,
      });

      // Gérer la fermeture du transport
      transport.onclose = () => {
        console.error(`Server ${serverId} transport closed`);
        this.servers.delete(serverId);
      };

      transport.onerror = (error) => {
        console.error(`Server ${serverId} transport error:`, error);
        this.servers.delete(serverId);
      };

      return serverId;
    } catch (error) {
      // Nettoyer en cas d'erreur
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

  // Méthode pour installer les dépendances
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

  // Installation des dépendances Node.js (TypeScript/JavaScript)
  private async installNodeDependencies(
    serverDir: string,
    dependencies: Record<string, string>
  ): Promise<void> {
    try {
      // Charger le package.json existant (s'il existe)
      let packageJson: any = {
        name: "mcp-dynamic-server",
        version: "1.0.0",
        type: "module",
        dependencies: {}
      };

      // Charger le package.json de l'application
      try {
        const appPackageJsonPath = path.join("/app", "package.json");
        const appPackageJsonContent = await fs.readFile(appPackageJsonPath, 'utf-8');
        const appPackageJson = JSON.parse(appPackageJsonContent);

        // Fusionner les dépendances nécessaires
        if (appPackageJson.dependencies) {
          // Copier particulièrement les dépendances @modelcontextprotocol
          Object.entries(appPackageJson.dependencies).forEach(([pkg, ver]) => {
            if (pkg.startsWith('@modelcontextprotocol') || pkg === 'mcp') {
              packageJson.dependencies[pkg] = ver;
            }
          });
        }

        console.error(`Merged dependencies from app package.json`);
      } catch (error) {
        console.error(`Error reading app package.json:`, error);
        // Continuer même en cas d'erreur
      }

      // Fusionner les dépendances spécifiées par l'utilisateur
      Object.entries(dependencies).forEach(([pkg, ver]) => {
        packageJson.dependencies[pkg] = ver;
      });

      // Écrire le package.json
      await fs.writeFile(
        path.join(serverDir, "package.json"),
        JSON.stringify(packageJson, null, 2)
      );

      // Exécuter npm install
      const npmCommand = await getCommandPath("npm");
      await new Promise<void>((resolve, reject) => {
        // Gérer le cas où npmCommand est un tableau
        let command: string;
        let args: string[];

        if (Array.isArray(npmCommand)) {
          command = npmCommand[0];
          args = [...npmCommand.slice(1), "install"];
        } else {
          command = npmCommand;
          args = ["install"];
        }

        const installProcess = spawn(
          command,
          args,
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

  // Installation des dépendances Python
  private async installPythonDependencies(
    serverDir: string,
    dependencies: Record<string, string>
  ): Promise<void> {
    try {
      // Création du requirements.txt
      const requirementsContent = Object.entries(dependencies)
        .map(([pkg, ver]) => `${pkg}${ver}`)
        .join("\n");

      await fs.writeFile(
        path.join(serverDir, "requirements.txt"),
        requirementsContent
      );

      // Exécuter pip install
      const pipCommand = await getCommandPath("pip");
      await new Promise<void>((resolve, reject) => {
        // Gérer le cas où pipCommand est un tableau (python3 -m pip)
        let command: string;
        let args: string[];

        if (Array.isArray(pipCommand)) {
          command = pipCommand[0];
          args = [...pipCommand.slice(1), "install", "-r", "requirements.txt"];
        } else {
          command = pipCommand;
          args = ["install", "-r", "requirements.txt"];
        }

        const installProcess = spawn(
          command,
          args,
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

  // Exécuter un outil sur un serveur
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
      // 🔍 VALIDATION: Obtenir d'abord les outils du serveur pour valider les paramètres
      const toolsResponse = await server.client.listTools();
      const tool = toolsResponse.tools?.find((t: any) => t.name === toolName);
      
      if (!tool) {
        // Retourner une erreur MCP standard pour outil non trouvé
        return {
          isError: true,
          content: [{
            type: "text",
            text: JSON.stringify({
              jsonrpc: "2.0",
              error: {
                code: -32601,
                message: `Tool not found: ${toolName}`
              }
            })
          }]
        };
      }

      // 🔍 VALIDATION: Valider les paramètres contre l'inputSchema si présent
      if (tool.inputSchema) {
        const validation = validateMcpParameters(args, tool.inputSchema);
        if (!validation.isValid) {
          // Retourner une erreur MCP standard pour paramètres invalides (code -32602)
          return {
            isError: true,
            content: [{
              type: "text", 
              text: JSON.stringify({
                jsonrpc: "2.0",
                error: {
                  code: -32602,
                  message: `Invalid parameters: ${validation.error}`
                }
              })
            }]
          };
        }
      }

      // ✅ Validation réussie - Appeler l'outil sur le serveur
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

  // Obtenir les outils d'un serveur
  async getServerTools(serverId: string): Promise<any> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Obtenir les outils du serveur en utilisant le client MCP
      const tools = await server.client.listTools();
      return tools;
    } catch (error) {
      console.error(`Error getting tools from server ${serverId}:`, error);
      throw error;
    }
  }

  // Mettre à jour un serveur
  async updateServer(
    serverId: string,
    code: string
  ): Promise<{ success: boolean; message: string }> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Mettre à jour le code du serveur
      await fs.writeFile(server.filePath, code);

      // Fermer la connexion client et le transport
      await server.transport.close();

      // Le processus sera automatiquement tué par la fermeture du transport
      // Pas besoin d'attendre explicitement car le transport gère le processus

      // Supprimer le serveur de la map
      this.servers.delete(serverId);

      // Créer un nouveau serveur avec le code mis à jour
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

  // Supprimer un serveur
  async deleteServer(
    serverId: string
  ): Promise<{ success: boolean; message: string }> {
    const server = this.servers.get(serverId);
    if (!server) {
      throw new Error(`Server ${serverId} not found`);
    }

    try {
      // Fermer la connexion client et le transport
      await server.transport.close();

      // Le processus sera automatiquement tué par la fermeture du transport

      // Supprimer le serveur de la map
      this.servers.delete(serverId);

      // Supprimer le répertoire du serveur
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

  // Lister tous les serveurs
  listServers(): string[] {
    return Array.from(this.servers.keys());
  }

  // Fermer tous les serveurs
  async closeAll(): Promise<void> {
    for (const [serverId, server] of this.servers.entries()) {
      try {
        await server.transport.close();
        // Le processus sera automatiquement fermé par le transport
        console.error(`Closed server ${serverId}`);
      } catch (error) {
        console.error(`Error closing server ${serverId}:`, error);
      }
    }

    this.servers.clear();
  }

  // Cleanup method for graceful shutdown
  cleanup(): void {
    console.error("Starting cleanup process...");
    // Close all active servers synchronously for fast shutdown
    for (const [serverId, server] of this.servers.entries()) {
      try {
        console.error(`Terminating server ${serverId}...`);

        // Since we're using StdioClientTransport, the process is managed by the transport
        // Just close the transport which will properly terminate the underlying process
        try {
          server.transport.close();
        } catch (e) {
          // Ignore transport close errors during shutdown
          console.error(`Transport close error for ${serverId}:`, e);
        }
      } catch (error) {
        console.error(`Error during cleanup of server ${serverId}:`, error);
      }
    }
    this.servers.clear();
    console.error("Cleanup completed");
  }

  // 🔧 PERSISTENCE METHODS - Pour récupérer les serveurs sauvegardés
  async saveServerToDisk(serverId: string, name: string, code: string, language: string): Promise<void> {
    try {
      // Ensure data directory exists
      await fs.mkdir(path.dirname(this.savedServersFile), { recursive: true });

      // Read existing saved servers
      let savedServers: Record<string, any> = {};
      try {
        const data = await fs.readFile(this.savedServersFile, 'utf-8');
        savedServers = JSON.parse(data);
      } catch (error) {
        // File doesn't exist or is invalid, start fresh
        savedServers = {};
      }

      // Add new server
      savedServers[serverId] = {
        name,
        code,
        language,
        savedAt: new Date().toISOString(),
        serverId
      };

      // Save back to disk
      await fs.writeFile(this.savedServersFile, JSON.stringify(savedServers, null, 2));
      console.error(`✅ Server ${serverId} saved to disk as "${name}"`);
    } catch (error) {
      console.error(`❌ Error saving server ${serverId}:`, error);
      throw error;
    }
  }

  async listSavedServers(): Promise<Array<{ id: string, name: string, language: string, savedAt: string }>> {
    try {
      const data = await fs.readFile(this.savedServersFile, 'utf-8');
      const savedServers = JSON.parse(data);

      return Object.entries(savedServers).map(([id, server]: [string, any]) => ({
        id,
        name: server.name,
        language: server.language,
        savedAt: server.savedAt
      }));
    } catch (error) {
      // File doesn't exist or is invalid
      return [];
    }
  }

  async loadSavedServer(savedServerId: string): Promise<string> {
    try {
      const data = await fs.readFile(this.savedServersFile, 'utf-8');
      const savedServers = JSON.parse(data);

      const serverData = savedServers[savedServerId];
      if (!serverData) {
        throw new Error(`❌ Saved server ${savedServerId} not found`);
      }

      // Create a new running server from saved data
      const newServerId = await this.createServer(
        serverData.code,
        serverData.language
      );

      console.error(`✅ Loaded saved server "${serverData.name}" as new server ${newServerId}`);
      return newServerId;
    } catch (error) {
      console.error(`❌ Error loading saved server ${savedServerId}:`, error);
      throw error;
    }
  }

  async deleteSavedServer(savedServerId: string): Promise<void> {
    try {
      const data = await fs.readFile(this.savedServersFile, 'utf-8');
      const savedServers = JSON.parse(data);

      if (!savedServers[savedServerId]) {
        throw new Error(`❌ Saved server ${savedServerId} not found`);
      }

      delete savedServers[savedServerId];

      await fs.writeFile(this.savedServersFile, JSON.stringify(savedServers, null, 2));
      console.error(`🗑️ Saved server ${savedServerId} deleted from disk`);
    } catch (error) {
      console.error(`❌ Error deleting saved server ${savedServerId}:`, error);
      throw error;
    }
  }

  getServerCode(serverId: string): string | null {
    const server = this.servers.get(serverId);
    if (!server) return null;

    try {
      return require('fs').readFileSync(server.filePath, 'utf-8');
    } catch (error) {
      console.error(`Error reading server file ${server.filePath}:`, error);
      return null;
    }
  }

  getServerInfo(serverId: string): { language: string; filePath: string } | null {
    const server = this.servers.get(serverId);
    if (!server) return null;

    return {
      language: server.language,
      filePath: server.filePath
    };
  }
}

// Définitions des outils
// const createServerTool: Tool = {
//   name: "create-server",
//   description: "Créer un nouveau serveur MCP à partir du code",
//   inputSchema: {
//     type: "object",
//     properties: {
//       code: {
//         type: "string",
//         description: "Le code du serveur",
//       },
//       language: {
//         type: "string",
//         enum: ["typescript", "javascript", "python"],
//         description: "Le langage de programmation du code du serveur",
//       },
//     },
//     required: ["code", "language"],
//   },
// };

const createServerFromTemplateTool: Tool = {
  name: "create-server-from-template",
  description: `Create a new MCP server from a template.
  
  Please implement a server suitable for the user's needs based on the following template code.
  Select the appropriate template according to the language and add/modify functionalities as needed.
  
  TypeScript Template:
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

  // Implement your tools here
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
      // Use type assertion to properly handle TypeScript types
      const message = request.params.arguments.message as string;
      // or use any: const message: any = request.params.arguments.message;
      
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

  // Start the server
  const transport = new StdioServerTransport();
  server.connect(transport);
  \`\`\`
  
  Python Template:
  \`\`\`python
  #!/usr/bin/env python3
  import json
  import sys

  def handle_initialize(request):
      """Handle MCP initialization request"""
      return {
          "jsonrpc": "2.0",
          "id": request.get("id"),
          "result": {
              "protocolVersion": "2024-11-05",
              "capabilities": {
                  "tools": {}
              },
              "serverInfo": {
                  "name": "dynamic-python-server",
                  "version": "1.0.0"
              }
          }
      }

  def handle_tools_list(request):
      """Handle tools/list request"""
      return {
          "jsonrpc": "2.0", 
          "id": request.get("id"),
          "result": {
              "tools": [
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
          }
      }

  def handle_tools_call(request):
      """Handle tools/call request"""
      params = request.get("params", {})
      tool_name = params.get("name")
      arguments = params.get("arguments", {})
      
      if tool_name == "echo":
          message = arguments.get("message", "No message")
          return {
              "jsonrpc": "2.0",
              "id": request.get("id"), 
              "result": {
                  "content": [
                      {
                          "type": "text",
                          "text": f"Echo: {message}"
                      }
                  ]
              }
          }
      else:
          return {
              "jsonrpc": "2.0",
              "id": request.get("id"),
              "error": {
                  "code": -32601,
                  "message": f"Tool not found: {tool_name}"
              }
          }

  def main():
      """Main server loop with improved stability"""
      import signal
      import time
      
      # Ignore SIGPIPE to prevent premature exit
      signal.signal(signal.SIGPIPE, signal.SIG_DFL)
      
      try:
          while True:
              try:
                  line = sys.stdin.readline()
                  if not line or line.strip() == "":
                      # Keep server alive even with empty lines
                      time.sleep(0.01)
                      continue
                      
                  request = json.loads(line.strip())
                  method = request.get("method")
                  
                  if method == "initialize":
                      response = handle_initialize(request)
                  elif method == "tools/list":
                      response = handle_tools_list(request)
                  elif method == "tools/call":
                      response = handle_tools_call(request)
                  else:
                      response = {
                          "jsonrpc": "2.0",
                          "id": request.get("id"),
                          "error": {
                              "code": -32601,
                              "message": f"Method not found: {method}"
                          }
                      }
                  
                  print(json.dumps(response))
                  sys.stdout.flush()
                  
              except json.JSONDecodeError as e:
                  error_response = {
                      "jsonrpc": "2.0", 
                      "error": {
                          "code": -32700,
                          "message": f"Parse error: {str(e)}"
                      }
                  }
                  print(json.dumps(error_response))
                  sys.stdout.flush()
              except EOFError:
                  # Keep running even if stdin closes temporarily
                  time.sleep(0.1)
                  continue
              except Exception as e:
                  error_response = {
                      "jsonrpc": "2.0",
                      "id": request.get("id") if 'request' in locals() else None,
                      "error": {
                          "code": -32603,
                          "message": f"Internal error: {str(e)}"
                      }
                  }
                  print(json.dumps(error_response))
                  sys.stdout.flush()
      except KeyboardInterrupt:
          pass

  if __name__ == "__main__":
      main()
  \`\`\`
  
  Remarques importantes :
  - Lors de l'implémentation TypeScript, utilisez l'assertion de type (as string) pour gérer correctement les types d'arguments,
    ou déclarez explicitement les types (exemple : const value: string = request.params.arguments.someValue).
  - Pour les types complexes, il est recommandé de définir des interfaces ou des types pour assurer la sécurité des types.
  
  Veuillez personnaliser les modèles ci-dessus selon les besoins de l'utilisateur. Vous pouvez modifier les noms d'outils et les fonctionnalités tout en conservant la structure de base.`,
  inputSchema: {
    type: "object",
    properties: {
      language: {
        type: "string",
        enum: ["typescript", "python"],
        description: "Le langage de programmation pour le modèle",
      },
      code: {
        type: "string",
        description:
          "Code de serveur personnalisé. Entrez le code modifié basé sur le modèle. Si omis, le modèle par défaut sera utilisé.",
      },
      dependencies: {
        type: "object",
        description: "Bibliothèques utilisées et leurs versions (exemple: { \"axios\": \"^1.0.0\" })",
      },
    },
    required: ["language"],
  },
};

const executeToolTool: Tool = {
  name: "execute-tool",
  description: "Exécuter un outil sur un serveur",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "L'ID du serveur",
      },
      toolName: {
        type: "string",
        description: "Le nom de l'outil à exécuter",
      },
      args: {
        type: "object",
        description: "Les arguments à passer à l'outil",
      },
    },
    required: ["serverId", "toolName"],
  },
};

const getServerToolsTool: Tool = {
  name: "get-server-tools",
  description: "Obtenir les outils disponibles sur un serveur",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "L'ID du serveur",
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
  description: "Supprimer un serveur",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "L'ID du serveur",
      },
    },
    required: ["serverId"],
  },
};

const listServersTool: Tool = {
  name: "list-servers",
  description: "Lister tous les serveurs en cours d'exécution",
  inputSchema: {
    type: "object",
    properties: {},
  },
};

// 🔧 NOUVEAUX OUTILS DE PERSISTENCE - Pour récupérer les serveurs sauvegardés
const saveServerTool: Tool = {
  name: "save-server",
  description: "Sauvegarder un serveur en cours d'exécution sur disque pour le récupérer plus tard",
  inputSchema: {
    type: "object",
    properties: {
      serverId: {
        type: "string",
        description: "L'ID du serveur à sauvegarder",
      },
      name: {
        type: "string",
        description: "Un nom descriptif pour identifier le serveur sauvegardé",
      },
    },
    required: ["serverId", "name"],
  },
};

const listSavedServersTool: Tool = {
  name: "list-saved-servers",
  description: "Lister tous les serveurs sauvegardés sur disque",
  inputSchema: {
    type: "object",
    properties: {},
  },
};

const loadSavedServerTool: Tool = {
  name: "load-saved-server",
  description: "Charger un serveur sauvegardé depuis le disque et le remettre en cours d'exécution",
  inputSchema: {
    type: "object",
    properties: {
      savedServerId: {
        type: "string",
        description: "L'ID du serveur sauvegardé à charger",
      },
    },
    required: ["savedServerId"],
  },
};

const deleteSavedServerTool: Tool = {
  name: "delete-saved-server",
  description: "Supprimer définitivement un serveur sauvegardé du disque",
  inputSchema: {
    type: "object",
    properties: {
      savedServerId: {
        type: "string",
        description: "L'ID du serveur sauvegardé à supprimer",
      },
    },
    required: ["savedServerId"],
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

    // Créer le gestionnaire de serveurs
    const serverManager = new ServerManager();

    // Enregistrer les gestionnaires d'outils
    server.setRequestHandler(ListToolsRequestSchema, async () => {
      console.error("Received ListToolsRequest");
      return {
        tools: [
          createServerFromTemplateTool,
          executeToolTool,
          getServerToolsTool,
          deleteServerTool,
          listServersTool,
          // 🔧 NOUVEAUX OUTILS DE PERSISTENCE
          saveServerTool,
          listSavedServersTool,
          loadSavedServerTool,
          deleteSavedServerTool,
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

              // Validation plus explicite des paramètres
              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.language || typeof args.language !== 'string') {
                throw new Error("Missing or invalid required argument: language (must be a string)");
              }

              if (!["typescript", "python"].includes(args.language)) {
                throw new Error("Invalid language: must be 'typescript' or 'python'");
              }

              // Utiliser le code personnalisé fourni par LLM s'il existe, sinon utiliser le modèle par défaut
              let serverCode = args.code;

              // Utiliser le modèle par défaut si aucun code n'est fourni
              if (!serverCode) {
                // Logique de sélection de modèle existante
                switch (args.language) {
                  case "typescript":
                    serverCode = `/* Modèle TypeScript */`;
                    break;
                  case "python":
                    serverCode = `#!/usr/bin/env python3
import json
import sys
import signal

def handle_initialize(request):
    """Handle MCP initialization request"""
    request_id = request.get("id")
    if request_id is None:
        request_id = 1  # Provide default ID if missing
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "dynamic-python-server",
                "version": "1.0.0"
            }
        }
    }

def handle_tools_list(request):
    """Handle tools/list request"""
    request_id = request.get("id")
    if request_id is None:
        request_id = 1  # Provide default ID if missing
    
    return {
        "jsonrpc": "2.0",
        "id": request_id, 
        "result": {
            "tools": [
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
        }
    }

def validate_tool_parameters(tool_name, arguments, tool_schema):
    """Validate tool parameters against schema"""
    if not tool_schema or 'inputSchema' not in tool_schema:
        return {"valid": True}
    
    schema = tool_schema['inputSchema']
    if schema.get('type') != 'object':
        return {"valid": True}  # Skip validation for non-object schemas
    
    properties = schema.get('properties', {})
    required_fields = schema.get('required', [])
    
    # Check required fields
    for field in required_fields:
        if field not in arguments:
            return {
                "valid": False,
                "error": f"Missing required parameter: '{field}'"
            }
    
    # Check field types (basic validation)
    for field, value in arguments.items():
        if field in properties:
            expected_type = properties[field].get('type')
            if expected_type == 'string' and not isinstance(value, str):
                return {
                    "valid": False,
                    "error": f"Parameter '{field}' must be a string"
                }
            elif expected_type == 'number' and not isinstance(value, (int, float)):
                return {
                    "valid": False,
                    "error": f"Parameter '{field}' must be a number"
                }
            elif expected_type == 'boolean' and not isinstance(value, bool):
                return {
                    "valid": False,
                    "error": f"Parameter '{field}' must be a boolean"
                }
    
    return {"valid": True}

def handle_tools_call(request):
    """Handle tools/call request with parameter validation"""
    params = request.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    request_id = request.get("id")
    if request_id is None:
        request_id = 1  # Provide default ID if missing
    
    # Define tool schemas for validation
    TOOL_SCHEMAS = {
        "echo": {
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        }
    }
    
    if tool_name == "echo":
        # 🔍 VALIDATION: Validate parameters before execution
        validation = validate_tool_parameters(tool_name, arguments, TOOL_SCHEMAS.get(tool_name))
        if not validation["valid"]:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"Invalid parameters: {validation['error']}"
                }
            }
        
        # ✅ Parameters are valid - execute tool
        message = arguments.get("message")  # No default value since validation passed
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Echo: {message}"
                    }
                ]
            }
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Tool not found: {tool_name}"
            }
        }

def main():
    """Main server loop - robust stdin handling"""
    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    
    try:
        while True:
            try:
                # Read line from stdin - this blocks until input is available
                line = sys.stdin.readline()
                
                # Check for EOF (empty string means stdin closed)
                if not line:
                    break
                    
                # Skip empty lines
                line = line.strip()
                if not line:
                    continue
                    
                # Parse JSON request
                request = json.loads(line)
                method = request.get("method")
                
                # Route to appropriate handler
                if method == "initialize":
                    response = handle_initialize(request)
                elif method == "tools/list":
                    response = handle_tools_list(request)
                elif method == "tools/call":
                    response = handle_tools_call(request)
                else:
                    request_id = request.get("id")
                    if request_id is None:
                        request_id = 1  # Provide default ID if missing
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                
                # Send response
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0", 
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
            except EOFError:
                # EOF received - exit gracefully
                break
                
            except Exception as e:
                request_id = 1  # Default ID for internal errors
                if 'request' in locals() and request.get("id") is not None:
                    request_id = request.get("id")
                    
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        pass  # Exit gracefully on Ctrl+C

if __name__ == "__main__":
    main()`;
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
                        ? `Serveur créé à partir du code personnalisé en ${args.language}`
                        : `Serveur créé à partir du modèle ${args.language}`,
                    }),
                  },
                ],
              };
            }

            case "execute-tool": {
              const args = request.params
                .arguments as unknown as ExecuteToolArgs;

              // Validation plus explicite des paramètres
              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.serverId || typeof args.serverId !== 'string') {
                throw new Error("Missing or invalid required argument: serverId (must be a string)");
              }

              if (!args.toolName || typeof args.toolName !== 'string') {
                throw new Error("Missing or invalid required argument: toolName (must be a string)");
              }

              // Extraire les vrais arguments - ils peuvent être dans args.args selon le format de la requête
              let toolArgs = args.args || {};

              // Si args.args existe, c'est là que sont les vrais paramètres de l'outil
              if (args.args && typeof args.args === 'object') {
                toolArgs = args.args;
              }

              const result = await serverManager.executeToolOnServer(
                args.serverId,
                args.toolName,
                toolArgs
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

              // Validation plus explicite des paramètres
              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.serverId || typeof args.serverId !== 'string') {
                throw new Error("Missing or invalid required argument: serverId (must be a string)");
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

              // Validation plus explicite des paramètres
              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.serverId || typeof args.serverId !== 'string') {
                throw new Error("Missing or invalid required argument: serverId (must be a string)");
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

            // 🔧 NOUVEAUX GESTIONNAIRES DE PERSISTENCE
            case "save-server": {
              const args = request.params.arguments as { serverId: string; name: string };

              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.serverId || typeof args.serverId !== 'string') {
                throw new Error("Missing or invalid required argument: serverId (must be a string)");
              }

              if (!args.name || typeof args.name !== 'string') {
                throw new Error("Missing or invalid required argument: name (must be a string)");
              }

              // Get server code
              const serverCode = serverManager.getServerCode(args.serverId);
              if (!serverCode) {
                throw new Error(`Server ${args.serverId} not found or code is not accessible`);
              }

              // Get server info
              const serverInfo = serverManager.getServerInfo(args.serverId);
              if (!serverInfo) {
                throw new Error(`Server ${args.serverId} not found`);
              }

              await serverManager.saveServerToDisk(args.serverId, args.name, serverCode, serverInfo.language);

              return {
                content: [
                  {
                    type: "text",
                    text: `✅ Server ${args.serverId} saved as "${args.name}"`,
                  },
                ],
              };
            }

            case "list-saved-servers": {
              const savedServers = await serverManager.listSavedServers();

              if (savedServers.length === 0) {
                return {
                  content: [
                    {
                      type: "text",
                      text: "📂 No saved servers found",
                    },
                  ],
                };
              }

              const serversList = savedServers.map(server =>
                `📄 ${server.name} (ID: ${server.id}, Language: ${server.language}, Saved: ${server.savedAt})`
              ).join('\n');

              return {
                content: [
                  {
                    type: "text",
                    text: `📂 Saved servers:\n${serversList}`,
                  },
                ],
              };
            }

            case "load-saved-server": {
              const args = request.params.arguments as { savedServerId: string };

              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.savedServerId || typeof args.savedServerId !== 'string') {
                throw new Error("Missing or invalid required argument: savedServerId (must be a string)");
              }

              const newServerId = await serverManager.loadSavedServer(args.savedServerId);

              return {
                content: [
                  {
                    type: "text",
                    text: `✅ Saved server loaded as new server: ${newServerId}`,
                  },
                ],
              };
            }

            case "delete-saved-server": {
              const args = request.params.arguments as { savedServerId: string };

              if (!args || typeof args !== 'object') {
                throw new Error("Arguments must be an object");
              }

              if (!args.savedServerId || typeof args.savedServerId !== 'string') {
                throw new Error("Missing or invalid required argument: savedServerId (must be a string)");
              }

              await serverManager.deleteSavedServer(args.savedServerId);

              return {
                content: [
                  {
                    type: "text",
                    text: `🗑️ Saved server ${args.savedServerId} deleted from disk`,
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

    // Add graceful shutdown handling
    const cleanup = () => {
      console.error('Shutting down gracefully...');
      try {
        serverManager.cleanup();
        console.error('All servers closed successfully');
      } catch (error) {
        console.error('Error during cleanup:', error);
      }
      process.exit(0);
    };

    process.on('SIGTERM', cleanup);
    process.on('SIGINT', cleanup);
    process.on('SIGHUP', cleanup);

    // Configurer le transport et se connecter
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

// Global error handling
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  process.exit(1);
});

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
