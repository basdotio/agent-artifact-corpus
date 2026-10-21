// track_lock_order: repository-wide lock-acquisition order, potential deadlock cycles, locks held across blocking
// calls. Twin of staticsight-py/src/staticsight/tools/lock_order.py (byte-identical output).
import { join } from "node:path";
import { type Config, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { stripCode } from "../core/cppText.js";
import { StaticSightError } from "../core/errors.js";
import { LOCK_TRIGGERS, LockWalker, lineEvents, RECURSIVE_KINDS } from "../core/locks.js";
import { matchesGlob, readLines } from "../core/paths.js";
import { cmpStr, FUNCTION_KINDS, tryCtagsForFiles } from "../engines/ctags.js";
import { rgSearch } from "../engines/rg.js";

const BLOCKING = new RegExp(
  "\\b(send|sendto|sendmsg|recv|recvfrom|recvmsg|connect|accept|select|poll|epoll_wait|fopen|fread|fwrite|fflush|" +
    "sleep|usleep|nanosleep|Sleep|SleepEx|WaitForSingleObject|WaitForSingleObjectEx|WaitForMultipleObjects|" +
    "ReadFile|WriteFile|DeviceIoControl|CreateFileW?|CreateFileA|WinHttpSendRequest|WinHttpReceiveResponse|" +
    "sleep_for|sleep_until)\\s*\\(",
);
const CALL = /\b([A-Za-z_]\w*)\s*\(/g;
const COND_BEFORE = /\b(?:if|else|for|while|case|switch|default)\b|\?/;
const BRACELESS_HEAD = /^\s*(?:\}\s*)?(?:(?:else\s+)?if\s*\(.*\)|for\s*\(.*\)|while\s*\(.*\)|else)\s*$/;

/** The acquisition on line n is guarded: a condition before it on the line, or a brace-less if/else/loop above. */
export function conditional(stripped: string[], n: number, col: number): boolean {
  if (COND_BEFORE.test(stripped[n - 1].slice(0, col))) return true;
  let k = n - 2;
  while (k >= 0 && !stripped[k].trim()) k--;
  return k >= 0 && BRACELESS_HEAD.test(stripped[k]);
}
const NOT_CALLS = new Set([
  "if", "for", "while", "switch", "return", "sizeof", "alignof", "decltype", "static_cast", "reinterpret_cast",
  "const_cast", "dynamic_cast", "catch", "throw", "noexcept", "defined", "static_assert", "typeid", "alignas",
  "assert", "new", "delete", "operator",
]);
const MAX_CYCLE = 4;

interface Edge {
  first: string;
  second: string;
  path: string;
  fn: string;
  lineFirst: number;
  lineSecond: number;
  via: string;
}

interface Fn {
  name: string;
  qualified: string;
  path: string;
  cls: string;
  acquired: Map<string, [number, string, boolean]>; // key -> (line, kind, unconditional)
}

type Blocking = [string, string, number, string, string[]];
type SelfRe = [string, string, number, string, string];

/** Bare member-like names are qualified with the enclosing class, so `m_lock` of two classes stays distinct. */
function key(mx: string, cls: string): string {
  return cls && /^[A-Za-z_]\w*$/.test(mx) ? `${cls}::${mx}` : mx;
}

function clsOf(scope: string): string {
  return scope ? scope.split("::").pop()! : "";
}

function cmpTuple(a: Array<string | number | string[]>, b: Array<string | number | string[]>): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const x = a[i];
    const y = b[i];
    let c: number;
    if (typeof x === "number" && typeof y === "number") c = x - y;
    else if (Array.isArray(x) && Array.isArray(y)) c = cmpTuple(x, y);
    else c = cmpStr(String(x), String(y));
    if (c) return c;
  }
  return a.length - b.length;
}

export async function analyse(cfg: Config, pathGlob = "") {
  const res = await rgSearch(cfg, LOCK_TRIGGERS);
  const files = res.sortedPaths().filter((p) => !pathGlob || matchesGlob(p, pathGlob));
  const tagsByFile = await tryCtagsForFiles(cfg, files);
  const fns: Fn[] = [];
  const edges: Edge[] = [];
  const blocking: Blocking[] = [];
  const calls: Array<[Fn, number, string, Array<[string, number, string]>]> = [];
  const selfre: SelfRe[] = [];
  for (const path of files) {
    let stripped: string[];
    try {
      stripped = stripCode(readLines(join(cfg.workspaceRoot, path)));
    } catch (e) {
      if (e instanceof StaticSightError) continue;
      throw e;
    }
    const funcs = (tagsByFile.get(path) ?? []).filter((t) => FUNCTION_KINDS.has(t.kind) && t.end).sort((a, b) => a.line - b.line);
    for (const t of funcs) {
      const cls = clsOf(t.scope);
      const f: Fn = { name: t.shortName, qualified: t.qualified, path, cls, acquired: new Map() };
      fns.push(f);
      const walker = new LockWalker();
      for (let n = t.line; n <= Math.min(t.end, stripped.length); n++) {
        const code = stripped[n - 1];
        walker.step(code, n, (e, held) => {
          const newKeys = e.mutexes.map((m) => key(m, f.cls));
          const top = walker.depth <= 1 && !conditional(stripped, n, e.col);
          for (const k of newKeys) {
            const prev = f.acquired.get(k);
            if (prev === undefined || (top && !prev[2])) f.acquired.set(k, [n, e.kind, top]);
          }
          for (const h of held) {
            for (const hm of h.mutexes) {
              const hk = key(hm, f.cls);
              for (const k of newKeys) {
                if (hk === k) {
                  if (!RECURSIVE_KINDS.has(e.kind) && !RECURSIVE_KINDS.has(h.kind)) selfre.push([path, f.qualified, n, k, ""]);
                } else edges.push({ first: hk, second: k, path, fn: f.qualified, lineFirst: h.line, lineSecond: n, via: "" });
              }
            }
          }
        });
        const openHeld = walker.openHeld();
        if (!openHeld.length) continue;
        const held: Array<[string, number, string]> = [];
        for (const h of openHeld) for (const m of h.mutexes) held.push([key(m, cls), h.line, h.kind]);
        if (!held.length) continue;
        const bm = BLOCKING.exec(code);
        if (bm) blocking.push([path, f.qualified, n, bm[1], held.map(([k]) => k)]);
        if (lineEvents(code).length) continue;
        for (const m of code.matchAll(CALL)) {
          const name = m[1];
          if (NOT_CALLS.has(name) || name === t.shortName || /^[A-Z][A-Z0-9_]*$/.test(name)) continue;
          const before = code.slice(0, m.index).trimEnd();
          if ((before.endsWith(".") || before.endsWith("->")) && !before.endsWith("this->")) continue; // another object's locks
          calls.push([f, n, name, held]);
        }
      }
    }
  }
  // one call level: a function called while holding A that itself takes B gives A -> B
  const byName = new Map<string, Fn[]>();
  for (const f of fns) if (f.acquired.size) byName.set(f.name, [...(byName.get(f.name) ?? []), f]);
  for (const [f, n, callee, held] of calls) {
    for (const g of byName.get(callee) ?? []) {
      if (g.cls && f.cls && g.cls !== f.cls) continue; // same short name on an unrelated class
      for (const [k, [, gkind, gtop]] of [...g.acquired.entries()].sort((a, b) => cmpStr(a[0], b[0]))) {
        for (const [hk, hl, hkind] of held) {
          if (hk === k) {
            // only a lock the callee always takes; `if (acquireLock) AcquireSRWLock...` is a common pattern
            if (gtop && !RECURSIVE_KINDS.has(gkind) && !RECURSIVE_KINDS.has(hkind)) selfre.push([f.path, f.qualified, n, k, g.qualified]);
          } else edges.push({ first: hk, second: k, path: f.path, fn: f.qualified, lineFirst: hl, lineSecond: n, via: g.qualified });
        }
      }
    }
  }
  return { fns, edges, blocking, selfre };
}

export function findCycles(edges: Edge[]): string[][] {
  const graph = new Map<string, Set<string>>();
  for (const e of edges) {
    if (!graph.has(e.first)) graph.set(e.first, new Set());
    graph.get(e.first)!.add(e.second);
  }
  const cycles: string[][] = [];
  for (const start of [...graph.keys()].sort(cmpStr)) {
    const stack: Array<[string, string[]]> = [[start, [start]]];
    while (stack.length) {
      const [node, path] = stack.pop()!;
      for (const nxt of [...(graph.get(node) ?? [])].sort(cmpStr).reverse()) {
        if (nxt === start && path.length >= 2) cycles.push([...path]);
        else if (cmpStr(nxt, start) > 0 && !path.includes(nxt) && path.length < MAX_CYCLE) stack.push([nxt, [...path, nxt]]);
      }
    }
  }
  return cycles.sort((a, b) => a.length - b.length || cmpTuple(a, b));
}

function ev(e: Edge): string {
  const how = e.via ? `via \`${e.via}()\` at L${e.lineSecond}` : `at L${e.lineSecond}`;
  return `\`${e.path}:${e.lineFirst}\` in \`${e.fn}\`: holds \`${e.first}\` (L${e.lineFirst}), takes \`${e.second}\` ${how}`;
}

function involves(k: string, symbol: string): boolean {
  if (!symbol || k === symbol) return true;
  const last = k.split("::").pop()!;
  return last.split(".").pop() === symbol;
}

function dedupe<T>(items: T[]): T[] {
  const seen = new Set<string>();
  return items.filter((x) => {
    const k = JSON.stringify(x);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

/** `focus` = "path\0qualified" of changed functions: review mode, only findings about their locks ("" when none). */
export async function lockOrderReport(cfg: Config, pathGlob = "", symbol = "", focus: Set<string> | null = null): Promise<string> {
  symbol = (symbol || "").trim();
  const a = await analyse(cfg, pathGlob);
  const { fns, edges } = a;
  let { blocking, selfre } = a;
  const scope = symbol ? `\`${symbol}\`` : pathGlob ? `\`${pathGlob}\`` : "repository";
  const title = focus === null ? `### 🔀 LOCK ORDER: ${scope}` : "### 🔀 LOCK ORDER: locks taken by changed functions";
  const lockingFns = fns.filter((f) => f.acquired.size);
  const keys = [...new Set(lockingFns.flatMap((f) => [...f.acquired.keys()]))].sort(cmpStr);
  let onlyKeys: Set<string> | null = null;
  if (focus !== null) {
    onlyKeys = new Set();
    for (const f of fns) if (focus.has(`${f.path}\0${f.qualified}`)) for (const k of f.acquired.keys()) onlyKeys.add(k);
    for (const e of edges) if (focus.has(`${e.path}\0${e.fn}`)) (onlyKeys.add(e.first), onlyKeys.add(e.second));
    if (!onlyKeys.size) return "";
    blocking = blocking.filter((b) => focus.has(`${b[0]}\0${b[1]}`));
    selfre = selfre.filter((x) => focus.has(`${x[0]}\0${x[1]}`));
  }
  if (!lockingFns.length) return `${title}\n✅ No lock acquisitions found` + (pathGlob ? ` in files matching \`${pathGlob}\`.` : ".");
  const keep = (ks: string[]): boolean => ks.some((k) => involves(k, symbol)) && (onlyKeys === null || ks.some((k) => onlyKeys!.has(k)));
  const cycles = findCycles(edges).filter(keep);
  if (focus !== null && !cycles.length && !selfre.length && !blocking.length) return "";
  const pairs = new Map<string, Edge[]>();
  for (const e of edges) {
    const pk = `${e.first}\0${e.second}`;
    if (!pairs.has(pk)) pairs.set(pk, []);
    pairs.get(pk)!.push(e);
  }
  const files = new Set(lockingFns.map((f) => f.path));
  const out = [
    title,
    `Scanned ${md.plural(lockingFns.length, "function")} that take locks in ${md.plural(files.size, "file")}: ` +
      `${md.plural(keys.length, "lock")}, ${md.plural(pairs.size, "ordering pair")}.`,
  ];
  if (cycles.length) {
    out.push(`\n⚠️ **${md.plural(cycles.length, "potential deadlock cycle")}** (locks taken in opposite orders):`);
    const items = cycles.map((c, i) => {
      const ring = [...c, c[0]].map((k) => `\`${k}\``).join(" → ");
      const lines = [`${i + 1}. ${ring}`];
      c.forEach((x, j) => {
        const y = c[(j + 1) % c.length];
        const evs = [...pairs.get(`${x}\0${y}`)!].sort((p, q) => cmpTuple([p.path, p.lineFirst, p.lineSecond, p.via], [q.path, q.lineFirst, q.lineSecond, q.via]));
        lines.push(`   - ${ev(evs[0])}` + (evs.length > 1 ? ` (+${evs.length - 1} more)` : ""));
      });
      return lines.join("\n");
    });
    out.push(...md.truncateList(items, cfg.maxResults, "cycles", "Pass symbol or path_glob to focus."));
  } else out.push("\n✅ No lock-order cycles found" + (symbol ? ` involving \`${symbol}\`.` : "."));
  const sre = dedupe(selfre.filter((s) => keep([s[3]]))).sort(cmpTuple);
  if (sre.length) {
    out.push("\n⚠️ **Same lock taken twice** (self-deadlock for non-recursive mutexes):");
    out.push(
      ...md.truncateList(
        sre.map(([p, fn, n, k, via]) => `- \`${p}:${n}\` in \`${fn}\`: \`${k}\` is already held` + (via ? `, and \`${via}()\` takes it again` : "")),
        cfg.maxResults,
        "sites",
      ),
    );
  }
  const blk = dedupe(
    blocking.filter((b) => keep(b[4])).map(([p, fn, n, call, ks]) => [p, fn, n, call, [...new Set(ks)].sort(cmpStr)] as Blocking),
  ).sort(cmpTuple);
  if (blk.length) {
    out.push("\n⏳ **Locks held across blocking calls** (latency, and deadlock if the other side needs the lock):");
    out.push(
      ...md.truncateList(
        blk.map(([p, fn, n, call, ks]) => `- \`${p}:${n}\` in \`${fn}\`: \`${call}()\` while holding ` + ks.map((k) => `\`${k}\``).join(", ")),
        cfg.maxResults,
        "sites",
      ),
    );
  }
  const order = [...pairs.entries()]
    .map(([pk, evs]) => [pk.split("\0") as [string, string], evs] as const)
    .filter(([[x, y]]) => keep([x, y]))
    .sort((p, q) => cmpStr(p[0][0], q[0][0]) || cmpStr(p[0][1], q[0][1]));
  if (order.length && onlyKeys === null) {
    out.push("\n**Acquisition order** (A → B: B is taken while A is held):");
    out.push(
      ...md.truncateList(
        order.map(([[x, y], evs]) => {
          const e0 = [...evs].sort((p, q) => cmpTuple([p.path, p.lineSecond, p.via], [q.path, q.lineSecond, q.via]))[0];
          return `- \`${x}\` → \`${y}\`: ${md.plural(evs.length, "place")}, e.g. \`${e0.path}:${e0.lineSecond}\` in \`${e0.fn}\`` + (e0.via ? ` via \`${e0.via}()\`` : "");
        }),
        cfg.maxResults,
        "pairs",
      ),
    );
  }
  out.push(
    "\n_Heuristic: locks matched by name (members qualified by class), order taken inside each function " +
      "plus one call level; aliases, lock hierarchies and runtime conditions are not modelled._",
  );
  return out.join("\n");
}

export async function track_lock_order(args: { path_glob?: string; symbol?: string }): Promise<string> {
  return lockOrderReport(loadConfig(), args.path_glob ?? "", args.symbol ?? "");
}
