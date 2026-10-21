import { lookup } from 'node:dns/promises';
import net from 'node:net';

const BLOCKED_HOSTNAMES = new Set([
  'localhost',
  'metadata.google.internal',
  'metadata.google',
]);

export class SsrfError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SsrfError';
  }
}

export async function assertSafeUrl(rawUrl: string): Promise<URL> {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    throw new SsrfError(`Invalid URL: ${rawUrl}`);
  }

  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new SsrfError(`Blocked protocol: ${url.protocol}`);
  }

  const hostname = url.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (BLOCKED_HOSTNAMES.has(hostname) || hostname.endsWith('.localhost')) {
    throw new SsrfError(`Blocked hostname: ${hostname}`);
  }

  if (net.isIP(hostname)) {
    if (isPrivateIp(hostname)) {
      throw new SsrfError(`Blocked private IP: ${hostname}`);
    }
    return url;
  }

  let addresses: Array<{ address: string }>;
  try {
    addresses = await lookup(hostname, { all: true });
  } catch {
    throw new SsrfError(`Unable to resolve host: ${hostname}`);
  }

  for (const { address } of addresses) {
    if (isPrivateIp(address)) {
      throw new SsrfError(`Blocked resolved private IP for ${hostname}: ${address}`);
    }
  }

  return url;
}

export function isPrivateIp(ip: string): boolean {
  const v = ip.toLowerCase();

  if (v === '::1' || v === '0.0.0.0') return true;
  if (v.startsWith('fc') || v.startsWith('fd') || v.startsWith('fe80:')) return true;

  const m = v.match(/^(\d+)\.(\d+)\.(\d+)\.(\d+)$/);
  if (!m) return false;
  const [a, b] = [Number(m[1]), Number(m[2])];

  if (a === 10) return true;
  if (a === 127) return true;
  if (a === 0) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 100 && b >= 64 && b <= 127) return true; // CGNAT
  return false;
}
