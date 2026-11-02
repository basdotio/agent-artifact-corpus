import type { Server } from "@modelcontextprotocol/sdk/server/index.js";
export declare const startHTTPStreamableServer: (createServer: () => Server, endpoint?: string, port?: number, host?: string) => Promise<void>;
