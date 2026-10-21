import { serve } from "@hono/node-server";
import { createApp } from "./app.js";
const port = Number(process.env.PORT ?? 3000);
const base = process.env.PUBLIC_BASE_URL ?? `http://localhost:${port}`;
const instance = createApp(base, {
  trustFlyProxy: Boolean(process.env.FLY_APP_NAME),
  openaiAppsChallenge: process.env.OPENAI_APPS_CHALLENGE
});
const server = serve({ fetch: instance.app.fetch, port, hostname: "0.0.0.0" });
console.log(`Signal Galaxy listening at ${base}`);
let closing = false;
async function close() {
  if (closing) return; closing = true;
  const timeout = setTimeout(() => process.exit(0), 5000); timeout.unref();
  server.close(); await instance.close();
}
process.once("SIGINT", close); process.once("SIGTERM", close);
