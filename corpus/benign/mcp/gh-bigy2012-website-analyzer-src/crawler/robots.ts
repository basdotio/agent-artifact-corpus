import { config } from '../config.js';

export interface RobotsDecision {
  allowed: boolean;
  reason: string;
}

/**
 * Minimal robots.txt check for v0.1 (single-page).
 * Fetches /robots.txt when RESPECT_ROBOTS_TXT=true and blocks Disallow matches for User-agent: *.
 */
export async function checkRobotsTxt(targetUrl: string): Promise<RobotsDecision> {
  if (!config.respectRobotsTxt) {
    return { allowed: true, reason: 'RESPECT_ROBOTS_TXT=false' };
  }

  let url: URL;
  try {
    url = new URL(targetUrl);
  } catch {
    return { allowed: false, reason: 'invalid url' };
  }

  const robotsUrl = `${url.origin}/robots.txt`;
  try {
    const res = await fetch(robotsUrl, {
      headers: { 'User-Agent': config.userAgent },
      signal: AbortSignal.timeout(Math.min(config.requestTimeout, 10_000)),
    });
    if (!res.ok) {
      return { allowed: true, reason: `robots.txt HTTP ${res.status}` };
    }
    const body = await res.text();
    const disallows = parseDisallows(body);
    const path = url.pathname || '/';
    for (const rule of disallows) {
      if (pathStartsWith(path, rule)) {
        return { allowed: false, reason: `Disallow: ${rule}` };
      }
    }
    return { allowed: true, reason: 'allowed by robots.txt' };
  } catch (error) {
    return {
      allowed: true,
      reason: `robots.txt unreachable (${error instanceof Error ? error.message : String(error)})`,
    };
  }
}

function parseDisallows(body: string): string[] {
  const lines = body.split(/\r?\n/);
  let inStar = false;
  const rules: string[] = [];
  for (const line of lines) {
    const cleaned = line.replace(/#.*$/, '').trim();
    if (!cleaned) continue;
    const [key, ...rest] = cleaned.split(':');
    const value = rest.join(':').trim();
    const k = key.toLowerCase();
    if (k === 'user-agent') {
      inStar = value === '*';
      continue;
    }
    if (inStar && k === 'disallow' && value) {
      rules.push(value);
    }
  }
  return rules;
}

function pathStartsWith(path: string, rule: string): boolean {
  if (rule === '/') return true;
  return path === rule || path.startsWith(rule.endsWith('/') ? rule : `${rule}`);
}
