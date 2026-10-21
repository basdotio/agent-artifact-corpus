import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import readline from "readline/promises";
import dotenv from "dotenv";

dotenv.config();

class MCPClient {
    private mcp: Client;
    private transport: StdioClientTransport | null = null;

    constructor() {
        this.mcp = new Client({ name: "mcp-client-cli", version: "1.0.0" });
    }

    async connectToServer(serverScriptPath: string, envVars: Record<string, string>) {
        /**
         * Connect to an MCP server
         *
         * @param serverScriptPath - Path to the server script (.py or .js)
         * @param envVars - Optional environment variables to pass to the server
         */
        try {
            // Determine script type and appropriate command
            const isJs = serverScriptPath.endsWith(".js");
            const isPy = serverScriptPath.endsWith(".py");
            if (!isJs && !isPy) {
                throw new Error("Server script must be a .js or .py file");
            }
            const command = isPy
                ? process.platform === "win32"
                    ? "python"
                    : "python3"
                : process.execPath;

            // Initialize transport and connect to server
            this.transport = new StdioClientTransport({
                command,
                args: [serverScriptPath],
                env: { ...Object.fromEntries(
                    Object.entries(process.env).map(([k, v]) => [k, v ?? ''])
                ), ...envVars },
            });
            this.mcp.connect(this.transport);

        } catch (e) {
            console.log("Failed to connect to MCP server: ", e);
            throw e;
        }
    }

    async processQuery(collectionName: string) {
        /**
         * Process a query using Claude and available tools
         *
         * @param query - The user's input query
         * @returns Processed response as a string
         */

        try {
            const response = await this.mcp.callTool({
                name: "query",
                arguments: {
                    filter: {},
                    collectionName: collectionName
                }
            });
            const responseText = (response.content as { text: string }[]).map((response) => response.text);
            return responseText;
        } catch (e) {
            console.log("ERORR", e);
        }
    }

    async chatLoop() {
        /**
         * Run an interactive chat loop
         */
        const rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
        });

        try {
            console.log("MCP Client Started! This client currently only accepts collection names as input and returns 10 records from that collection.");
            while (true) {
                const message = await rl.question("\nEnter the collection name you want to query or 'quit' to exit.");
                if (message.toLowerCase() === "quit") {
                    break;
                }
                const response = await this.processQuery(message);
                console.log("\n" + response);
            }
        } finally {
            rl.close();
        }
    }

    async cleanup() {
        /**
         * Clean up resources
         */
        await this.mcp.close();
    }
}

async function main() {
    if (process.argv.length < 3) {
        console.log("Usage: node build/index.js <path_to_server_script>");
        return;
    }
    const mcpClient = new MCPClient();
    const connectionString = process.env.MONGO_CONNECTION_STRING || "";
    if (!connectionString) {
        throw new Error("MONGO_CONNECTION_STRING is not set");
    }
    try {
        // Pass environment variables to the server
        await mcpClient.connectToServer(process.argv[2], {
            MONGO_CONNECTION_STRING: connectionString,
            // Add other environment variables as needed
        });
        await mcpClient.chatLoop();
    } finally {
        await mcpClient.cleanup();
        process.exit(0);
    }
}

main();
