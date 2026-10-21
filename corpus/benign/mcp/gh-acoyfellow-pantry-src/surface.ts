import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { PantryClient, automationTokenAuthentication } from './client.ts';

export const DEFAULT_URL = 'https://pantry.coey.dev';
export function tokenFile(): string {
  const terrariumHome = process.env.TERRARIUM_HOME?.trim();
  return terrariumHome
    ? join(terrariumHome, 'pantry-token.secret')
    : join(homedir(), '.terrarium', 'pantry-token.secret');
}

export function loadAutomationToken(): string | undefined {
  const fromEnv = process.env.PANTRY_TOKEN?.trim();
  if (fromEnv) return fromEnv;
  try {
    return readFileSync(tokenFile(), 'utf8').trim() || undefined;
  } catch {
    return undefined;
  }
}

export const loadToken = loadAutomationToken;

export function resolvedUrl(): string {
  return (process.env.PANTRY_URL?.trim() || DEFAULT_URL).replace(/\/$/, '');
}

export function makeFetch(): typeof fetch {
  const pin = process.env.PANTRY_RESOLVE?.trim();
  if (!pin) return fetch;
  const [host, ip] = pin.split(':');
  if (!host || !ip) throw new Error(`PANTRY_RESOLVE must be "host:ip" (got "${pin}")`);
  return ((input: RequestInfo | URL, init?: RequestInit) => {
    const original = new URL(typeof input === 'string' ? input : input.toString());
    if (original.hostname !== host) return fetch(input, init);
    const pinned = new URL(original);
    pinned.hostname = ip;
    const headers = new Headers(init?.headers as ConstructorParameters<typeof Headers>[0]);
    headers.set('host', host);
    return fetch(pinned, { ...init, headers, tls: { serverName: host } } as RequestInit);
  }) as typeof fetch;
}

export function describeError(err: unknown, url: string): string {
  const code = (err as { code?: string } | undefined)?.code ?? '';
  const message = err instanceof Error ? err.message : String(err);
  if (
    !/ConnectionRefused|connection refused|unable to connect|failed to fetch|ENOTFOUND|EAI_AGAIN/i.test(
      `${code} ${message}`,
    )
  )
    return message;
  return [
    `Could not reach pantry at ${url} (${code || 'connect failure'}).`,
    '',
    'A stale local DNS resolver can make plain fetch fail even when pantry is live.',
    'Workarounds:',
    '  PANTRY_RESOLVE="pantry.coey.dev:<ip>" with a fresh IP from dig +short pantry.coey.dev A',
    '  PANTRY_URL="https://<reachable-host-or-ip>"',
  ].join('\n');
}

export function browserSsoUnavailableMessage(url = resolvedUrl()): string {
  return [
    `Browser SSO login/session handoff is not implemented for the Pantry CLI at ${url}.`,
    'Sign in to the Pantry deployment browser management app with SSO for employee access.',
    `For non-interactive automation, explicitly configure PANTRY_TOKEN or ${tokenFile()} with a scoped credential.`,
  ].join('\n');
}

export function makeClient(fetchImpl = makeFetch()): { client: PantryClient; url: string } {
  const url = resolvedUrl();
  const token = loadAutomationToken();
  if (!token)
    throw new Error(
      ['Pantry authentication is not configured.', browserSsoUnavailableMessage(url)].join('\n\n'),
    );
  return {
    client: new PantryClient({
      url,
      authentication: automationTokenAuthentication(token),
      fetch: fetchImpl,
    }),
    url,
  };
}

export const RUN_CAVEAT =
  "pantry run is NOT a security sandbox; running fetched code is the caller's decision and risk. Untrusted recipes need a real isolate.";
