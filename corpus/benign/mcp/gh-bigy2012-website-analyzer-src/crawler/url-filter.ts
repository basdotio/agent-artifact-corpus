export function isSameOrigin(base: string, candidate: string): boolean {
  try {
    const a = new URL(base);
    const b = new URL(candidate, base);
    return a.origin === b.origin;
  } catch {
    return false;
  }
}

export function normalizeUrl(href: string, base: string): string | null {
  try {
    const url = new URL(href, base);
    url.hash = '';
    if (!['http:', 'https:'].includes(url.protocol)) return null;
    return url.toString();
  } catch {
    return null;
  }
}

export function shouldSkipPath(pathname: string): boolean {
  return /\.(pdf|zip|png|jpe?g|gif|svg|webp|mp4|mp3|woff2?|css|js)$/i.test(pathname);
}
