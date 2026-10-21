#!/usr/bin/env node
// Turn one reference photo into a branded, uniform head-and-shoulders portrait
// for a lanyard badge, using Higgsfield (Grok Image 2.0 edit). Zero npm deps;
// uses `sharp` for the web-ready WebP only if the project already has it.
//
// Usage (run from the website project root):
//   node ~/.claude/skills/lanyard-badge/scripts/generate-portrait.mjs \
//     --photo path/to/person.jpg --logo path/to/logo.png --slug david \
//     [--out brand_assets/badge/generated] [--webp public/badge] \
//     [--shirt "deep navy short-sleeve polo shirt"] \
//     [--backdrop "soft light gray with a very subtle cool blue tint"] \
//     [--notes "keep the long straight highlighted hair"] [--no-logo] [--dry-run]
//
// Credentials: HF_CREDENTIALS="key-id:key-secret" from the environment, or from
// .env.local / .env in the current directory. Never printed.

import { readFile, writeFile, mkdir, access } from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";

const API = "https://api.higgsfield.ai";
const MODEL = "xai/grok-imagine-image-2.0";
const POLL_MS = 3000;
const MAX_WAIT_MS = 10 * 60 * 1000;

function parseArgs(argv) {
  const out = { flags: new Set() };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    const next = argv[i + 1];
    if (next === undefined || next.startsWith("--")) out.flags.add(key);
    else out[key] = argv[++i];
  }
  return out;
}

async function exists(p) {
  try {
    await access(p);
    return true;
  } catch {
    return false;
  }
}

async function loadCredentials() {
  if (process.env.HF_CREDENTIALS) return process.env.HF_CREDENTIALS.trim();
  for (const file of [".env.local", ".env"]) {
    if (!(await exists(file))) continue;
    const match = (await readFile(file, "utf8")).match(/^\s*HF_CREDENTIALS\s*=\s*["']?([^"'\r\n]+)/m);
    if (match) return match[1].trim();
  }
  return null;
}

const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };

function mimeFor(file) {
  const type = MIME[path.extname(file).toLowerCase()];
  if (!type) throw new Error(`Unsupported image type: ${file} (use png, jpg or webp)`);
  return type;
}

async function api(creds, method, url, body) {
  const res = await fetch(url.startsWith("http") ? url : `${API}${url}`, {
    method,
    headers: { Authorization: `Key ${creds}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) throw new Error("Higgsfield rejected the credentials (401). Check HF_CREDENTIALS.");
  if (res.status === 403) throw new Error("Not enough Higgsfield credits (403).");
  if (!res.ok) throw new Error(`Higgsfield ${method} ${url} failed (${res.status}): ${await res.text()}`);
  return res.json();
}

// Presigned upload; credentials only go to the Higgsfield API host, never to storage.
async function upload(creds, file) {
  const contentType = mimeFor(file);
  const slot = await api(creds, "POST", "/files/generate-upload-url", { content_type: contentType });
  const put = await fetch(slot.upload_url, { method: "PUT", headers: slot.upload_headers, body: await readFile(file) });
  if (!put.ok) throw new Error(`Upload of ${path.basename(file)} failed (${put.status}).`);
  return slot.public_url;
}

function buildPrompt({ shirt, backdrop, notes, withLogo }) {
  return [
    "Keep the exact face, identity, skin tone, hair and facial hair of the person in the first reference image.",
    notes ?? "",
    "Realistic professional corporate headshot, head-and-shoulders crop even if the reference is full-body,",
    "centered, eye-level camera, looking at the camera with a natural, approachable expression.",
    `Wearing a ${shirt} with a clean collar.`,
    withLogo
      ? "Use the second reference image only as the exact logo artwork: place it small and cleanly embroidered on the left chest of the shirt. Reproduce it faithfully; if unsure, keep it simple and small."
      : "The shirt is plain, with no logo or text.",
    `Plain seamless studio backdrop in ${backdrop}.`,
    "Soft even daylight studio lighting, natural skin texture, sharp face, shallow depth of field.",
    "No other text anywhere, no lanyard, no badge, no ID card, no props.",
  ]
    .filter(Boolean)
    .join(" ");
}

async function poll(creds, requestId) {
  const start = Date.now();
  for (;;) {
    if (Date.now() - start > MAX_WAIT_MS) throw new Error(`Timed out waiting for request ${requestId}.`);
    await new Promise((r) => setTimeout(r, POLL_MS));
    const s = await api(creds, "GET", `/requests/${requestId}/status`).catch((e) => {
      if (/\(5\d\d\)/.test(e.message)) return null; // transient server error: keep polling
      throw e;
    });
    if (s && ["completed", "failed", "nsfw", "canceled"].includes(s.status)) return s;
  }
}

async function toWebp(src, dir, slug) {
  try {
    const require = createRequire(path.join(process.cwd(), "package.json"));
    const sharp = require("sharp");
    await mkdir(dir, { recursive: true });
    const dest = path.join(dir, `${slug}.webp`);
    // 3:4 at 600x800, anchored to the top so the head is never cropped.
    await sharp(src).resize(600, 800, { fit: "cover", position: "top" }).webp({ quality: 82 }).toFile(dest);
    return dest;
  } catch (e) {
    console.warn(`(skipped WebP: ${e.code === "MODULE_NOT_FOUND" ? "sharp is not installed in this project" : e.message})`);
    return null;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const dryRun = args.flags.has("dry-run");
  const withLogo = !args.flags.has("no-logo") && Boolean(args.logo);
  const slug = args.slug ?? (args.photo ? path.parse(args.photo).name.toLowerCase().replace(/[^a-z0-9]+/g, "-") : "person");
  const outDir = args.out ?? "brand_assets/badge/generated";

  if (!args.photo) throw new Error("--photo is required.");
  if (!(await exists(args.photo))) throw new Error(`Photo not found: ${args.photo}`);
  mimeFor(args.photo);
  if (withLogo && !(await exists(args.logo))) throw new Error(`Logo not found: ${args.logo}`);

  const creds = await loadCredentials();
  if (!creds) throw new Error("HF_CREDENTIALS not found (env, .env.local or .env). Format: key-id:key-secret");
  if (creds.split(":").length !== 2) throw new Error("HF_CREDENTIALS must look like key-id:key-secret.");

  const prompt = buildPrompt({
    shirt: args.shirt ?? "deep navy short-sleeve polo shirt",
    backdrop: args.backdrop ?? "soft light gray with a very subtle cool blue tint",
    notes: args.notes,
    withLogo,
  });

  if (dryRun) {
    console.log(JSON.stringify({ ok: true, dryRun: true, model: MODEL, slug, photo: args.photo, logo: withLogo ? args.logo : null, outDir, prompt }, null, 2));
    return;
  }

  const imageUrls = [await upload(creds, args.photo)];
  if (withLogo) imageUrls.push(await upload(creds, args.logo));

  console.error(`Submitting ${slug} to ${MODEL}…`);
  const submitted = await api(creds, "POST", `/${MODEL}`, {
    prompt,
    image_urls: imageUrls,
    aspect_ratio: "3:4",
    resolution: "2k",
    quality: "medium",
  });
  const result = submitted.status === "completed" ? submitted : await poll(creds, submitted.request_id);
  const url = result.status === "completed" ? result.images?.[0]?.url : null;
  if (!url) throw new Error(`Request ${result.request_id} ended with status "${result.status}" and no image.`);

  const img = await fetch(url);
  // Fixed extensions only: never build a file name from a response header.
  const type = (img.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
  const ext = { "image/jpeg": "jpg", "image/webp": "webp" }[type] ?? "png";
  await mkdir(outDir, { recursive: true });
  const raw = path.join(outDir, `${slug}-${Date.now()}.${ext}`);
  await writeFile(raw, Buffer.from(await img.arrayBuffer()));
  const webp = args.webp ? await toWebp(raw, args.webp, slug) : null;

  console.log(JSON.stringify({ ok: true, slug, requestId: result.request_id, raw, webp }, null, 2));
}

main().catch((e) => {
  console.error(`Error: ${e.message}`);
  process.exit(1);
});
