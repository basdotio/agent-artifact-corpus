// ripgrep-powered memory-layout risk tracking and #include blast radius.
import { posix } from "node:path";
import { join } from "node:path";
import { CPP_GLOBS, type Config, isHeader, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { stripCode } from "../core/cppText.js";
import { cmpStr, FUNCTION_KINDS, innermost, tryCtagsForFiles, TYPE_KINDS } from "../engines/ctags.js";
import { matchesGlob, readLines } from "../core/paths.js";
import { rgFiles, rgSearch } from "../engines/rg.js";
import { InvalidArgument } from "../core/errors.js";
import { normalizeSymbol } from "./graphGtags.js";

const CONTEXT_RADIUS = 2;

interface RiskRule {
  key: string;
  icon: string;
  label: string;
  explanation: string;
  pattern: RegExp;
}

function rules(name: string): RiskRule[] {
  const n = md.escapeRegex(name);
  return [
    { key: "io", icon: "🌐", label: "raw I/O", explanation: "struct bytes sent/received/persisted directly: size, padding or member order changes break the wire/disk format and peers built from older code",
      pattern: /\b(?:send|sendto|sendmsg|recv|recvfrom|recvmsg|write|read|pwrite|pread|writev|readv|fwrite|fread|ioctl|mmap)\s*\(/ },
    { key: "mem", icon: "🧬", label: "raw memory op", explanation: "memcpy/memmove/memset/memcmp over the object: layout changes shift offsets, and memcmp also compares padding bytes",
      pattern: /\b(?:memcpy|memmove|memset|memcmp|bcopy|bzero|memcpy_s|memmove_s)\s*\(/ },
    { key: "size", icon: "📏", label: "size/offset assumption", explanation: "sizeof/offsetof/alignof values change with the layout; buffers, protocol lengths and array math sized from them shift silently",
      pattern: /\b(?:sizeof|offsetof|alignof|_Alignof)\s*\(/ },
    { key: "cast", icon: "🎭", label: "type punning", explanation: "reinterpret_cast / C-style pointer cast / bit_cast reinterprets raw bytes: the layout must match the producer exactly",
      pattern: new RegExp(`\\breinterpret_cast\\s*<|\\bbit_cast\\s*<|\\(\\s*(?:const\\s+)?(?:struct\\s+)?${n}\\s*(?:const\\s*)?\\*+\\s*\\)`) },
    { key: "pack", icon: "📦", label: "packing/alignment", explanation: "explicit packing or alignment: new members may break alignment assumptions or the ABI",
      pattern: /#\s*pragma\s+pack|__attribute__\s*\(\(\s*(?:packed|aligned)|\balignas\s*\(/ },
    { key: "assert", icon: "✅", label: "layout assertion", explanation: "static_assert on the layout: it must be updated deliberately (good sign, but check the new value)",
      pattern: /\bstatic_assert\s*\(/ },
    { key: "union", icon: "🔀", label: "union aliasing", explanation: "aliased through a union: all members must stay layout-compatible", pattern: /\bunion\b/ },
    { key: "endian", icon: "🔁", label: "byte-order conversion", explanation: "per-field endianness conversion: new or resized fields need matching hton/ntoh handling",
      pattern: /\b(?:hton[sl]|ntoh[sl]|htobe\d+|be\d+toh|htole\d+|le\d+toh|bswap\w*|__builtin_bswap\d+)\s*\(/ },
    { key: "serial", icon: "🗃️", label: "serialization", explanation: "custom (de)serializer: every added/removed member needs matching encode/decode logic and versioning",
      pattern: /\b\w*(?:[Ss]eriali[sz]e|[Mm]arshal|[Ee]ncode|[Dd]ecode)\w*\s*\(/ },
  ];
}

function riskKeys(code: string, rs: RiskRule[]): string[] {
  return rs.filter((r) => r.pattern.test(code)).map((r) => r.key);
}

export async function structRisksReport(cfg: Config, structName: string, pathGlob = ""): Promise<string> {
  const name = normalizeSymbol(structName);
  const rs = rules(name);
  const byKey = new Map(rs.map((r) => [r.key, r]));
  const order = rs.map((r) => r.key);
  const res = await rgSearch(cfg, name, { word: true, fixed: true, context: CONTEXT_RADIUS });
  const title = `### ⚠️ LOW-LEVEL MEMORY USAGES: \`${name}\``;
  const files = res.sortedPaths().filter((p) => matchesGlob(p, pathGlob));
  if (!files.length) return `${title}\n✅ \`${name}\` is not referenced in any C/C++ file` + (pathGlob ? ` matching \`${pathGlob}\`.` : ".");
  const tagsByFile = await tryCtagsForFiles(cfg, files);
  const hits: Array<[string, number, string[], string, string, string]> = [];
  const defs: string[] = [];
  let totalRefs = 0;
  const word = new RegExp(`\\b${md.escapeRegex(name)}\\b`);
  for (const path of files) {
    let lines: string[];
    try {
      lines = readLines(join(cfg.workspaceRoot, path));
    } catch {
      continue;
    }
    const stripped = stripCode(lines);
    const tags = tagsByFile.get(path) ?? [];
    for (const t of tags) if (t.shortName === name && TYPE_KINDS.has(t.kind)) defs.push(`${path}:${t.line}-${t.end}`);
    const matchLines = res.files
      .get(path)!
      .filter((m) => m.isMatch && m.line > 0 && m.line <= lines.length && word.test(stripped[m.line - 1]))
      .map((m) => m.line);
    totalRefs += matchLines.length;
    const direct = new Map<number, string[]>();
    for (const ln of matchLines) {
      const keys = riskKeys(stripped[ln - 1], rs);
      if (keys.length) direct.set(ln, keys);
    }
    for (const ln of matchLines) {
      let keys: string[];
      let how: string;
      if (direct.has(ln)) {
        keys = direct.get(ln)!;
        how = "direct";
      } else {
        if ([...direct.keys()].some((d) => Math.abs(d - ln) <= CONTEXT_RADIUS)) continue;
        keys = [];
        for (let k = Math.max(1, ln - CONTEXT_RADIUS); k <= Math.min(lines.length, ln + CONTEXT_RADIUS); k++) {
          if (k !== ln) for (const x of riskKeys(stripped[k - 1], rs)) if (!keys.includes(x)) keys.push(x);
        }
        if (!keys.length) continue;
        how = "nearby";
      }
      const fn = innermost(tags, ln, FUNCTION_KINDS);
      hits.push([path, ln, keys, how, fn ? fn.qualified : "", lines[ln - 1].trim()]);
    }
  }
  const head = [title];
  if (defs.length) head.push("Defined at: " + defs.slice(0, 3).map((d) => `\`${d}\``).join(", ") + ".");
  if (!hits.length) {
    head.push(`✅ No layout-sensitive operations found among ${md.plural(totalRefs, "reference")}.`);
    return head.join("\n");
  }
  head.push(`Modifying the size, padding or member order of \`${name}\` may break ${md.plural(hits.length, "site")} (out of ${md.plural(totalRefs, "reference")}):`);
  const items = hits.map(([path, ln, keys, how, fn, text], i) => {
    const sorted = [...keys].sort((a, b) => order.indexOf(a) - order.indexOf(b));
    const labels = sorted.map((k) => `${byKey.get(k)!.icon} ${byKey.get(k)!.label}`).join(", ");
    const where = fn ? ` in \`${fn}\`` : "";
    const near = how === "nearby" ? " (operation within ±2 lines)" : "";
    return `${i + 1}. \`${path}:${ln}\`${where} — ${labels}${near}\n   ${md.codeSpan(text)}`;
  });
  const body = md.truncateList(items, cfg.maxResults, "risk sites", "Use path_glob to focus.");
  const used = [...new Set(hits.flatMap((h) => h[2]))].sort((a, b) => order.indexOf(a) - order.indexOf(b));
  const legend = ["", "**Why it matters:**", ...used.map((k) => `- ${byKey.get(k)!.icon} **${byKey.get(k)!.label}:** ${byKey.get(k)!.explanation}.`)];
  return [...head, "", ...body, ...legend].join("\n");
}

export async function track_struct_risks(args: { struct_name: string; path_glob?: string }): Promise<string> {
  return structRisksReport(loadConfig(), args.struct_name, args.path_glob ?? "");
}

// --------------------------------------------------------------------------- blast radius
const INCLUDE_RX = /^\s*#\s*include\s*[<"]([^">]+)[">]/;

function normalizeInclude(p: string): string {
  const parts = p.replace(/\\/g, "/").split("/").filter((x) => x !== "" && x !== ".");
  while (parts.length && parts[0] === "..") parts.shift();
  return parts.join("/");
}

function includeMatches(included: string, headerRel: string | null, headerName: string, includer: string): boolean {
  const inc = normalizeInclude(included);
  if (!inc) return false;
  if (headerRel === null) return inc === headerName || inc.endsWith("/" + headerName);
  if (headerRel === inc || headerRel.endsWith("/" + inc)) return true;
  if (included.startsWith(".")) return posix.normalize(posix.join(posix.dirname(includer), included)) === headerRel;
  return false;
}

async function directIncluders(cfg: Config, headerRel: string | null, headerName: string, basenames: Map<string, string[]>): Promise<Array<[string, number, string, boolean]>> {
  const base = headerName.split("/").pop()!;
  const pattern = `^\\s*#\\s*include\\s*["<]([^">]*/)?${md.escapeRegex(base)}[">]`;
  const res = await rgSearch(cfg, pattern, { globs: CPP_GLOBS });
  const out: Array<[string, number, string, boolean]> = [];
  const ambiguousBase = (basenames.get(base) ?? []).length > 1;
  for (const m of res.matches()) {
    const im = INCLUDE_RX.exec(m.text);
    if (!im) continue;
    const inc = im[1];
    if (!includeMatches(inc, headerRel, headerName, m.path)) continue;
    if (m.path === headerRel) continue;
    const amb = ambiguousBase && !normalizeInclude(inc).includes("/");
    out.push([m.path, m.line, m.text.trim(), amb]);
  }
  return out;
}

export async function blastRadiusReport(cfg: Config, headerFilename: string, transitiveDepth = 2): Promise<string> {
  const raw = (headerFilename ?? "").trim().replace(/\\/g, "/");
  if (!raw || raw.startsWith("-") || /["<>\n]/.test(raw)) {
    throw new InvalidArgument(`\`${headerFilename}\` is not a valid header name.`, "Pass e.g. `packet.hpp` or `src/net/packet.hpp`.");
  }
  const depth = Math.max(1, Math.min(Math.trunc(transitiveDepth || 1), 3));
  const allFiles = await rgFiles(cfg);
  const basenames = new Map<string, string[]>();
  for (const f of allFiles) {
    const b = f.split("/").pop()!;
    if (!basenames.has(b)) basenames.set(b, []);
    basenames.get(b)!.push(f);
  }
  const norm = normalizeInclude(raw);
  let headerRel: string | null = allFiles.includes(norm) ? norm : null;
  if (headerRel === null) {
    const cands = allFiles.filter((f) => f === norm || f.endsWith("/" + norm));
    if (cands.length === 1) headerRel = cands[0];
  }
  const title = `### 💥 BLAST RADIUS: \`${headerRel ?? norm}\``;
  const direct = await directIncluders(cfg, headerRel, norm, basenames);
  if (!direct.length) {
    const note = headerRel ? "" : " (header not found in the workspace; matched by name)";
    return `${title}\n✅ No C/C++ file includes \`${norm}\`${note}.`;
  }
  const directFiles = [...new Set(direct.map((d) => d[0]))].sort(cmpStr);
  const levels: string[][] = [directFiles];
  const seen = new Set(directFiles);
  if (headerRel) seen.add(headerRel);
  let frontier = directFiles.filter(isHeader);
  for (let d = 0; d < depth - 1; d++) {
    const nxt: string[] = [];
    for (const h of frontier) {
      for (const [p] of await directIncluders(cfg, h, h, basenames)) {
        if (!seen.has(p)) {
          seen.add(p);
          nxt.push(p);
        }
      }
    }
    if (!nxt.length) break;
    levels.push([...nxt].sort(cmpStr));
    frontier = nxt.filter(isHeader);
  }
  const affected = [...new Set(levels.flat())].sort(cmpStr);
  const sources = affected.filter((f) => !isHeader(f));
  const tuTotal = allFiles.filter((f) => !isHeader(f)).length;
  const share = tuTotal ? `${md.formatFixed0((100 * sources.length) / tuTotal)}%` : "n/a";
  const out = [
    title,
    `- **Direct includers:** ${md.plural(directFiles.length, "file")}` +
      (levels.length > 1 ? `; **transitive:** ${md.plural(affected.length - directFiles.length, "more file")} (depth ${levels.length})` : ""),
    `- **Translation units affected:** ${sources.length} of ${tuTotal} source files (${share}); headers affected: ${affected.length - sources.length}`,
  ];
  const groups = new Map<string, number>();
  for (const f of affected) {
    const d = posix.dirname(f) || ".";
    groups.set(d, (groups.get(d) ?? 0) + 1);
  }
  const top = [...groups.entries()].sort((a, b) => b[1] - a[1] || cmpStr(a[0], b[0]));
  out.push("- **By directory:** " + top.slice(0, 10).map(([d, n]) => `\`${d}/\` (${n})`).join(", ") + (top.length > 10 ? " …" : ""));
  if (direct.some((d) => d[3])) {
    out.push(`- ⚠️ Some includes use the bare name \`${norm.split("/").pop()}\`, which matches several headers in the repo; those hits are marked (ambiguous).`);
  }
  const sortedDirect = [...direct].sort((a, b) => cmpStr(a[0], b[0]) || a[1] - b[1] || cmpStr(a[2], b[2]) || Number(a[3]) - Number(b[3]));
  const items = sortedDirect.map(([path, ln, inc, amb]) => `- \`${path}:${ln}\` ${md.codeSpan(inc)}` + (amb ? " (ambiguous)" : ""));
  out.push("", "**Direct includers:**", ...md.truncateList(items, cfg.maxResults, "includers"));
  if (levels.length > 1) {
    const trans = levels.slice(1).flatMap((lvl, i) => lvl.map((p) => `- \`${p}\` (depth ${i + 2})`));
    out.push("", "**Transitive includers:**", ...md.truncateList(trans, cfg.maxResults, "transitive includers"));
  }
  if (sources.length >= 20 || (sources.length >= 5 && tuTotal && sources.length / tuTotal >= 0.25)) {
    out.push("\n_High-fan-out header: macro, inline, template or layout changes here recompile and can alter many modules._");
  }
  return out.join("\n");
}

export async function get_include_blast_radius(args: { header_filename: string; transitive_depth?: number }): Promise<string> {
  return blastRadiusReport(loadConfig(), args.header_filename, args.transitive_depth ?? 2);
}
