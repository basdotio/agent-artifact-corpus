import { lookup } from 'node:dns/promises';
import { BlockList, isIP } from 'node:net';
import type { Page, Route } from 'playwright-core';

type IpFamily = 4 | 6;

const ALLOW_PRIVATE_NETWORK_ENV = 'ALLOW_PRIVATE_NETWORK';
const TRUTHY_ENV_VALUES = new Set(['1', 'true', 'yes', 'on']);

interface LookupAddress {
  address: string;
  family: IpFamily;
}

export type HostnameResolver = (hostname: string) => Promise<LookupAddress[]>;

interface UrlGuardOptions {
  allowPrivateNetwork?: boolean;
}

const ALLOWED_PROTOCOLS = new Set(['http:', 'https:']);
const protectedPages = new WeakMap<Page, Promise<void>>();

const blockedIpRanges = new BlockList();
blockedIpRanges.addSubnet('0.0.0.0', 8, 'ipv4');
blockedIpRanges.addSubnet('10.0.0.0', 8, 'ipv4');
blockedIpRanges.addSubnet('100.64.0.0', 10, 'ipv4');
blockedIpRanges.addSubnet('127.0.0.0', 8, 'ipv4');
blockedIpRanges.addSubnet('169.254.0.0', 16, 'ipv4');
blockedIpRanges.addSubnet('172.16.0.0', 12, 'ipv4');
blockedIpRanges.addSubnet('192.168.0.0', 16, 'ipv4');
blockedIpRanges.addSubnet('::', 128, 'ipv6');
blockedIpRanges.addSubnet('::1', 128, 'ipv6');
blockedIpRanges.addSubnet('fc00::', 7, 'ipv6');
blockedIpRanges.addSubnet('fe80::', 10, 'ipv6');

function normalizeHostname(hostname: string): string {
  return hostname.startsWith('[') && hostname.endsWith(']')
    ? hostname.slice(1, -1)
    : hostname;
}

function describeBlockedAddress(address: string): Error {
  return new Error(`Blocked URL target: resolved IP ${address} is not allowed`);
}

function resolveAllowPrivateNetwork(options?: UrlGuardOptions): boolean {
  if (typeof options?.allowPrivateNetwork === 'boolean') {
    return options.allowPrivateNetwork;
  }

  const envValue = process.env[ALLOW_PRIVATE_NETWORK_ENV]?.trim().toLowerCase();
  return envValue !== undefined && TRUTHY_ENV_VALUES.has(envValue);
}

export function isPrivateNetworkAllowed(options?: UrlGuardOptions): boolean {
  return resolveAllowPrivateNetwork(options);
}

function assertAddressIsAllowed(
  address: string,
  family: IpFamily,
  options?: UrlGuardOptions,
): void {
  if (resolveAllowPrivateNetwork(options)) {
    return;
  }

  if (blockedIpRanges.check(address, family === 4 ? 'ipv4' : 'ipv6')) {
    throw describeBlockedAddress(address);
  }
}

async function defaultResolveHostname(hostname: string): Promise<LookupAddress[]> {
  const results = await lookup(hostname, { all: true, verbatim: true });
  return results
    .filter((result): result is LookupAddress => result.family === 4 || result.family === 6)
    .map((result) => ({
      address: result.address,
      family: result.family,
    }));
}

async function resolveAndValidateHostname(
  hostname: string,
  resolveHostname: HostnameResolver,
  options?: UrlGuardOptions,
): Promise<void> {
  const addresses = await resolveHostname(hostname);

  if (addresses.length === 0) {
    throw new Error(`Blocked URL target: hostname ${hostname} did not resolve to an IP address`);
  }

  for (const result of addresses) {
    assertAddressIsAllowed(result.address, result.family, options);
  }
}

function parseUrl(rawUrl: string): URL {
  let parsedUrl: URL;

  try {
    parsedUrl = new URL(rawUrl);
  } catch {
    throw new Error(`Invalid URL: ${rawUrl}`);
  }

  if (!ALLOWED_PROTOCOLS.has(parsedUrl.protocol)) {
    throw new Error(`Blocked URL target: unsupported protocol ${parsedUrl.protocol}`);
  }

  return parsedUrl;
}

async function assertParsedUrlIsSafe(
  parsedUrl: URL,
  resolveHostname: HostnameResolver,
  options?: UrlGuardOptions,
): Promise<void> {
  const hostname = normalizeHostname(parsedUrl.hostname);
  const family = isIP(hostname);

  if (family === 4 || family === 6) {
    assertAddressIsAllowed(hostname, family, options);
    return;
  }

  await resolveAndValidateHostname(hostname, resolveHostname, options);
}

export async function assertUrlIsSafe(
  rawUrl: string,
  resolveHostname: HostnameResolver = defaultResolveHostname,
  options?: UrlGuardOptions,
): Promise<URL> {
  const parsedUrl = parseUrl(rawUrl);
  await assertParsedUrlIsSafe(parsedUrl, resolveHostname, options);
  return parsedUrl;
}

async function allowOrBlockRequest(
  route: Pick<Route, 'request' | 'abort' | 'continue'>,
  validateUrl: (url: string) => Promise<void>,
): Promise<void> {
  try {
    await validateUrl(route.request().url());
    await route.continue();
  } catch {
    await route.abort('blockedbyclient');
  }
}

export async function installUrlProtection(
  page: Pick<Page, 'route'>,
  resolveHostname: HostnameResolver = defaultResolveHostname,
  options?: UrlGuardOptions,
): Promise<void> {
  const existingInstallation = protectedPages.get(page as Page);

  if (existingInstallation) {
    await existingInstallation;
    return;
  }

  const validateUrl = async (url: string): Promise<void> => {
    const parsedUrl = parseUrl(url);
    const hostname = normalizeHostname(parsedUrl.hostname);
    const family = isIP(hostname);

    if (family === 4 || family === 6) {
      assertAddressIsAllowed(hostname, family, options);
      return;
    }

    await assertParsedUrlIsSafe(parsedUrl, resolveHostname, options);
  };

  const installation = page.route('**/*', async (route) => {
    await allowOrBlockRequest(route, validateUrl);
  });

  protectedPages.set(page as Page, installation);
  await installation;
}
