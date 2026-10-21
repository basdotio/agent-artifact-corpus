import { getHoldings, getPositions, getProfile, placeOrder } from "./trade";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

// Create an MCP server
const server = new McpServer({
  name: "Trade Stocks",
  version: "1.0.0"
});

// Get profile
server.tool("get-profile", "Get my profile on zerodha exchange",
    {},
    async () => {
        const profile = await getProfile();
        return {
            content : [{type : "text", text : String(profile)}]
        }
    }
)
// Buy a stock 
server.tool("buy-stock", "Buy a stock on zerodha exchange for the user. It execute a real order for the user on the exchange",
    {stock : z.string(), quantity : z.number()}, 
    async ({stock, quantity}) => {
        placeOrder(stock, quantity, "BUY");
        return {
            content : [{type : "text", text : "Order placed successfully"}]
        }
    }
)

// Sell a stock 
server.tool("sell-stock", "Sell a stock on zerodha exchange for the user. It execute a real order for the user on the exchange",
    {stock : z.string(), quantity : z.number()}, 
    async ({stock, quantity}) => {
        placeOrder(stock, quantity, "SELL");
        return {
            content : [{type : "text", text : "Order placed successfully"}]
        }
    }
)

// Show portfolio
server.tool("show-portfolio", "Shows my completed portfolio on zerodha exchange",
    {},
    async () => {
        const holdings = await getHoldings();
        return {
            content : [{type : "text", text : holdings}]
        }
    }
)

// Show positions
server.tool("show-positions", "Shows my open positions on zerodha exchange",
    {},
    async () => {
        const positions = await getPositions();
        return {    
            content : [{type : "text", text : positions}]
        }
    }
)

// Start receiving messages on stdin and sending messages on stdout
const transport = new StdioServerTransport();
await server.connect(transport);