// Lightweight C++ text utilities: comment/string stripping (length preserving) and doc-comment extraction.

const RAW_PREFIX = /(?:u8|u|U|L)?R"([^()\\\s]{0,16})\(/y;

function isWord(ch: string | undefined): boolean {
  return !!ch && /^[A-Za-z0-9_]$/.test(ch);
}

/** Blank out comments and the contents of string/char literals, preserving every column position. */
export function stripCode(lines: string[]): string[] {
  const out: string[] = [];
  let inBlock = false;
  let rawEnd: string | null = null;
  for (const line of lines) {
    const chars = line.split("");
    const n = chars.length;
    let i = 0;
    while (i < n) {
      if (rawEnd !== null) {
        const j = line.indexOf(rawEnd, i);
        if (j < 0) {
          for (let k = i; k < n; k++) chars[k] = " ";
          i = n;
          break;
        }
        for (let k = i; k < j; k++) chars[k] = " ";
        i = j + rawEnd.length;
        rawEnd = null;
        continue;
      }
      if (inBlock) {
        const j = line.indexOf("*/", i);
        if (j < 0) {
          for (let k = i; k < n; k++) chars[k] = " ";
          i = n;
          break;
        }
        for (let k = i; k < j + 2; k++) chars[k] = " ";
        i = j + 2;
        inBlock = false;
        continue;
      }
      const c = line[i];
      const nxt = i + 1 < n ? line[i + 1] : "";
      if (c === "/" && nxt === "/") {
        for (let k = i; k < n; k++) chars[k] = " ";
        break;
      }
      if (c === "/" && nxt === "*") {
        chars[i] = chars[i + 1] = " ";
        i += 2;
        inBlock = true;
        continue;
      }
      if ("uULR".includes(c) && (i === 0 || !isWord(line[i - 1]))) {
        RAW_PREFIX.lastIndex = i;
        const m = RAW_PREFIX.exec(line);
        if (m) {
          rawEnd = ")" + m[1] + '"';
          i = i + m[0].length;
          continue;
        }
      }
      if (c === '"') {
        let j = i + 1;
        while (j < n && line[j] !== '"') j += line[j] === "\\" ? 2 : 1;
        for (let k = i + 1; k < Math.min(j, n); k++) chars[k] = " ";
        i = j + 1;
        continue;
      }
      if (c === "'") {
        let t = i;
        while (t > 0 && isWord(line[t - 1])) t--;
        if (t < i && line[t] >= "0" && line[t] <= "9") {
          i += 1; // digit separator, e.g. 1'000'000
          continue;
        }
        let j = i + 1;
        while (j < n && line[j] !== "'") j += line[j] === "\\" ? 2 : 1;
        for (let k = i + 1; k < Math.min(j, n); k++) chars[k] = " ";
        i = j + 1;
        continue;
      }
      i += 1;
    }
    out.push(chars.join(""));
  }
  return out;
}

const SKIP_ABOVE = /^\s*(template\s*<.*|\[\[.*\]\]\s*|__attribute__.*|[A-Z][A-Z0-9_]*(\(.*\))?\s*)$/;
const TRAILING_DOC = /(\/\/\/<|\/\/!<|\/\*\*<)(.*?)(\*\/)?\s*$/;

function cleanCommentLine(text: string): string {
  let t = text.trim();
  for (const marker of ["/**", "/*!", "/*", "///", "//!", "//"]) {
    if (t.startsWith(marker)) {
      t = t.slice(marker.length);
      break;
    }
  }
  if (t.endsWith("*/")) t = t.slice(0, -2);
  t = t.trim();
  if (t.startsWith("*") && !t.startsWith("*/")) t = t.slice(1).trim();
  return t.replace(/\s+$/u, "");
}

export function extractLeadingComment(lines: string[], defIdx: number, maxLines = 40): string[] {
  if (!(defIdx >= 0 && defIdx < lines.length)) return [];
  const m = TRAILING_DOC.exec(lines[defIdx]);
  const trailing = m && m[2].trim() ? [m[2].trim()] : [];
  let i = defIdx - 1;
  let skipped = 0;
  while (i >= 0 && skipped < 3 && SKIP_ABOVE.test(lines[i]) && !/^(\/\/|\/\*|\*)/.test(lines[i].trim())) {
    if (!lines[i].trim()) break;
    i--;
    skipped++;
  }
  if (i < 0) return trailing;
  let collected: string[] = [];
  const stripped = lines[i].trim();
  if (stripped.endsWith("*/")) {
    let j = i;
    let found = false;
    while (j >= 0 && defIdx - j <= maxLines) {
      collected.push(lines[j]);
      if (lines[j].includes("/*")) {
        found = true;
        break;
      }
      j--;
    }
    if (!found || j < 0) return trailing;
    collected.reverse();
  } else if (stripped.startsWith("//")) {
    let j = i;
    while (j >= 0 && lines[j].trim().startsWith("//") && defIdx - j <= maxLines) {
      collected.push(lines[j]);
      j--;
    }
    collected.reverse();
  } else {
    return trailing;
  }
  const cleaned = collected.map(cleanCommentLine);
  while (cleaned.length && !cleaned[0]) cleaned.shift();
  while (cleaned.length && !cleaned[cleaned.length - 1]) cleaned.pop();
  collected = cleaned;
  return collected.length ? collected : trailing;
}

/** First '(' at/after start and its matching ')'. */
export function balancedParens(code: string, start = 0): [number, number] | null {
  const open = code.indexOf("(", start);
  if (open < 0) return null;
  let depth = 0;
  for (let k = open; k < code.length; k++) {
    if (code[k] === "(") depth++;
    else if (code[k] === ")") {
      depth--;
      if (depth === 0) return [open, k];
    }
  }
  return [open, code.length];
}
