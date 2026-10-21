/**
 * Dataset access for the agent-incidents MCP server. Pure functions, no I/O apart from loadDataset.
 *
 * Records follow schema/incident.schema.json of https://github.com/basitalisandhu/ai-agent-incidents. The bundled
 * file (plugins/agent-security/data/incidents.json) is a copy of the published site/incidents.json, a JSON array.
 * Set AGENT_INCIDENTS_DATA to point at another copy. The server never fetches anything itself.
 */
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

export interface Source {
  url: string;
  title?: string;
  publisher?: string;
  accessed?: string;
}

export interface Incident {
  id: string;
  date: string; // YYYY-MM or YYYY-MM-DD
  name: string;
  type: string;
  lens: string;
  vector: string;
  channel_in: string;
  authority: string;
  channel_out: string;
  adversarial: boolean;
  outcome: string;
  cve: string[];
  sources: Source[];
  summary: string;
  mappings: { owasp_agentic: string[]; owasp_llm: string[]; mitre_atlas: string[] };
  affected: { vendors: string[]; products: string[]; frameworks: string[] };
  tags: string[];
  status: string;
}

export interface Dataset {
  source: string;
  licence: string;
  count: number;
  date_range: { from: string; to: string } | null;
  fields: Record<string, string[]>;
  incidents: Incident[];
}

export const FILTER_FIELDS = ["type", "lens", "vector", "channel_in", "authority", "channel_out", "outcome"] as const;
export const LIST_FIELDS = ["vendor", "product", "framework", "owasp_agentic", "owasp_llm", "mitre_atlas", "tag"] as const;
export const STATS_FIELDS = [...FILTER_FIELDS, "year", "status", ...LIST_FIELDS] as const;
export type StatsField = (typeof STATS_FIELDS)[number];

export interface SearchFilters {
  query?: string;
  vector?: string;
  outcome?: string;
  channel_in?: string;
  authority?: string;
  channel_out?: string;
  lens?: string;
  type?: string;
  vendor?: string;
  product?: string;
  framework?: string;
  owasp_agentic?: string;
  owasp_llm?: string;
  mitre_atlas?: string;
  tag?: string;
  status?: string;
  since?: string;
  until?: string;
  cve_only?: boolean;
  adversarial?: boolean;
  limit?: number;
}

export function defaultDataPath(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  // npm package and container image: dist/data.js -> <package>/data/incidents.json (copied in by prepack or the Dockerfile)
  const packaged = resolve(here, "..", "data", "incidents.json");
  if (existsSync(packaged)) return packaged;
  // inside the plugin: dist/data.js -> incidents-server -> mcp -> agent-security/data/incidents.json
  return resolve(here, "..", "..", "..", "data", "incidents.json");
}

const strs = (v: unknown): string[] => (Array.isArray(v) ? v.map(String) : []);

function normalise(raw: Record<string, unknown>): Incident {
  const str = (k: string): string => (raw[k] === undefined || raw[k] === null ? "" : String(raw[k]));
  const adv = raw["adversarial"];
  const cveRaw = raw["cve"];
  const cve = Array.isArray(cveRaw) ? cveRaw.map(String) : typeof cveRaw === "string" && cveRaw.trim() !== "" && cveRaw.trim() !== "-" ? cveRaw.split(",").map((s) => s.trim()) : [];
  const sourcesRaw = raw["sources"];
  const sources: Source[] = Array.isArray(sourcesRaw) && sourcesRaw.length
    ? sourcesRaw.map((s) => (s && typeof s === "object" ? (s as Source) : { url: String(s) }))
    : raw["url"] ? [{ url: String(raw["url"]) }] : [];
  const m = (raw["mappings"] && typeof raw["mappings"] === "object" ? raw["mappings"] : {}) as Record<string, unknown>;
  const a = (raw["affected"] && typeof raw["affected"] === "object" ? raw["affected"] : {}) as Record<string, unknown>;
  return {
    id: str("id"),
    date: str("date"),
    name: str("name"),
    type: str("type"),
    lens: str("lens"),
    vector: str("vector"),
    channel_in: str("channel_in"),
    authority: str("authority"),
    channel_out: str("channel_out"),
    adversarial: typeof adv === "boolean" ? adv : ["yes", "true", "1"].includes(String(adv).toLowerCase()),
    outcome: str("outcome"),
    cve,
    sources,
    summary: str("summary") || str("notes"),
    mappings: { owasp_agentic: strs(m["owasp_agentic"]), owasp_llm: strs(m["owasp_llm"]), mitre_atlas: strs(m["mitre_atlas"]) },
    affected: { vendors: strs(a["vendors"]).length ? strs(a["vendors"]) : strs(raw["vendors"]), products: strs(a["products"]), frameworks: strs(a["frameworks"]) },
    tags: strs(raw["tags"]),
    status: str("status") || "confirmed",
  };
}

export function parseDataset(text: string): Dataset {
  const raw = JSON.parse(text) as unknown;
  let entries: unknown[];
  let meta: Record<string, unknown> = {};
  if (Array.isArray(raw)) {
    entries = raw;
  } else if (raw && typeof raw === "object" && Array.isArray((raw as Record<string, unknown>)["incidents"])) {
    meta = raw as Record<string, unknown>;
    entries = meta["incidents"] as unknown[];
  } else {
    throw new Error("incident dataset must be an array or an object with an incidents array");
  }
  const incidents = entries.filter((e): e is Record<string, unknown> => !!e && typeof e === "object").map(normalise);
  if (incidents.length === 0) throw new Error("incident dataset is empty");
  incidents.sort((a, b) => (a.date === b.date ? a.id.localeCompare(b.id) : a.date.localeCompare(b.date)));
  const fields: Record<string, string[]> = {};
  for (const f of FILTER_FIELDS) fields[f] = [...new Set(incidents.map((i) => i[f]).filter(Boolean))].sort();
  fields["owasp_agentic"] = [...new Set(incidents.flatMap((i) => i.mappings.owasp_agentic))].sort();
  fields["vendor"] = [...new Set(incidents.flatMap((i) => i.affected.vendors))].sort();
  return {
    source: String(meta["source"] ?? "https://github.com/basitalisandhu/ai-agent-incidents"),
    licence: String(meta["licence"] ?? "CC BY 4.0"),
    count: incidents.length,
    date_range: { from: incidents[0].date, to: incidents[incidents.length - 1].date },
    fields,
    incidents,
  };
}

export function loadDataset(path?: string): Dataset {
  const file = path ?? process.env["AGENT_INCIDENTS_DATA"] ?? defaultDataPath();
  return parseDataset(readFileSync(file, "utf8"));
}

export const primaryUrl = (i: Incident): string => i.sources[0]?.url ?? "";

export function listValues(i: Incident, key: (typeof LIST_FIELDS)[number]): string[] {
  switch (key) {
    case "vendor": return i.affected.vendors;
    case "product": return i.affected.products;
    case "framework": return i.affected.frameworks;
    case "owasp_agentic": return i.mappings.owasp_agentic;
    case "owasp_llm": return i.mappings.owasp_llm;
    case "mitre_atlas": return i.mappings.mitre_atlas;
    case "tag": return i.tags;
  }
}

function textOf(i: Incident): string {
  return [i.name, i.summary, i.sources.map((s) => s.url).join(" "), i.affected.vendors.join(" "), i.affected.products.join(" "),
    i.affected.frameworks.join(" "), i.tags.join(" "), i.cve.join(" ")].join(" ").toLowerCase();
}

const eq = (a: string, b?: string): boolean => !b || a.toLowerCase() === b.toLowerCase();
const hasSub = (xs: string[], b?: string): boolean => !b || xs.some((x) => x.toLowerCase().includes(b.toLowerCase()));
const hasEq = (xs: string[], b?: string): boolean => !b || xs.some((x) => x.toLowerCase() === b.toLowerCase());

/** True when the incident satisfies every filter (limit is ignored here). */
export function matches(i: Incident, f: SearchFilters): boolean {
  if (!eq(i.vector, f.vector) || !eq(i.outcome, f.outcome) || !eq(i.channel_in, f.channel_in)) return false;
  if (!eq(i.authority, f.authority) || !eq(i.channel_out, f.channel_out) || !eq(i.lens, f.lens) || !eq(i.type, f.type)) return false;
  if (f.vendor && !hasSub(i.affected.vendors, f.vendor) && !i.name.toLowerCase().includes(f.vendor.toLowerCase())) return false;
  if (!hasSub(i.affected.products, f.product) || !hasSub(i.affected.frameworks, f.framework) || !hasSub(i.tags, f.tag)) return false;
  if (!hasEq(i.mappings.owasp_agentic, f.owasp_agentic) || !hasEq(i.mappings.owasp_llm, f.owasp_llm) || !hasEq(i.mappings.mitre_atlas, f.mitre_atlas)) return false;
  if (!eq(i.status, f.status)) return false;
  if (f.since && i.date.slice(0, 7) < f.since) return false;
  if (f.until && i.date.slice(0, 7) > f.until) return false;
  if (f.cve_only && i.cve.length === 0) return false;
  if (typeof f.adversarial === "boolean" && i.adversarial !== f.adversarial) return false;
  if (f.query && !textOf(i).includes(f.query.toLowerCase())) return false;
  return true;
}

export function searchIncidents(ds: Dataset, f: SearchFilters): { total: number; incidents: Incident[] } {
  const rows = ds.incidents.filter((i) => matches(i, f)).sort((a, b) => (b.date === a.date ? b.id.localeCompare(a.id) : b.date.localeCompare(a.date)));
  const limit = Math.max(1, Math.min(100, f.limit ?? 20));
  return { total: rows.length, incidents: rows.slice(0, limit) };
}

export function getIncident(ds: Dataset, id: string): Incident | undefined {
  const wanted = /^\d+$/.test(id) ? id.padStart(3, "0") : id;
  return ds.incidents.find((i) => i.id === wanted || i.id === id);
}

export function stats(ds: Dataset, by: StatsField, filters: SearchFilters = {}): { by: string; total: number; rows: { value: string; count: number; share: number }[] } {
  const all = ds.incidents.filter((i) => matches(i, filters));
  const counter = new Map<string, number>();
  for (const i of all) {
    let keys: string[];
    if (by === "year") keys = [i.date.slice(0, 4)];
    else if (by === "status") keys = [i.status];
    else if ((LIST_FIELDS as readonly string[]).includes(by)) {
      const vals = listValues(i, by as (typeof LIST_FIELDS)[number]);
      keys = vals.length ? vals : ["(none)"];
    } else keys = [i[by as (typeof FILTER_FIELDS)[number]] || "-"];
    for (const k of keys) counter.set(k, (counter.get(k) ?? 0) + 1);
  }
  const rows = [...counter.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([value, count]) => ({ value, count, share: all.length ? Math.round((1000 * count) / all.length) / 10 : 0 }));
  return { by, total: all.length, rows };
}
