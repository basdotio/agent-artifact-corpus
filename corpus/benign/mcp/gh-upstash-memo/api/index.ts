import { Hono } from "hono";
import { Redis } from "@upstash/redis";
import { Ratelimit } from "@upstash/ratelimit";
import { nanoid } from "nanoid";

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL!,
  token: process.env.UPSTASH_REDIS_REST_TOKEN!,
});

const ratelimit = new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(60, "1 m"),
});

const app = new Hono().basePath("/api");

// Rate limit middleware
app.use(async (c, next) => {
  const ip = c.req.header("x-forwarded-for")?.split(",")[0] || "anonymous";
  const { success, remaining } = await ratelimit.limit(ip);
  c.header("X-RateLimit-Remaining", remaining.toString());
  if (!success) {
    return c.json({ error: "Rate limit exceeded" }, 429);
  }
  return next();
});

// Accept id from query params, path, or body
app.all("/get/:id?", async (c) => {
  let id = c.req.param("id") || c.req.query("id");

  // Try body if not in query/path
  if (!id) {
    try {
      const body = await c.req.json();
      id = body.id;
    } catch {
      // No body or invalid JSON
    }
  }

  if (!id) {
    return c.json({ error: "Missing id parameter" }, 400);
  }
  const summary = await redis.get(id);
  if (!summary) {
    return c.json({ error: "Summary not found" }, 404);
  }
  // Upstash auto-parses JSON, so stringify if we got an object back
  const summaryStr = typeof summary === "string" ? summary : JSON.stringify(summary);
  return c.json({ summary: summaryStr });
});

app.post("/set", async (c) => {
  const body = await c.req.json();
  // Accept summary, context, or data field
  const summary = body.summary || body.context || body.data;
  if (!summary) {
    return c.json({ error: "Missing summary/context/data field" }, 400);
  }
  const ttlMins = body.ttlMins || 1440; // 24 hours
  const id = nanoid();
  await redis.set(id, summary, { ex: ttlMins * 60 });
  return c.json({ id, message: "Data received" });
});

export default app;
