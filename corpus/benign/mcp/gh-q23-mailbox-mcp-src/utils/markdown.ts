/**
 * Escapes user-controlled strings for safe use inside Markdown tables and inline content.
 * Replaces pipe characters (|) and backticks (`) that would break table formatting,
 * and collapses newlines to a space to prevent row injection.
 */
export function escapeMd(str: string): string {
  return str.replace(/[|`\r\n]/g, (c) => (c === "\r" || c === "\n" ? " " : `\\${c}`));
}
