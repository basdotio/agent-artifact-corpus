function envBool(key: string, fallback: boolean): boolean {
  const raw = process.env[key];
  if (raw === undefined || raw === '') return fallback;
  return ['1', 'true', 'yes', 'on'].includes(raw.toLowerCase());
}

function envInt(key: string, fallback: number): number {
  const raw = process.env[key];
  if (!raw) return fallback;
  const n = Number.parseInt(raw, 10);
  return Number.isFinite(n) ? n : fallback;
}

export const config = {
  maxPages: envInt('MAX_PAGES', 20),
  requestTimeout: envInt('REQUEST_TIMEOUT', 30_000),
  maxDepth: envInt('MAX_DEPTH', 2),
  screenshot: envBool('SCREENSHOT', true),
  mobileView: envBool('MOBILE_VIEW', true),
  tabletView: envBool('TABLET_VIEW', true),
  desktopView: envBool('DESKTOP_VIEW', true),
  userAgent: process.env.USER_AGENT ?? 'WebsiteAnalyzerMCP/1.0',
  respectRobotsTxt: envBool('RESPECT_ROBOTS_TXT', true),
  maxResponseSize: envInt('MAX_RESPONSE_SIZE', 5_000_000),
};

export function viewportWidthsFromConfig(): number[] {
  const widths: number[] = [];
  if (config.mobileView) widths.push(375);
  if (config.tabletView) widths.push(768, 1024);
  if (config.desktopView) widths.push(1440, 1920);
  return widths.length ? widths : [375, 768, 1024, 1440, 1920];
}
