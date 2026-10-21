import { describe as testDescribe, it, expect } from "vitest";
import { Hono } from "hono";
import { z } from "zod";
import { mcp, registerTool } from "./mcp";

testDescribe("mcp", () => {
  it("adds /mcp endpoint to app", async () => {
    const app = new Hono().get("/users", (c) => c.json([]));
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "test", version: "1.0.0" },
          },
        }),
      }),
    );

    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toContain('"name":"Test"');
    expect(text).toContain('"version":"1.0.0"');
  });

  it("exposes routes as MCP tools", async () => {
    const app = new Hono()
      .get("/users", (c) => c.json([]))
      .post("/users", (c) => c.json({ id: 1 }))
      .get("/users/:id", (c) => c.json({ id: c.req.param("id") }));

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("get_users");
    expect(text).toContain("post_users");
    expect(text).toContain("get_users_by_id");
  });

  it("uses custom descriptions from describe()", async () => {
    const app = new Hono().get("/users", registerTool("My custom description"), (c) => c.json([]));

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("My custom description");
  });

  it("calls the actual API endpoint when tool is invoked", async () => {
    const app = new Hono().get("/users", (c) => c.json([{ id: 1, name: "Alice" }]));

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "get_users", arguments: {} },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("Alice");
  });

  it("handles path parameters correctly", async () => {
    const app = new Hono().get("/users/:id", (c) => c.json({ id: c.req.param("id"), name: "Bob" }));

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "get_users_by_id", arguments: { id: "42" } },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain('\\"id\\": \\"42\\"');
    expect(text).toContain("Bob");
  });

  it("handles POST with body", async () => {
    const app = new Hono().post("/users", async (c) => {
      const body = await c.req.json();
      return c.json({ id: 1, ...body });
    });

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: {
            name: "post_users",
            arguments: { body: { name: "Charlie" } },
          },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("Charlie");
  });

  it("includes server description in initialize response", async () => {
    const app = new Hono().get("/users", (c) => c.json([]));
    const wrapped = mcp(app, {
      name: "Test",
      version: "1.0.0",
      description: "My test server",
    });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "test", version: "1.0.0" },
          },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("My test server");
  });

  it("uses custom mcpPath", async () => {
    const app = new Hono().get("/users", (c) => c.json([]));
    const wrapped = mcp(app, {
      name: "Test",
      version: "1.0.0",
      mcpPath: "/api/mcp",
    });

    const res = await wrapped.fetch(
      new Request("http://localhost/api/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "test", version: "1.0.0" },
          },
        }),
      }),
    );

    expect(res.status).toBe(200);
  });

  it("returns CORS headers on OPTIONS request", async () => {
    const app = new Hono().get("/users", (c) => c.json([]));
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(new Request("http://localhost/mcp", { method: "OPTIONS" }));

    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");
    expect(res.headers.get("Access-Control-Allow-Methods")).toContain("POST");
  });

  it("adds CORS headers to responses", async () => {
    const app = new Hono().get("/users", (c) => c.json([]));
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );

    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");
  });

  it("handles DELETE method", async () => {
    const app = new Hono().delete("/users/:id", (c) =>
      c.json({ deleted: true, id: c.req.param("id") }),
    );
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "delete_users_by_id", arguments: { id: "99" } },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("deleted");
    expect(text).toContain("99");
  });

  it("handles PUT method", async () => {
    const app = new Hono().put("/users/:id", async (c) => {
      const body = await c.req.json();
      return c.json({ id: c.req.param("id"), ...body });
    });
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "put_users_by_id", arguments: { id: "5", body: { name: "Updated" } } },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("Updated");
  });

  it("handles PATCH method", async () => {
    const app = new Hono().patch("/users/:id", async (c) => {
      const body = await c.req.json();
      return c.json({ patched: true, ...body });
    });
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "patch_users_by_id", arguments: { id: "5", body: { status: "active" } } },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("patched");
  });

  it("handles query parameters", async () => {
    const app = new Hono().get("/users", (c) => {
      const limit = c.req.query("limit");
      return c.json({ limit });
    });
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "get_users", arguments: { query: { limit: "10" } } },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("10");
  });

  it("generates default descriptions without describe()", async () => {
    const app = new Hono()
      .get("/users", (c) => c.json([]))
      .post("/items", (c) => c.json({}))
      .delete("/posts/:id", (c) => c.json({}));
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("List users");
    expect(text).toContain("Create items");
    expect(text).toContain("Delete posts");
  });

  it("excludes /mcp routes from tools", async () => {
    const app = new Hono()
      .get("/users", (c) => c.json([]))
      .get("/mcp/health", (c) => c.json({ ok: true }));
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("get_users");
    expect(text).not.toContain("mcp_health");
  });

  it("handles API errors gracefully", async () => {
    const app = new Hono().get("/error", (c) => c.json({ error: "Not found" }, 404));
    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "get_error", arguments: {} },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("Not found");
    expect(text).toContain('"isError":true');
  });

  it("includes title in server info", async () => {
    const app = new Hono().get("/users", (c) => c.json([]));
    const wrapped = mcp(app, {
      name: "Test",
      version: "1.0.0",
      title: "My API Title",
    });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: {
            protocolVersion: "2024-11-05",
            capabilities: {},
            clientInfo: { name: "test", version: "1.0.0" },
          },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("My API Title");
  });
});

testDescribe("registerTool", () => {
  it("returns middleware with string description", () => {
    const middleware = registerTool("Test description");
    expect(typeof middleware).toBe("function");
  });

  it("returns middleware with config object", () => {
    const middleware = registerTool({ description: "Test description" });
    expect(typeof middleware).toBe("function");
  });

  it("uses inputSchema from describe config", async () => {
    const app = new Hono().post(
      "/users",
      registerTool({
        description: "Create a new user",
        inputSchema: {
          name: z.string().describe("User name"),
          email: z.string().email().describe("User email"),
        },
      }),
      async (c) => {
        const { name } = c.req.valid("json");
        return c.json({ id: 1, name });
      },
    );

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/list",
          params: {},
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("Create a new user");
    expect(text).toContain("name");
    expect(text).toContain("email");
    expect(text).toContain("User name");
    expect(text).toContain("User email");
  });

  it("returns structuredContent when outputSchema is defined", async () => {
    const app = new Hono().get(
      "/users",
      registerTool({
        description: "List users",
        outputSchema: {
          users: z.array(z.object({ id: z.number(), name: z.string() })),
        },
      }),
      (c) => c.json({ users: [{ id: 1, name: "Alice" }] }),
    );

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "get_users", arguments: {} },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("structuredContent");
    expect(text).toContain("Alice");
  });

  it("returns plain text for text responses", async () => {
    const app = new Hono().get("/hello", registerTool("Say hello"), (c) => c.text("Hello, World!"));

    const wrapped = mcp(app, { name: "Test", version: "1.0.0" });

    const res = await wrapped.fetch(
      new Request("http://localhost/mcp", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json, text/event-stream",
        },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "get_hello", arguments: {} },
        }),
      }),
    );

    const text = await res.text();
    expect(text).toContain("Hello, World!");
    expect(text).not.toContain("structuredContent");
  });
});
