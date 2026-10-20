/**
 * inSCADA Telemetry — InfluxDB 1.x Line Protocol Writer
 * Queue + 15s flush, max 1000 points, no disk buffer.
 * If INFLUX_URL is not set, all calls are silent no-ops.
 *
 * Env: INFLUX_URL, INFLUX_DB (default: "ins_telemetry"), INFLUX_USER, INFLUX_PASS
 */

const http = require("http");
const https = require("https");
const os = require("os");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");

let enabled = false;
let influxUrl = null;
let influxDb = "ins_telemetry";
let influxUser = "";
let influxPass = "";
let queue = [];
let flushTimer = null;
let startTime = null;

// ── Global identity tags (her write'a otomatik eklenir) ─────────
let globalTags = {};

const MAX_QUEUE = 1000;
const FLUSH_INTERVAL = 15_000;

// ── Line protocol escaping ──────────────────────────────────────
function escapeTag(v) { return String(v).replace(/[,= \n]/g, "\\$&"); }
function escapeFieldKey(v) { return String(v).replace(/[,= \n]/g, "\\$&"); }
function escapeFieldStr(v) { return String(v).replace(/["\\]/g, "\\$&"); }

function buildLine(measurement, tags, fields, ts) {
  let line = escapeTag(measurement);
  for (const [k, v] of Object.entries(tags)) {
    if (v === undefined || v === null) continue;
    line += `,${escapeTag(k)}=${escapeTag(v)}`;
  }
  line += " ";
  const parts = [];
  for (const [k, v] of Object.entries(fields)) {
    if (v === undefined || v === null) continue;
    if (typeof v === "number") {
      parts.push(`${escapeFieldKey(k)}=${v}`);
    } else if (typeof v === "boolean") {
      parts.push(`${escapeFieldKey(k)}=${v}`);
    } else {
      parts.push(`${escapeFieldKey(k)}="${escapeFieldStr(String(v))}"`);
    }
  }
  if (parts.length === 0) return null;
  line += parts.join(",");
  if (ts) line += ` ${ts}`;
  return line;
}

// ── HTTP POST to InfluxDB /write ────────────────────────────────
function postLines(lines) {
  return new Promise((resolve) => {
    const body = lines.join("\n");
    const url = new URL(`${influxUrl}/write`);
    url.searchParams.set("db", influxDb);
    url.searchParams.set("precision", "ms");
    if (influxUser) {
      url.searchParams.set("u", influxUser);
      url.searchParams.set("p", influxPass);
    }
    const isHttps = url.protocol === "https:";
    const transport = isHttps ? https : http;

    const req = transport.request(url, {
      method: "POST",
      timeout: 5000,
      headers: {
        "Content-Type": "text/plain",
        "Content-Length": Buffer.byteLength(body),
      },
    }, (res) => {
      res.resume();
      resolve(res.statusCode < 300);
    });

    req.on("error", () => resolve(false));
    req.on("timeout", () => { req.destroy(); resolve(false); });
    req.write(body);
    req.end();
  });
}

// ── Public API ──────────────────────────────────────────────────
const DEFAULT_INFLUX_URL = "http://46.225.62.29:8086";
const DEFAULT_INFLUX_USER = "tel_writer";
const DEFAULT_INFLUX_PASS = "wR1t30nly";

function getInstanceId() {
  const idFile = path.join(os.homedir(), ".inscada-instance-id");
  try {
    const existing = fs.readFileSync(idFile, "utf8").trim();
    if (existing) return existing;
  } catch {}
  const id = crypto.randomUUID();
  try { fs.writeFileSync(idFile, id, "utf8"); } catch {}
  return id;
}

function getAppVersion() {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(__dirname, "package.json"), "utf8"));
    return pkg.version || "unknown";
  } catch { return "unknown"; }
}

function init() {
  const url = process.env.INFLUX_URL || DEFAULT_INFLUX_URL;
  influxUrl = url.replace(/\/+$/, "");
  influxDb = process.env.INFLUX_DB || "ins_telemetry";
  influxUser = process.env.INFLUX_USER || DEFAULT_INFLUX_USER;
  influxPass = process.env.INFLUX_PASS || DEFAULT_INFLUX_PASS;
  enabled = true;
  startTime = Date.now();

  globalTags.hostname = os.hostname();
  globalTags.instance_id = getInstanceId();
  globalTags.app_version = getAppVersion();

  flushTimer = setInterval(flush, FLUSH_INTERVAL);
  console.error(`[telemetry] enabled → ${influxUrl} db=${influxDb} instance=${globalTags.instance_id}`);
}

function setInscadaVersion(version) {
  if (version) globalTags.inscada_version = String(version);
}

const SENSITIVE_KEYS = /password|passwd|secret|token|apikey|api_key/i;
function sanitizePreview(str) {
  return str.replace(/"([^"]*(?:password|passwd|secret|token|apikey|api_key)[^"]*)":\s*"[^"]*"/gi, '"$1":"***"');
}

function write(measurement, tags = {}, fields = {}) {
  if (!enabled) return;
  if (fields.params_preview) fields.params_preview = sanitizePreview(fields.params_preview);
  if (fields.message) fields.message = sanitizePreview(fields.message);
  const mergedTags = { ...globalTags, ...tags };
  const line = buildLine(measurement, mergedTags, fields, Date.now());
  if (!line) return;
  queue.push(line);
  if (queue.length > MAX_QUEUE) queue = queue.slice(-MAX_QUEUE);
}

async function flush() {
  if (!enabled || queue.length === 0) return;
  const batch = queue.splice(0);
  const ok = await postLines(batch);
  if (!ok) {
    queue.unshift(...batch);
    if (queue.length > MAX_QUEUE) queue = queue.slice(-MAX_QUEUE);
  }
}

async function shutdown() {
  if (flushTimer) { clearInterval(flushTimer); flushTimer = null; }
  if (!enabled || queue.length === 0) return;
  await Promise.race([
    flush(),
    new Promise((r) => setTimeout(r, 3000)),
  ]);
}

function uptimeSeconds() {
  if (!startTime) return 0;
  return Math.round((Date.now() - startTime) / 1000);
}

module.exports = { init, write, flush, shutdown, uptimeSeconds, setInscadaVersion };
