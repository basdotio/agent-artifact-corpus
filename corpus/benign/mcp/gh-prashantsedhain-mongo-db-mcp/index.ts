import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { getMongoClient, runReadOnlyTransaction } from "./mongo_utils.js";

const server = new McpServer({
    name: "example-servers/mongodb",
    version: "0.1.0"
});

server.tool(
    "query",
    {
        collectionName: z.string(),
        filter: z.object({}).catchall(z.any()),
        limit: z.number().optional().default(10)
    },
    async ({ collectionName, filter, limit }) => {

        const connectionString = process.env.MONGO_CONNECTION_STRING;

        if (!connectionString) {
            throw new Error("MONGO_CONNECTION_STRING is not set");
        }

        const client = await getMongoClient(connectionString);
        if (!client) {
            throw new Error("Failed to connect to MongoDB");
        }

        console.log("Running query", filter, collectionName);
        const queryResult = await runReadOnlyTransaction(client, collectionName, filter, limit);
        return {
            content: [{ type: "text", text: queryResult.map((doc) => JSON.stringify(doc)).join("\n") }],
        };
    }
);


async function runServer() {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}

runServer().catch(console.error);