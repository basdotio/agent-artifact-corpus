import { describe, expect, test } from "bun:test";
import {
  DEFAULT_SERVER_CONFIG,
  isBearerTokenAuthorized,
  resolveServerConfig,
} from "./protocol.js";

describe("MCP server config helpers", () => {
  test("defaults to local-only host/port and auth disabled", () => {
    expect(DEFAULT_SERVER_CONFIG.host).toBe("127.0.0.1");
    expect(DEFAULT_SERVER_CONFIG.port).toBe(3838);
    expect(DEFAULT_SERVER_CONFIG.auth.enabled).toBe(false);
    expect(DEFAULT_SERVER_CONFIG.auth.token).toBeUndefined();
  });

  test("applies CLI overrides for host/port and auth token", () => {
    const resolved = resolveServerConfig(
      {
        host: "127.0.0.1",
        port: 3838,
        auth: {
          enabled: false,
        },
      },
      {
        host: "0.0.0.0",
        port: 4848,
        authToken: "top-secret",
      },
    );

    expect(resolved.host).toBe("0.0.0.0");
    expect(resolved.port).toBe(4848);
    expect(resolved.auth.enabled).toBe(true);
    expect(resolved.auth.token).toBe("top-secret");
  });
});

describe("bearer auth", () => {
  test("allows requests when auth is disabled", () => {
    const headers = new Headers();
    expect(
      isBearerTokenAuthorized(headers, {
        enabled: false,
      }),
    ).toBe(true);
  });

  test("rejects missing bearer token when auth is enabled", () => {
    const headers = new Headers();
    expect(
      isBearerTokenAuthorized(headers, {
        enabled: true,
        token: "abc",
      }),
    ).toBe(false);
  });

  test("accepts exact bearer token when auth is enabled", () => {
    const headers = new Headers({
      authorization: "Bearer abc",
    });
    expect(
      isBearerTokenAuthorized(headers, {
        enabled: true,
        token: "abc",
      }),
    ).toBe(true);
  });
});
