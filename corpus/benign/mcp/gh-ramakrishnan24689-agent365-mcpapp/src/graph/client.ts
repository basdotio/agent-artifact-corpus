/**
 * Graph client — abstraction layer for Microsoft Graph API calls.
 * Switches between mock and live data based on USE_MOCK_DATA env var.
 */
import { exchangeTokenForGraph } from "../../auth.js";

export function useMockData(): boolean {
  return process.env.USE_MOCK_DATA !== "false";
}

/**
 * Make an authenticated Graph API call.
 * Returns parsed JSON response.
 */
export async function graphFetch<T>(
  endpoint: string,
  incomingToken: string | undefined,
  options?: { method?: string; body?: unknown },
): Promise<T> {
  if (!incomingToken) {
    throw new Error("No auth token available for Graph API call");
  }

  const graphToken = await exchangeTokenForGraph(incomingToken);
  const url = endpoint.startsWith("http")
    ? endpoint
    : `https://graph.microsoft.com/beta${endpoint}`;

  const response = await fetch(url, {
    method: options?.method ?? "GET",
    headers: {
      Authorization: `Bearer ${graphToken}`,
      "Content-Type": "application/json",
    },
    body: options?.body ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Graph API ${response.status}: ${errorText}`);
  }

  // Handle 204 No Content (block/unblock/reassign actions)
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
