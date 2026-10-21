import { serve } from "@hono/node-server";
import { createApp } from "./app.js";
import { loadConfig } from "./config.js";

const config = loadConfig();
const instance = createApp(config);
const server = serve({ fetch: instance.app.fetch, port: config.port });
console.log(`Agents Chat listening at ${config.publicBaseUrl}/mcp`);

let closing = false;
async function close() {
  if (closing) return;
  closing = true;
  server.close();
  await instance.close();
}
process.once("SIGINT", close);
process.once("SIGTERM", close);
