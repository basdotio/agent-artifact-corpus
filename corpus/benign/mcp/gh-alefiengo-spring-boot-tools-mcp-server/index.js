#!/usr/bin/env node
/** Six Spring-aware tools; project discovery and build coordination are shared with hooks. */

import { McpServer } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import { z } from "zod";
import fs from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { XMLParser, XMLValidator } from "fast-xml-parser";
import { parseAllDocuments } from "yaml";

// ── helpers ─────────────────────────────────────────────────────────

// No shell interpretation. Bound captured output and terminate the whole process
// group so Maven/Gradle JVMs cannot keep running after cancellation or timeout.
export function run(command, args = [], { cwd, timeout = 120_000, signal, input, maxOutputBytes = 4 * 1024 * 1024, env = process.env } = {}) {
  return new Promise((resolve) => {
    let stdout = "", stderr = "", reason, spawnError, size = 0, killTimer;
    const grouped = process.platform !== "win32";
    const child = spawn(command, args, { cwd, env, shell: false, detached: grouped, stdio: [input === undefined ? "ignore" : "pipe", "pipe", "pipe"] });
    if (input !== undefined) { child.stdin.on("error", () => {}); child.stdin.end(input); }
    const kill = (sig) => {
      try { grouped ? process.kill(-child.pid, sig) : child.kill(sig); } catch { /* already exited */ }
    };
    const stop = (why) => {
      if (reason) return;
      reason = why;
      kill("SIGTERM");
      killTimer = setTimeout(() => kill("SIGKILL"), 1000);
      killTimer.unref();
    };
    const capture = (stream) => (chunk) => {
      const remaining = maxOutputBytes - size;
      const text = chunk.subarray(0, Math.max(0, remaining)).toString();
      size += chunk.length;
      if (stream === "stdout") stdout += text; else stderr += text;
      if (size > maxOutputBytes) stop("Output limit exceeded");
    };
    child.stdout.on("data", capture("stdout"));
    child.stderr.on("data", capture("stderr"));
    const abort = () => stop("Cancelled");
    signal?.addEventListener("abort", abort, { once: true });
    if (signal?.aborted) abort();
    const timer = setTimeout(() => stop("Timed out"), timeout);
    child.on("error", (error) => { spawnError = error.message; stderr += error.message; });
    child.on("close", (code, exitSignal) => {
      clearTimeout(timer);
      clearTimeout(killTimer);
      signal?.removeEventListener("abort", abort);
      resolve({ stdout, stderr, exitCode: spawnError ? 1 : code ?? 1, ...(spawnError || reason || exitSignal ? { error: spawnError || reason || `Terminated by ${exitSignal}` } : {}) });
    });
  });
}

const textResult = (value, isError = false) => ({ content: [{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) }], ...(isError ? { isError: true } : {}) });
const result = (r) => textResult(r, r.exitCode !== 0 || r.ok === false || r.inputsChanged === true);
const asArray = (value) => value == null ? [] : Array.isArray(value) ? value : [value];
const xmlParser = new XMLParser({ ignoreAttributes: false, attributeNamePrefix: "@", parseAttributeValue: false, removeNSPrefix: true });
function parseXml(text) {
  if (text.length > 8 * 1024 * 1024) throw new Error("XML file exceeds 8 MiB limit.");
  if (/<!DOCTYPE|<!ENTITY/i.test(text)) throw new Error("DTD and entity declarations are not supported.");
  const valid = XMLValidator.validate(text);
  if (valid !== true) throw new Error(`Invalid XML: ${valid.err.msg}`);
  return xmlParser.parse(text);
}
async function walk(dir) {
  let entries;
  try { entries = await fs.readdir(dir, { withFileTypes: true }); } catch (e) { if (e.code === "ENOENT") return []; throw e; }
  const files = [];
  for (const entry of entries) {
    const file = path.join(dir, entry.name);
    if (entry.isDirectory() && ![".git", "node_modules", ".gradle", "target", "build"].includes(entry.name)) files.push(...await walk(file));
    else if (entry.isFile()) files.push(file);
  }
  return files.sort();
}
const runtimeFile = fileURLToPath(new URL("../runtime/project_runtime.py", import.meta.url));
async function runtime(payload, ctx, timeout = 120_000) {
  // This plugin-owned setting selects diagnostic HTTP endpoints, not build inputs.
  const buildEnvironment = { ...process.env };
  delete buildEnvironment.SPRING_BOOT_APP_PORT;
  const execution = await run("python3", [runtimeFile], {
    input: JSON.stringify({ projectRoot: process.env.PROJECT_ROOT || process.cwd(), ...payload }), env: buildEnvironment,
    timeout, signal: ctx?.mcpReq?.signal, maxOutputBytes: 32 * 1024 * 1024,
  });
  if (execution.error) throw new Error(execution.error);
  let response;
  try { response = JSON.parse(execution.stdout); } catch { throw new Error(`Project runtime failed: ${execution.stderr || execution.stdout}`); }
  if (execution.exitCode !== 0 || response.error) throw new Error(response.error || execution.stderr || "Project runtime failed");
  return response;
}
async function requireProject() {
  const project = await runtime({ action: "discover" });
  if (!project.buildTool) throw new Error("No Maven/Gradle project found.");
  return project;
}
async function build(project, options, ctx, timeout = 120_000) {
  return runtime({ action: "run", projectRoot: project.root, ...options, timeoutMs: timeout }, ctx, timeout + 2000);
}

// ── tool implementations ────────────────────────────────────────────

async function analyzeProject() {
  const project = await requireProject();
  const { root } = project;
  const projectModules = [{ root, buildFile: project.buildFile }, ...(project.modules || [])];
  const dependencies = [], versions = [], persistence = [], configurations = [], layers = [], ports = [];
  for (const { root: moduleRoot, buildFile } of projectModules) {
    if (buildFile) {
      const file = path.join(moduleRoot, buildFile), source = await fs.readFile(file, "utf-8");
      const provenance = { file: path.relative(root, file), module: path.relative(root, moduleRoot) || ".", resolution: "declared-static" };
      if (buildFile === "pom.xml") {
        const pom = parseXml(source).project;
        for (const dep of asArray(pom?.dependencies?.dependency)) dependencies.push({ group: dep.groupId, artifact: dep.artifactId, version: dep.version || null, scope: dep.scope || "compile", provenance });
        if (pom?.artifactId && pom?.version) versions.push({ component: `${pom.groupId || pom.parent?.groupId || ""}:${pom.artifactId}`, version: String(pom.version), provenance });
      if (pom?.parent) versions.push({ component: `${pom.parent.groupId}:${pom.parent.artifactId}`, version: pom.parent.version, provenance });
        for (const [name, version] of Object.entries(pom?.properties || {})) if (/version|java|jdk/i.test(name)) versions.push({ component: name, version: String(version), provenance });
      } else {
        const clean = source.replace(/\/\*[\s\S]*?\*\/|^\s*\/\/.*$/gm, "");
        for (const match of clean.matchAll(/\b(implementation|api|compileOnly|runtimeOnly|testImplementation|testRuntimeOnly|annotationProcessor|kapt)\s*(?:\(\s*)?(?:(?:platform|enforcedPlatform)\s*\(\s*)?["']([^"']+:[^"']+)["']/g)) {
          const [group, artifact, version] = match[2].split(":"); dependencies.push({ group, artifact, version: version || null, scope: match[1], provenance });
        }
        for (const match of clean.matchAll(/(?:id\s*\(\s*["']([^"']+)["']\s*\)|id\s+["']([^"']+)["'])\s+version\s+["']([^"']+)["']/g)) versions.push({ component: match[1] || match[2], version: match[3], provenance });
      }
    }
    for (const language of ["java", "kotlin"]) for (const file of await walk(path.join(moduleRoot, "src/main", language))) {
      if (!/\.(?:java|kt)$/.test(file)) continue;
      const source = await fs.readFile(file, "utf-8"), relative = path.relative(root, file);
      layers.push(path.relative(path.join(moduleRoot, "src/main", language), path.dirname(file)));
      if (!/@Entity\b/.test(source)) continue;
      const table = source.match(/@Table\s*\(([^)]*)\)/)?.[1]?.match(/\bname\s*=\s*"([^"]+)"/)?.[1];
      persistence.push({ name: source.match(/\bclass\s+(\w+)/)?.[1], file: relative, table: table || null, columns: [...source.matchAll(/@Column\s*\(([^)]*)\)/g)].map(m => ({ name: m[1].match(/\bname\s*=\s*"([^"]+)"/)?.[1] || null, options: m[1] })), relations: [...source.matchAll(/@(OneToOne|OneToMany|ManyToOne|ManyToMany)(?:\s*\(([^)]*)\))?/g)].map(m => ({ type: m[1], options: m[2] || "" })), fields: [...source.matchAll(/private\s+(\S+(?:<[^>]+>)?)\s+(\w+)\s*;/g)].map(m => ({ type: m[1], name: m[2] })), entityGraph: /@EntityGraph\b/.test(source), provenance: { file: relative, resolution: "static-annotations" } });
    }
    for (const file of await walk(path.join(moduleRoot, "src/main/resources"))) {
      if (!/application(?:-[^.]+)?\.(?:ya?ml|properties)$/.test(path.basename(file))) continue;
      const content = await fs.readFile(file, "utf-8"), declaredPorts = [];
      if (/\.properties$/.test(file)) for (const m of content.matchAll(/^\s*server\.port\s*[=:]\s*(\d+)\s*$/gm)) declaredPorts.push(Number(m[1]));
      else for (const doc of parseAllDocuments(content)) {
        if (doc.errors.length) throw new Error(`Invalid YAML in ${file}: ${doc.errors[0].message}`);
        const config = doc.toJS(), port = config?.server?.port ?? config?.["server.port"];
        if (/^\d+$/.test(String(port))) declaredPorts.push(Number(port));
      }
      configurations.push({ file: path.relative(root, file), ports: declaredPorts }); ports.push(...declaredPorts);
    }
  }
  const artifacts = dependencies.map(d => d.artifact || "");
  return textResult({ ...project, dependencies, versions, persistence, configurations, layers: [...new Set(layers)].filter(Boolean), ports: [...new Set(ports)], capabilities: { build: true, tests: true, actuator: artifacts.some(a => a.includes("actuator")) ? "declared" : "unknown", openapi: artifacts.some(a => a.includes("springdoc")) ? "declared" : "unknown", persistence: persistence.length > 0 || artifacts.some(a => /jpa|jdbc/.test(a)) ? "declared" : "unknown", flyway: artifacts.some(a => a.includes("flyway")) ? "declared" : "unknown" }, limitations: ["Dependencies and versions are declared values; parent inheritance, catalogs, expressions and transitive dependencies require build-tool resolution.", "Entity annotations and configuration files are inventories, not effective runtime metadata. Configuration values other than ports are not returned."] });
}
async function runBuild(args, ctx) {
  const project = await requireProject();
  if (activeBuilds.has(project.root)) throw new Error("A build is already active for this project.");
  activeBuilds.add(project.root);
  try { return result(await build(project, { task: args?.task || "compile", module: args?.module, profiles: args?.profiles || [], reuse: !args?.force }, ctx)); }
  finally { activeBuilds.delete(project.root); }
}
async function checkMigrations(args, ctx) {
  const project = await requireProject(), { root } = project;
  if (args?.mode === "status") {
    const execution = await build(project, { task: "migration-status", module: args.module, profiles: args.profiles || [] }, ctx);
    return textResult({ mode: "status", databaseAccess: true, limitation: "Build-tool Flyway status queries the configured database; plugin and credentials must already be configured.", ...execution }, execution.exitCode !== 0 || !execution.ok);
  }
  const selectedModule = args?.module;
  if (selectedModule && !project.modules.some(m => m.path === selectedModule)) throw new Error("module must match a discovered module path");
  const scanRoot = selectedModule ? path.join(root, selectedModule) : root;
  const files = (await walk(scanRoot)).filter(f => /(?:^|[/\\])src[/\\]main[/\\]resources[/\\]db[/\\]migration[/\\][^/\\]+\.sql$/.test(f));
  const migrations = [], errors = [], risks = [], groups = new Map();
  for (const file of files) {
    const relative = path.relative(root, file), name = path.basename(file), match = name.match(/^(?:([VU])(\d+(?:[._]\d+)*)|R)__([^/]+)\.sql$/);
    const location = path.relative(root, path.dirname(file)), content = await fs.readFile(file, "utf-8");
    if (!match) errors.push({ file: relative, code: "naming", message: "Expected V/U<version>__description.sql or R__description.sql." });
    if (!content.trim()) errors.push({ file: relative, code: "empty", message: "Empty migration." });
    let version = match?.[2]?.split(/[._]/).map(n => BigInt(n).toString());
    while (version?.length > 1 && version.at(-1) === "0") version.pop();
    const normalizedVersion = version?.join(".") || null;
    migrations.push({ file: relative, location, type: match?.[1] || (match ? "R" : null), version: normalizedVersion });
    if (normalizedVersion) {
      const key = `${location}:${match[1]}:${normalizedVersion}`;
      if (groups.has(key)) errors.push({ file: relative, code: "duplicate-version", message: `Equivalent version to ${groups.get(key)}`, version: normalizedVersion }); else groups.set(key, relative);
    }
    const sql = content.replace(/\/\*[\s\S]*?\*\/|--[^\n]*|'(?:''|[^'])*'/g, " ");
    if (/\b(?:DROP\s+(?:TABLE|SCHEMA|DATABASE|INDEX|COLUMN)|TRUNCATE(?:\s+TABLE)?)\b/i.test(sql)) risks.push({ file: relative, code: "destructive-sql", message: "DROP/TRUNCATE requires data-loss and lock review." });
    for (const statement of sql.split(";")) if (/\bDELETE\s+FROM\b/i.test(statement) && !/\bWHERE\b/i.test(statement)) risks.push({ file: relative, code: "unbounded-delete", message: "DELETE without WHERE requires explicit data-loss review." });
  }
  migrations.sort((a, b) => a.location.localeCompare(b.location) || compareVersions(a.version, b.version) || a.file.localeCompare(b.file));
  return textResult({ mode: "lint", databaseAccess: false, migrations, errors, risks, ordering: "Numeric version order per source location; repeatable migrations follow versioned migrations. Source locations may be merged by runtime Flyway configuration; cross-location duplicates require effective configuration.", limitation: "SQL lint does not prove migration safety or applied-state immutability." }, errors.length > 0);
}
function compareVersions(a, b) {
  if (!a || !b) return a ? -1 : b ? 1 : 0;
  const aa = a.split(".").map(BigInt), bb = b.split(".").map(BigInt);
  for (let i = 0; i < Math.max(aa.length, bb.length); i++) { const x = aa[i] || 0n, y = bb[i] || 0n; if (x !== y) return x < y ? -1 : 1; } return 0;
}

// ── tool: run_tests ─────────────────────────────────────────────────
const activeBuilds = new Set();
async function runTests(args, ctx) {
  const project = await requireProject();
  const testClass = args?.testClass;
  if (activeBuilds.has(project.root)) throw new Error("A test run is already active for this project.");
  activeBuilds.add(project.root);
  try {
    // Capture both snapshots and report contents inside the shared build lock.
    // A queued invocation must never claim XML generated by another build.
    const { testReports = [], ...r } = await build(project, { task: "test", testClass, module: args?.module, profiles: args?.profiles || [], reuse: false, collectTestReports: true }, ctx, 300_000);
    const suites = [], failures = [], reportErrors = [];
    const staleReportsIgnored = r.staleReportsIgnored || 0;
    for (const { file, content } of testReports) {
      try {
        const parsed = parseXml(content);
        const visit = (suite) => {
          if (!suite) return;
          if (suite["@tests"] !== undefined) suites.push({ suite: suite["@name"] || path.basename(file), tests: Number(suite["@tests"] || 0), failures: Number(suite["@failures"] || 0), errors: Number(suite["@errors"] || 0), skipped: Number(suite["@skipped"] || 0), timeSec: Number(suite["@time"] || 0) });
          for (const test of asArray(suite.testcase)) {
            for (const failure of [...asArray(test.failure), ...asArray(test.error)]) failures.push({ test: `${test["@classname"] || ""}.${test["@name"] || ""}`, message: String(failure["@message"] || failure["#text"] || failure).slice(0, 2000) });
          }
          for (const child of asArray(suite.testsuite)) visit(child);
        };
        for (const suite of asArray(parsed.testsuite ?? parsed.testsuites?.testsuite)) visit(suite);
      } catch (e) { reportErrors.push(`${path.relative(project.root, file)}: ${e.message}`); }
    }
    return textResult({ ...r, suites, failures, staleReportsIgnored, reportErrors, ...(suites.length ? {} : { diagnostic: "No fresh test reports generated by this invocation." }) }, r.exitCode !== 0 || r.ok === false || r.inputsChanged === true || reportErrors.length > 0 || suites.some(s => s.failures || s.errors));
  } finally { activeBuilds.delete(project.root); }
}

// ── tool: openapi_endpoints ─────────────────────────────────────────
function mappingPaths(args = "") {
  const named = args.match(/\b(?:value|path)\s*=\s*(\{[^}]*\}|"[^"]*")/);
  const value = named?.[1] ?? (/^\s*(?:"|\{)/.test(args) ? args.split(/,\s*\w+\s*=/)[0] : "");
  return [...value.matchAll(/"([^"]*)"/g)].map(m => m[1]);
}
async function staticEndpoints() {
  const { root } = await requireProject();
  const endpoints = [], warnings = [];
  for (const file of (await walk(root)).filter(f => /(?:^|[/\\])src[/\\]main[/\\]java[/\\]/.test(f) && f.endsWith(".java"))) {
    const source = (await fs.readFile(file, "utf-8")).replace(/\/\*[\s\S]*?\*\/|^\s*\/\/.*$/gm, "");
    if (!/@(?:RestController|Controller)\b/.test(source)) continue;
    const classIndex = source.search(/\bclass\s+\w+/);
    const prefix = source.slice(0, classIndex);
    const base = [...prefix.matchAll(/@RequestMapping\b(?:\s*\(([^)]*)\))?/g)].at(-1);
    const bases = mappingPaths(base?.[1]);
    for (const match of source.slice(classIndex).matchAll(/@(Get|Post|Put|Patch|Delete|Request)Mapping\b(?:\s*\(([^)]*)\))?/g)) {
      const methods = match[1] === "Request" ? [...(match[2] || "").matchAll(/RequestMethod\.(\w+)/g)].map(m => m[1]) : [match[1].toUpperCase()];
      const paths = mappingPaths(match[2]);
      if (!methods.length) methods.push("ANY");
      if (/\b(?:path|value)\s*=\s*[A-Za-z_]/.test(match[2] || "")) warnings.push(`${path.relative(root, file)}: computed path cannot be resolved statically.`);
      for (const method of methods) for (const basePath of bases.length ? bases : [""]) for (const route of paths.length ? paths : [""]) {
        const routePath = `/${[basePath, route].map(p => p.replace(/^\/+|\/+$/g, "")).filter(Boolean).join("/")}`;
        endpoints.push({ file: path.relative(root, file), method, path: routePath, version: routePath.match(/\/v(\d+)(?:\/|$)/)?.[1] || "1" });
      }
    }
  }
  return { count: endpoints.length, endpoints, warnings, limitation: "Static annotation inventory; computed constants, Kotlin mappings and composed annotations require runtime OpenAPI inspection." };
}

function appUrl(baseUrl, endpoint) {
  const configuredPort = process.env.SPRING_BOOT_APP_PORT || "8080";
  if (!/^\d+$/.test(configuredPort) || Number(configuredPort) < 1 || Number(configuredPort) > 65535) throw new Error("SPRING_BOOT_APP_PORT must be between 1 and 65535.");
  const url = new URL(baseUrl || `http://localhost:${configuredPort}`);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) throw new Error("baseUrl must be HTTP(S), without credentials, query or fragment.");
  url.pathname = url.pathname.replace(/\/$/, "") + endpoint;
  return url;
}
function httpDiagnosis(status) {
  if (status === 401 || status === 403) return "Access denied: check the application's authentication/authorization; no automatic credential forwarding is performed.";
  if (status === 404) return "Endpoint absent: check exposure, management context path/port and whether the relevant feature is configured.";
  if (status >= 500) return "Application or dependency unhealthy; inspect the selected endpoint and application logs.";
  return status >= 200 && status < 300 ? "Endpoint available." : `Unexpected HTTP status ${status}.`;
}
async function fetchDocument(url, ctx) {
  try {
    const response = await fetch(url, { redirect: "error", signal: AbortSignal.any([AbortSignal.timeout(10_000), ...(ctx?.mcpReq?.signal ? [ctx.mcpReq.signal] : [])]) });
    let size = 0, text = "";
    const decoder = new TextDecoder();
    for await (const chunk of response.body || []) {
      size += chunk.length;
      if (size > 2 * 1024 * 1024) throw new Error("HTTP document exceeds 2 MiB limit.");
      text += decoder.decode(chunk, { stream: true });
    }
    text += decoder.decode();
    return { status: response.status, ok: response.ok, text, diagnosis: httpDiagnosis(response.status) };
  } catch (e) { return { ok: false, error: e.message, diagnosis: "Connection, TLS, cancellation or response limit failure; confirm the application and management port are reachable." }; }
}
async function actuatorHealth(args, ctx) {
  const probes = [...new Set(args?.probes || ["health"])], results = [];
  for (const probe of probes) {
    const endpoint = probe === "health" ? "/actuator/health" : `/actuator/health/${probe}`;
    const response = await fetchDocument(appUrl(args?.baseUrl, endpoint), ctx);
    let health;
    if (response.ok) {
      try { health = JSON.parse(response.text); } catch { response.ok = false; response.error = "Health endpoint did not return valid JSON."; }
    } else if (response.status >= 500) { try { health = JSON.parse(response.text); } catch { /* no response body disclosure for access errors */ } }
    if (["DOWN", "OUT_OF_SERVICE"].includes(health?.status)) { response.ok = false; response.diagnosis = "Health reports an unavailable application or dependency; inspect application logs."; }
    results.push({ probe, endpoint, ...response, text: undefined, ...(health ? { health } : {}) });
  }
  return textResult({ results, limitation: "Only requested health probes are queried; no credentials, env, configprops, heap dumps or arbitrary Actuator endpoints are fetched." }, results.some(r => !r.ok));
}
async function openapiEndpoints(args, ctx) {
  const mode = args?.mode || "static";
  const inventory = mode === "runtime" ? undefined : await staticEndpoints();
  if (mode === "static") return textResult({ mode, ...inventory });
  const response = await fetchDocument(appUrl(args?.baseUrl, args?.documentPath || "/v3/api-docs"), ctx);
  if (!response.ok) return textResult({ mode, runtime: { ...response, text: undefined }, ...(inventory ? { static: inventory } : {}) }, true);
  let document;
  try {
    if ((args?.documentPath || "").endsWith(".yaml")) {
      const documents = parseAllDocuments(response.text);
      if (documents.length !== 1 || documents[0].errors.length) throw new Error("OpenAPI YAML must be one valid document.");
      document = documents[0].toJS();
    } else document = JSON.parse(response.text);
    if (!document || !/^3\.\d+\.\d+/.test(document.openapi) || !document.paths || typeof document.paths !== "object" || Array.isArray(document.paths)) throw new Error("Expected OpenAPI 3.x document with a paths object.");
  } catch (e) { return textResult({ mode, error: `Invalid runtime OpenAPI: ${e.message}`, ...(inventory ? { static: inventory } : {}) }, true); }
  const endpoints = [], warnings = [];
  for (const [route, item] of Object.entries(document.paths)) {
    if (!route.startsWith("/") || !item || typeof item !== "object") { warnings.push(`Invalid path item: ${route}`); continue; }
    if (item.$ref) warnings.push(`${route}: referenced path item is not resolved; external references are never fetched.`);
    for (const method of ["get", "put", "post", "delete", "options", "head", "patch", "trace"]) if (item[method] && typeof item[method] === "object") endpoints.push({ method: method.toUpperCase(), path: route, operationId: item[method].operationId || null });
  }
  const runtimeInventory = { source: "runtime-openapi", version: document.openapi, status: response.status, endpoints, count: endpoints.length, warnings };
  const result = { mode, runtime: runtimeInventory, ...(inventory ? { static: inventory } : {}) };
  if (inventory) {
    const match = (a, b) => a.path === b.path && (a.method === b.method || a.method === "ANY" || b.method === "ANY");
    result.comparison = { onlyStatic: inventory.endpoints.filter(e => !endpoints.some(r => match(e, r))), onlyRuntime: endpoints.filter(e => !inventory.endpoints.some(r => match(e, r))), limitation: "Differences can reflect conditional controllers, context paths, grouped docs, composed annotations or static-parser limits; they are findings to investigate, not proven API defects." };
  }
  return textResult(result);
}

// ── server & registration ───────────────────────────────────────────

export function createServer() {
  const server = new McpServer({ name: "mcp-spring-boot", version: "0.1.0" });
  const register = (name, description, inputSchema, handler) => server.registerTool(name, { description, ...(inputSchema ? { inputSchema } : {}) }, async (...args) => {
    try { return await handler(...args); } catch (e) { return textResult({ error: e.message }, true); }
  });
  const selection = { module: z.string().optional(), profiles: z.array(z.string()).optional() };
  register("analyze_project", "Discovers modules, declared dependency/version provenance, persistence annotations, configuration file inventory and capabilities using the shared project runtime.", undefined, analyzeProject);
  register("run_build", "Runs controlled Maven/Gradle tasks through the shared build coordinator; wrappers, module/profile validation, process locking and bounded output are shared with hooks.", z.object({ task: z.enum(["compile", "test-compile", "package", "verify", "check", "clean", "dependencies"]).default("compile"), force: z.boolean().default(false).describe("Force a fresh verification even when unchanged inputs were already verified."), ...selection }), runBuild);
  register("run_tests", "Runs Maven/Gradle tests with fresh structured XML reports, preserving diagnostics and rejecting stale reports; shared coordinator prevents racing builds.", z.object({ testClass: z.string().optional().describe("Qualified class name, optionally #method; validated by the shared build runtime."), ...selection }), runTests);
  register("check_migrations", "Lints migration names, normalized duplicate versions and risk warnings by module/location. Explicit status mode queries the configured database through Flyway.", z.object({ mode: z.enum(["lint", "status"]).default("lint"), ...selection }), checkMigrations);
  register("openapi_endpoints", "Inventories static controllers; optionally fetches runtime OpenAPI paths and compares routes. Static approximations and runtime schemas are reported separately.", z.object({ mode: z.enum(["static", "runtime", "compare"]).default("static"), baseUrl: z.string().optional(), documentPath: z.enum(["/v3/api-docs", "/v3/api-docs.yaml"]).default("/v3/api-docs") }), openapiEndpoints);
  register("actuator_health", "Queries only explicitly selected health/readiness/liveness endpoints; diagnoses HTTP authentication, exposure and connection failures without collecting other Actuator endpoints.", z.object({ baseUrl: z.string().optional(), probes: z.array(z.enum(["health", "readiness", "liveness"])).min(1).max(3).default(["health"]) }), actuatorHealth);
  return server;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) serveStdio(createServer, { onerror: error => console.error(error.message) });
