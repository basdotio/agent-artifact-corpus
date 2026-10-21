// Embedding engine: resolves/downloads the pinned model, runs it with ONNX Runtime, or uses the test embedder.
// Same ONNX model + tokenizer.json as the Python implementation, so one index serves both.
import { createHash } from "node:crypto";
import { createReadStream, createWriteStream, existsSync, mkdirSync, readFileSync, renameSync, rmSync, statSync } from "node:fs";
import { basename, dirname, join } from "node:path";
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
import type { Config } from "../config.js";
import { StaticSightError } from "../core/errors.js";
import { sharedJson } from "../shared.js";

export class SemanticUnavailable extends StaticSightError {
  constructor(message: string, hint?: string) {
    super(message, hint);
    this.title = "Semantic search is not available";
  }
}

export interface ModelSpec {
  description: string;
  repo?: string;
  revision?: string;
  dims: number;
  max_tokens: number;
  pooling: string;
  onnx?: string;
  files?: Record<string, string>;
}

export function modelSpec(name: string): ModelSpec {
  const models = sharedJson<{ models: Record<string, ModelSpec> }>("semantic/models.json").models;
  if (!(name in models)) {
    throw new SemanticUnavailable(`Unknown embedding model \`${name}\`.`, `Use one of: ${Object.keys(models).sort().join(", ")} (STATICSIGHT_EMBED_MODEL).`);
  }
  return models[name];
}

/** Identity stored in the index; changing it triggers a rebuild. */
export function modelId(cfg: Config): string {
  if (cfg.embedModelDir) return "custom:" + basename(cfg.embedModelDir.replace(/[\\/]+$/, ""));
  const spec = modelSpec(cfg.embedModel);
  return `${cfg.embedModel}@${spec.revision ?? "builtin"}`;
}

export interface Embedder {
  name: string;
  dims: number;
  embed(texts: string[]): Promise<Float32Array[]>;
}

// ----------------------------------------------------------------------------- test embedder
const IDENT = /[A-Za-z0-9_]+/g;
const SUBWORD = /[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+/g;

function asciiLower(s: string): string {
  return s.replace(/[A-Z]/g, (c) => String.fromCharCode(c.charCodeAt(0) + 32));
}

export function hashTokens(text: string): string[] {
  const out: string[] = [];
  for (const m of text.matchAll(IDENT)) {
    for (const part of m[0].split("_")) for (const sw of part.matchAll(SUBWORD)) out.push(asciiLower(sw[0]));
  }
  return out;
}

export function fnv1a32(data: Uint8Array): number {
  let h = 0x811c9dc5;
  for (const b of data) {
    h ^= b;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

/** Deterministic bag-of-subwords embedder (tests only): identical output in Python and TypeScript. */
export class HashEmbedder implements Embedder {
  name = "test-hash";
  constructor(public dims = 256) {}
  async embed(texts: string[]): Promise<Float32Array[]> {
    return texts.map((t) => {
      const v = new Float64Array(this.dims);
      for (const tok of hashTokens(t)) {
        const h = fnv1a32(Buffer.from(tok, "utf8"));
        v[h % this.dims] += (h >>> 8) & 1 ? -1 : 1;
      }
      let n = 0;
      for (const x of v) n += x * x;
      n = Math.sqrt(n) || 1;
      return Float32Array.from(v, (x) => x / n);
    });
  }
}

// ----------------------------------------------------------------------------- model files
export function modelDir(cfg: Config): string {
  if (cfg.embedModelDir) return cfg.embedModelDir;
  const spec = modelSpec(cfg.embedModel);
  return join(cfg.cacheDir, "models", cfg.embedModel, spec.revision!);
}

async function sha256(path: string): Promise<string> {
  const h = createHash("sha256");
  await pipeline(createReadStream(path), h);
  return h.digest("hex");
}

const verified = new Set<string>();

function isFile(p: string): boolean {
  try {
    return statSync(p).isFile();
  } catch {
    return false;
  }
}

/** Files that are absent or fail their pinned sha256 (custom model dirs are only checked for presence). */
export async function missingModelFiles(cfg: Config): Promise<string[]> {
  const d = modelDir(cfg);
  if (cfg.embedModelDir) {
    const onnx = ["onnx/model_quantized.onnx", "onnx/model.onnx", "model.onnx"].some((p) => isFile(join(d, p)));
    return [...(isFile(join(d, "tokenizer.json")) ? [] : ["tokenizer.json"]), ...(onnx ? [] : ["onnx/model.onnx"])];
  }
  const spec = modelSpec(cfg.embedModel);
  const bad: string[] = [];
  for (const [rel, sha] of Object.entries(spec.files ?? {})) {
    const p = join(d, rel);
    const key = `${p}:${sha}`;
    if (verified.has(key)) continue;
    if (!isFile(p) || (await sha256(p)) !== sha) bad.push(rel);
    else verified.add(key);
  }
  return bad;
}

/** Download the pinned model files into the cache (sha256-verified, atomic). Honours HF_ENDPOINT; proxies via NODE_USE_ENV_PROXY=1. */
export async function downloadModel(cfg: Config, progress?: (m: string) => void): Promise<string> {
  if (cfg.embedModelDir) {
    throw new SemanticUnavailable(
      `Model files are missing in STATICSIGHT_EMBED_MODEL_DIR (\`${cfg.embedModelDir}\`).`,
      "Copy tokenizer.json and the ONNX model there, or unset the variable to use the pinned download.",
    );
  }
  const spec = modelSpec(cfg.embedModel);
  if (!spec.repo) return modelDir(cfg);
  if (!cfg.semanticAllowDownload) {
    throw new SemanticUnavailable(
      `The embedding model \`${spec.repo}\` is not downloaded and downloads are disabled.`,
      `Run \`staticsight model download\` on a connected machine and copy \`${modelDir(cfg)}\`, or set STATICSIGHT_EMBED_MODEL_DIR to a pre-downloaded copy.`,
    );
  }
  const d = modelDir(cfg);
  const endpoint = (process.env.HF_ENDPOINT || "https://huggingface.co").replace(/\/+$/, "");
  for (const rel of await missingModelFiles(cfg)) {
    const url = `${endpoint}/${spec.repo}/resolve/${spec.revision}/${rel}`;
    const dest = join(d, rel);
    mkdirSync(dirname(dest), { recursive: true });
    const tmp = dest + ".part";
    progress?.(`downloading ${rel}`);
    try {
      const res = await fetch(url, { redirect: "follow" });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      await pipeline(Readable.fromWeb(res.body as never), createWriteStream(tmp));
    } catch (e) {
      rmSync(tmp, { force: true });
      throw new SemanticUnavailable(
        `Could not download \`${url}\`: ${(e as Error).message}`,
        "Check network/proxy (NODE_USE_ENV_PROXY=1 with HTTPS_PROXY) or HF_ENDPOINT, or pre-download with STATICSIGHT_EMBED_MODEL_DIR.",
      );
    }
    const got = await sha256(tmp);
    if (got !== spec.files![rel]) {
      rmSync(tmp, { force: true });
      throw new SemanticUnavailable(`Checksum mismatch for \`${rel}\` (got ${got.slice(0, 12)}…); the download was discarded.`);
    }
    renameSync(tmp, dest);
  }
  return d;
}

// ----------------------------------------------------------------------------- ONNX embedder
type Ort = typeof import("onnxruntime-node");

async function importOptional(): Promise<[Ort, any]> {
  try {
    const ort = (await import("onnxruntime-node")) as unknown as Ort;
    const tok = await import("@huggingface/tokenizers");
    return [ort, tok];
  } catch (e) {
    throw new SemanticUnavailable(
      `Node packages for semantic search are missing (${(e as Error).message.split("\n")[0]}).`,
      "Install the optional dependencies: `npm install onnxruntime-node @huggingface/tokenizers`.",
    );
  }
}

class OnnxEmbedder implements Embedder {
  constructor(
    public name: string,
    public dims: number,
    private ort: Ort,
    private session: any,
    private tokenizer: any,
    private inputs: Set<string>,
    private maxTokens: number,
    private pooling: string,
    private batch: number,
  ) {}

  async embed(texts: string[]): Promise<Float32Array[]> {
    const idsList = texts.map((t) => {
      const ids: number[] = this.tokenizer.encode(t).ids;
      return this.maxTokens ? ids.slice(0, this.maxTokens) : ids;
    });
    const out: Float32Array[] = new Array(texts.length);
    const order = texts.map((_, i) => i).sort((a, b) => idsList[a].length - idsList[b].length || a - b);
    for (let s = 0; s < order.length; s += this.batch) {
      const idx = order.slice(s, s + this.batch);
      const width = Math.max(1, ...idx.map((i) => idsList[i].length));
      const ids = new BigInt64Array(idx.length * width);
      const mask = new BigInt64Array(idx.length * width);
      idx.forEach((i, r) => {
        idsList[i].forEach((v, c) => {
          ids[r * width + c] = BigInt(v);
          mask[r * width + c] = 1n;
        });
      });
      const feeds: Record<string, any> = {
        input_ids: new this.ort.Tensor("int64", ids, [idx.length, width]),
        attention_mask: new this.ort.Tensor("int64", mask, [idx.length, width]),
      };
      if (this.inputs.has("token_type_ids")) feeds.token_type_ids = new this.ort.Tensor("int64", new BigInt64Array(idx.length * width), [idx.length, width]);
      const result = await this.session.run(feeds);
      const hidden: Float32Array = result[this.session.outputNames[0]].data;
      const D = hidden.length / (idx.length * width); // hidden size, read from the model output
      this.dims = D;
      idx.forEach((i, r) => {
        const v = new Float64Array(D);
        if (this.pooling === "cls") {
          for (let k = 0; k < D; k++) v[k] = hidden[(r * width) * D + k];
        } else {
          let count = 0;
          for (let c = 0; c < width; c++) {
            if (mask[r * width + c] === 0n) continue;
            count++;
            const base = (r * width + c) * D;
            for (let k = 0; k < D; k++) v[k] += hidden[base + k];
          }
          for (let k = 0; k < D; k++) v[k] /= Math.max(count, 1e-9);
        }
        let n = 0;
        for (const x of v) n += x * x;
        n = Math.sqrt(n) || 1;
        out[i] = Float32Array.from(v, (x) => x / n);
      });
    }
    return out;
  }
}

function poolingFromDir(d: string, dflt: string): string {
  const p = join(d, "1_Pooling", "config.json");
  if (existsSync(p)) {
    const c = JSON.parse(readFileSync(p, "utf8"));
    if (c.pooling_mode_cls_token) return "cls";
    if (c.pooling_mode_mean_tokens) return "mean";
  }
  return dflt;
}

const embedders = new Map<string, Promise<Embedder>>();

export async function dependenciesOk(): Promise<void> {
  await importOptional();
}

/** Cached embedder for the configured model (downloads the pinned model on first use when allowed). */
export function getEmbedder(cfg: Config, allowDownload = true, progress?: (m: string) => void): Promise<Embedder> {
  const key = `${cfg.embedModel}|${cfg.embedModelDir}|${cfg.cacheDir}`;
  let p = embedders.get(key);
  if (!p) {
    p = createEmbedder(cfg, allowDownload, progress);
    embedders.set(key, p);
    p.catch(() => embedders.delete(key));
  }
  return p;
}

async function createEmbedder(cfg: Config, allowDownload: boolean, progress?: (m: string) => void): Promise<Embedder> {
  if (!cfg.embedModelDir && cfg.embedModel === "test-hash") return new HashEmbedder(modelSpec("test-hash").dims);
  const [ort, tok] = await importOptional();
  if ((await missingModelFiles(cfg)).length) {
    if (!allowDownload) {
      throw new SemanticUnavailable("The embedding model is not downloaded yet.", "Call refresh_semantic_index (downloads it once) or run `staticsight model download`.");
    }
    await downloadModel(cfg, progress);
    if ((await missingModelFiles(cfg)).length) throw new SemanticUnavailable("The embedding model files are still incomplete after download.");
  }
  const spec: Partial<ModelSpec> = cfg.embedModelDir ? {} : modelSpec(cfg.embedModel);
  const d = modelDir(cfg);
  const onnx = ["onnx/model_quantized.onnx", "onnx/model.onnx", "model.onnx"].map((p) => join(d, p)).find(isFile)!;
  (ort as any).env.logLevel = "error";
  const opts: Record<string, unknown> = { logSeverityLevel: 3, executionProviders: ["cpu"] };
  if (cfg.embedThreads) opts.intraOpNumThreads = cfg.embedThreads;
  const session = await (ort as any).InferenceSession.create(onnx, opts);
  const tcPath = join(d, "tokenizer_config.json");
  const tokenizer = new tok.Tokenizer(JSON.parse(readFileSync(join(d, "tokenizer.json"), "utf8")), existsSync(tcPath) ? JSON.parse(readFileSync(tcPath, "utf8")) : {});
  const dims = spec.dims ?? 768;
  return new OnnxEmbedder(modelId(cfg), dims, ort, session, tokenizer, new Set(session.inputNames), spec.max_tokens ?? 512, poolingFromDir(d, spec.pooling ?? "mean"), cfg.embedBatch);
}

export function resetEmbedders(): void {
  embedders.clear();
}
