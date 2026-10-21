// video-gaga assets — maps, environments and models for three.js shots.
//
//   gaga asset find <words…> [--type hdris|textures|models] [--limit 12]
//       Search Poly Haven (CC0) by name, tag and category: ids to fetch.
//
//   gaga asset <project> polyhaven:<id> [--res 1k]
//       A CC0 asset from Poly Haven into <project>/assets/, credited in
//       assets/CREDITS.md. HDRIs land as assets/<id>.hdr (gl.hdri), textures
//       as a PBR folder assets/<id>/ (gl.pbr), models as assets/<id>/<id>.gltf
//       with their textures (gl.model). Downloads are cached once for every
//       project in ~/.cache/video-gaga/assets.
//
//   gaga asset restore <project> [--force]
//       Rebuild assets/ from assets/assets.json: fetch what came from Poly
//       Haven, derive maps from the pictures kept in assets/src/. `render`,
//       `still` and `moodboard` run it first, so a fresh clone renders.
//
//   gaga texture <project> --prompt "<surface>" --name <name> [--matcap]
//       Generates the albedo (or, with --matcap, a lit sphere) with Codex CLI's
//       image generation, keeps the picture in build/generated/, and writes
//       assets/<name>/ (or assets/<name>.png) with the prompt in CREDITS.md.
//       Any other image model works too: generate the picture, then the form below.
//
//   gaga texture <image> [--out dir] [--size 1024] [--seamless] [--delight]
//                        [--strength 2] [--rough 0.45,0.85] [--invert] [--ao 1]
//                        [--neutral [0.82]] [--only albedo,normal,…]
//       A colour image (a generated albedo, a photo of a surface) into the same
//       PBR folder: albedo.jpg, plus normal, roughness and ao derived from its
//       brightness. Good for paper, ceramic, plaster, fabric, painted and
//       hand-made surfaces; for wood, stone and metal read close up, a scanned
//       set (`gaga asset`) is better. --neutral makes the albedo grey (mean
//       0.82) so material.color tints it, for colourways; --only albedo with
//       --out on a scanned set's folder neutralises its colour and keeps its maps.
//
// Images are decoded and encoded with ffmpeg; the maths is plain JS, so the
// same input always gives the same maps.
//
// What a project keeps in git (assets/.gitignore says so): assets.json (where
// each asset came from and how it was processed), CREDITS.md, and src/, the
// pictures that can't be fetched again (a generated albedo, a matcap, a photo).
// Everything else in assets/ is rebuilt by `gaga asset restore`.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const API = 'https://api.polyhaven.com';
const cacheDir = () => path.join(process.env.VIDEO_GAGA_CACHE || path.join(os.homedir(), '.cache', 'video-gaga'), 'assets');

// API answers are cached too, so an asset fetched once can be added to another
// project offline. A 404 is "no such asset"; anything else is the network.
async function getJSON(url) {
  const cached = path.join(cacheDir(), 'api', encodeURIComponent(url.replace(/^https?:\/\//, '')) + '.json');
  let r;
  try { r = await fetch(url, { headers: { 'User-Agent': 'video-gaga' }, signal: AbortSignal.timeout(20000) }); }
  catch (e) {
    if (fs.existsSync(cached)) return JSON.parse(fs.readFileSync(cached, 'utf8'));
    throw Object.assign(new Error(`can't reach ${new URL(url).hostname} (${e.cause?.code || e.message}); check the network`), { network: true });
  }
  if (!r.ok) throw Object.assign(new Error(`${url}: HTTP ${r.status}`), { status: r.status });
  const json = await r.json();
  fs.mkdirSync(path.dirname(cached), { recursive: true });
  fs.writeFileSync(cached, JSON.stringify(json));
  return json;
}

// a file table entry ({ url, size }) into file, through the shared cache
async function download(f, file) {
  const cached = path.join(cacheDir(), new URL(f.url).hostname, decodeURIComponent(new URL(f.url).pathname));
  if (!fs.existsSync(cached) || (f.size && fs.statSync(cached).size !== f.size)) {
    const r = await fetch(f.url, { headers: { 'User-Agent': 'video-gaga' } });
    if (!r.ok) throw new Error(`${f.url}: HTTP ${r.status}`);
    fs.mkdirSync(path.dirname(cached), { recursive: true });
    fs.writeFileSync(cached + '.part', Buffer.from(await r.arrayBuffer()));
    fs.renameSync(cached + '.part', cached);
  }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.copyFileSync(cached, file);
}

const TYPES = { 0: 'hdri', 1: 'texture', 2: 'model' };
// rank Poly Haven assets for a query against the id, name, tags and categories:
// more words matched first, then closer matches, then the most downloaded
export function rankAssets(list, words) {
  const q = words.map((w) => w.toLowerCase());
  return Object.entries(list).map(([id, a]) => {
    const fields = [id, a.name, ...(a.tags || []), ...(a.categories || [])].map((x) => String(x).toLowerCase());
    let matched = 0, score = 0;
    for (const w of q) {
      const hit = fields.reduce((b, f) => Math.max(b, f === w ? 3 : f.split(/[\s_-]+/).includes(w) ? 2 : f.includes(w) ? 1 : 0), 0);
      if (hit) { matched++; score += hit; }
    }
    if (!matched) return null;
    return { id, name: a.name, type: TYPES[a.type] || '?', categories: a.categories || [], matched, score, downloads: a.download_count || 0 };
  }).filter(Boolean).sort((a, b) => b.matched - a.matched || b.score - a.score || b.downloads - a.downloads);
}

async function findCmd(opts, { log, die }) {
  const words = opts._.slice(2);
  if (!words.length) die('usage: gaga asset find <words…> [--type hdris|textures|models] [--limit 12]');
  const t = opts.type ? String(opts.type) : 'all';
  if (!['all', 'hdris', 'textures', 'models'].includes(t)) die('--type is hdris, textures or models');
  const hits = rankAssets(await getJSON(`${API}/assets?t=${t}`), words).slice(0, Number(opts.limit || 12));
  if (!hits.length) die(`nothing on Poly Haven for "${words.join(' ')}"${t === 'all' ? '' : ` in ${t}`}: try a broader word`);
  for (const h of hits) log(`polyhaven:${h.id.padEnd(30)} ${h.type.padEnd(8)} ${h.name}  (${h.categories.slice(0, 4).join(', ')})`);
  log(`\nfetch: gaga asset <project> polyhaven:<id>   preview: https://polyhaven.com/a/<id>`);
}

// a file from a resolution table: the one asked for, else the nearest smaller, else the smallest
function pick(table, res, fmt) {
  if (!table) return null;
  const order = Object.keys(table).sort((a, b) => parseInt(a) - parseInt(b));
  const want = parseInt(res);
  const key = table[res] ? res : [...order].reverse().find((k) => parseInt(k) <= want) || order[0];
  return table[key]?.[fmt] ? { res: key, ...table[key][fmt] } : null;
}

function credit(assetsDir, line) {
  const f = path.join(assetsDir, 'CREDITS.md');
  const head = '# Asset credits\n\n';
  const cur = fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : head;
  if (!cur.includes(line)) fs.writeFileSync(f, cur.trimEnd() + (cur.trim() === head.trim() ? '\n\n' : '\n') + line + '\n');
}

function flatImage(file, hex = 'white') {
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-f', 'lavfi', '-i', `color=${hex}:s=8x8`, '-frames:v', '1', '-q:v', '2', file]);
  if (r.status !== 0) throw new Error(`ffmpeg could not write ${file}`);
}

// a Poly Haven asset into assets/ → { key (its path in assets/), use, name }
async function fetchPolyhaven(assets, id, res, log) {
  const info = await getJSON(`${API}/info/${id}`).catch((e) => { throw e.status === 404 ? new Error(`Poly Haven has no asset "${id}": find one with gaga asset find <words>`) : e; });
  const files = await getJSON(`${API}/files/${id}`);
  const authors = Object.keys(info.authors || {}).join(', ') || 'Poly Haven';
  let where, use;
  if (info.type === 0) {
    const f = pick(files.hdri, res, 'hdr');
    if (!f) throw new Error(`${id}: no .hdr file`);
    where = path.join(assets, `${id}.hdr`);
    log(`▸ HDRI ${info.name} (${f.res}, ${(f.size / 1e6).toFixed(1)} MB)`);
    await download(f, where);
    use = `world.environment = gl.hdri('assets/${id}.hdr')`;
  } else if (info.type === 1) {
    const out = path.join(assets, id);
    const keys = Object.keys(files);
    const albedo = ['Diffuse', 'diff', ...keys.filter((k) => /^col/i.test(k)).sort()].find((k) => files[k]);
    // a metalness map only for metals: other sets' "Metal" maps are not always black
    const metal = (info.categories || []).some((c) => /metal/i.test(c));
    const want = { albedo, normal: 'nor_gl', roughness: 'Rough', ao: 'AO', ...(metal ? { metalness: 'Metal' } : {}) };
    if (!albedo || !files.nor_gl || !files.Rough) throw new Error(`${id}: missing a colour, normal (GL) or roughness map (has: ${keys.join(', ')})`);
    log(`▸ texture ${info.name} (${res})`);
    for (const [name, key] of Object.entries(want)) {
      const target = path.join(out, `${name}.jpg`);
      const f = key && pick(files[key], res, 'jpg');
      if (f) await download(f, target);
      else if (name === 'ao') flatImage(target);
      if (f || name === 'ao') log(`  ${name}.jpg${f ? '' : ' (flat: the set has no AO)'}`);
    }
    where = out;
    use = `new THREE.MeshPhysicalMaterial({ ...gl.pbr('assets/${id}', { repeat: 2${metal && files.Metal ? ', metalness: true' : ''} }) })`;
  } else if (info.type === 2) {
    const out = path.join(assets, id);
    const g = pick(files.gltf, res, 'gltf');
    if (!g) throw new Error(`${id}: no glTF file`);
    log(`▸ model ${info.name} (${g.res})`);
    await download(g, path.join(out, `${id}.gltf`));
    for (const [rel, f] of Object.entries(g.include || {})) {
      const target = path.resolve(out, rel);
      if (!target.startsWith(out + path.sep)) throw new Error(`${id}: refusing a file outside the asset folder: ${rel}`);
      await download(f, target);
    }
    where = out;
    use = `world.add(gl.model('assets/${id}/${id}.gltf', { shadows: true }))`;
  } else throw new Error(`${id}: unknown asset type ${info.type}`);
  const key = path.relative(assets, where).split(path.sep).join('/');
  credit(assets, `- \`${key}\`: "${info.name}" by ${authors}, Poly Haven, CC0 (https://polyhaven.com/a/${id})`);
  return { key, use, where };
}

// ---------------------------------------------------------------------------
// the manifest: assets/assets.json
// ---------------------------------------------------------------------------
const IGNORE = `# Fetched or derived from assets.json by \`gaga asset restore\` (render, still and
# moodboard run it too). Kept in git: this file, assets.json, CREDITS.md and src/,
# the pictures that can't be fetched again.
/*
!/.gitignore
!/assets.json
!/CREDITS.md
!/src/
`;
export function readManifest(assets) {
  const f = path.join(assets, 'assets.json');
  return fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : {};
}
export function writeManifest(assets, m) {
  fs.mkdirSync(assets, { recursive: true });
  const sorted = Object.fromEntries(Object.keys(m).sort().map((k) => [k, m[k]]));
  fs.writeFileSync(path.join(assets, 'assets.json'), JSON.stringify(sorted, null, 2) + '\n');
  if (!fs.existsSync(path.join(assets, '.gitignore'))) fs.writeFileSync(path.join(assets, '.gitignore'), IGNORE);
}
function record(assets, key, entry) {
  const m = readManifest(assets);
  m[key] = { ...(m[key] || {}), ...entry };
  for (const k of Object.keys(m[key])) if (m[key][k] == null) delete m[key][k];
  writeManifest(assets, m);
}
// the project's assets/ folder that p sits in (its parent holds video.html), or null
function assetsDirOf(p) {
  for (let d = path.resolve(p); d !== path.dirname(d); d = path.dirname(d)) {
    if (path.basename(d) === 'assets' && fs.existsSync(path.join(path.dirname(d), 'video.html'))) return d;
  }
  return null;
}
// the gaga texture flags that change the maps, as one string for the manifest
const TEXTURE_FLAGS = ['size', 'seamless', 'delight', 'neutral', 'strength', 'rough', 'invert', 'ao', 'only'];
const textureFlags = (o) => TEXTURE_FLAGS.filter((k) => o[k] != null && o[k] !== false).map((k) => (o[k] === true ? `--${k}` : `--${k} ${o[k]}`)).join(' ');
function parseFlags(str = '') {
  const o = {}, t = String(str).trim().split(/\s+/).filter(Boolean);
  for (let i = 0; i < t.length; i++) {
    if (!t[i].startsWith('--')) continue;
    const k = t[i].slice(2);
    if (t[i + 1] && !t[i + 1].startsWith('--')) o[k] = t[++i];
    else o[k] = true;
  }
  return o;
}

// Rebuild what assets.json names and assets/ lacks (all of it with force).
// → { restored: [key], failed: [{ key, error }] }
export async function restoreAssets(dir, { log = () => {}, force = false } = {}) {
  const assets = path.join(dir, 'assets');
  const m = readManifest(assets);
  const restored = [], failed = [];
  for (const [key, e] of Object.entries(m)) {
    const target = path.join(assets, key);
    const present = fs.existsSync(target) && (!fs.statSync(target).isDirectory() || fs.readdirSync(target).length > 0);
    if (present && !force) continue;
    try {
      const ph = /^polyhaven:([a-z0-9_]+)$/i.exec(e.source || '');
      if (ph) {
        await fetchPolyhaven(assets, ph[1], e.res || '1k', log);
        // a scanned set's albedo made neutral (or otherwise reworked) in place
        if (e.texture) deriveTexture(path.join(target, 'albedo.jpg'), target, parseFlags(e.texture), log);
      } else if (e.source?.startsWith('src/')) {
        const src = path.join(assets, e.source);
        if (!fs.existsSync(src)) throw new Error(`${e.source} is missing: it is the original picture and can't be fetched (is it in git?)`);
        if (e.texture != null) deriveTexture(src, target, parseFlags(e.texture), log);
        else { fs.mkdirSync(path.dirname(target), { recursive: true }); fs.copyFileSync(src, target); }
      } else throw new Error(`unknown source "${e.source}"`);
      restored.push(key);
    } catch (err) { failed.push({ key, error: err.message }); }
  }
  return { restored, failed };
}

export async function assetCmd(opts, { log, die, resolveProject }) {
  if (opts._[1] === 'find') return findCmd(opts, { log, die });
  if (opts._[1] === 'restore') {
    const { dir } = resolveProject(opts._[2]);
    if (!Object.keys(readManifest(path.join(dir, 'assets'))).length) { log('nothing to restore: no assets/assets.json'); return; }
    const { restored, failed } = await restoreAssets(dir, { log, force: !!opts.force });
    for (const f of failed) log(`✖ ${f.key}: ${f.error}`);
    log(`${failed.length ? '✖' : '✔'} ${restored.length} restored${failed.length ? `, ${failed.length} failed` : ''}${restored.length || failed.length ? '' : ' (all present)'}`);
    if (failed.length) process.exitCode = 1;
    return;
  }
  const { dir } = resolveProject(opts._[1]);
  const ref = opts._[2] || die('usage: gaga asset <project> polyhaven:<id> [--res 1k]  ·  gaga asset find <words>  ·  gaga asset restore <project>');
  const m = /^(?:polyhaven:|https?:\/\/polyhaven\.com\/a\/)([a-z0-9_]+)$/i.exec(ref);
  if (!m) die(`not a Poly Haven asset: ${ref} (use polyhaven:<id>, the id from polyhaven.com/a/<id>)`);
  const res = String(opts.res || '1k');
  const assets = path.join(dir, 'assets');
  const { key, use, where } = await fetchPolyhaven(assets, m[1], res, log).catch((e) => die(e.message));
  record(assets, key, { source: `polyhaven:${m[1]}`, res: res === '1k' ? undefined : res, texture: undefined });
  log(`✔ ${path.relative(process.cwd(), where)}  (recorded in assets/assets.json)\n  ${use}`);
}

// ---------------------------------------------------------------------------
// gaga texture: an image → albedo, normal, roughness, ao
// ---------------------------------------------------------------------------
function readRGB(file, size) {
  const vf = size ? ['-vf', `scale=${size}:${size}:flags=lanczos`] : [];
  const probe = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', file], { encoding: 'utf8' });
  if (probe.status !== 0) throw new Error(`not an image: ${file}`);
  const [w0, h0] = probe.stdout.trim().split(',').map(Number);
  const [w, h] = size ? [size, size] : [w0, h0];
  const r = spawnSync('ffmpeg', ['-v', 'error', '-i', file, ...vf, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { maxBuffer: 1 << 30 });
  if (r.status !== 0) throw new Error(`ffmpeg could not read ${file}`);
  return { w, h, px: new Uint8Array(r.stdout.buffer, r.stdout.byteOffset, w * h * 3) };
}

function writeRGB(file, w, h, px) {
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', `${w}x${h}`, '-i', '-', '-q:v', '2', file], { input: Buffer.from(px.buffer, px.byteOffset, px.length) });
  if (r.status !== 0) throw new Error(`ffmpeg could not write ${file}`);
}

// separable box blur with wrap-around (textures tile), on one channel
function boxBlur(src, w, h, r) {
  if (r < 1) return Float32Array.from(src);
  const tmp = new Float32Array(w * h), out = new Float32Array(w * h), n = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    let acc = 0;
    for (let k = -r; k <= r; k++) acc += src[y * w + ((k % w) + w) % w];
    for (let x = 0; x < w; x++) {
      tmp[y * w + x] = acc / n;
      acc += src[y * w + (x + r + 1) % w] - src[y * w + ((x - r) % w + w) % w];
    }
  }
  for (let x = 0; x < w; x++) {
    let acc = 0;
    for (let k = -r; k <= r; k++) acc += tmp[(((k % h) + h) % h) * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = acc / n;
      acc += tmp[((y + r + 1) % h) * w + x] - tmp[(((y - r) % h + h) % h) * w + x];
    }
  }
  return out;
}
const blur = (a, w, h, r) => boxBlur(boxBlur(a, w, h, r), w, h, r); // ≈ gaussian

const toLin = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

export function deriveMaps(img, o = {}) {
  const { w, h } = img;
  const N = w * h;
  const ch = [0, 1, 2].map((c) => { const a = new Float32Array(N); for (let i = 0; i < N; i++) a[i] = img.px[i * 3 + c] / 255; return a; });

  // seamless: cross-fade with a copy shifted by half, whose wrap seam sits in
  // the middle where the original wins
  if (o.seamless) {
    const wt = (u) => { const d = Math.min(u, 1 - u) * 2; return d >= 0.5 ? 1 : (d / 0.5) ** 2 * (3 - 2 * (d / 0.5)); };
    for (const a of ch) {
      const b = Float32Array.from(a);
      for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
        const k = wt(x / w) * wt(y / h), s = b[((y + (h >> 1)) % h) * w + ((x + (w >> 1)) % w)];
        a[y * w + x] = b[y * w + x] * k + s * (1 - k);
      }
    }
  }
  // delight: divide out large-scale shading baked into the picture (a generated
  // or photographed surface is rarely lit evenly), keeping its mean colour
  if (o.delight) {
    const r = Math.max(4, Math.round(Math.min(w, h) / 8));
    for (const a of ch) {
      let mean = 0;
      for (let i = 0; i < N; i++) mean += a[i];
      mean /= N;
      const low = blur(a, w, h, r);
      for (let i = 0; i < N; i++) a[i] = Math.min(1, a[i] * (mean / Math.max(1e-3, low[i])));
    }
  }

  // neutral: grey with a set mean, so material.color tints it (colourways)
  // instead of fighting the picture's own colour
  if (o.neutral) {
    const lum = new Float32Array(N);
    let mean = 0;
    for (let i = 0; i < N; i++) { lum[i] = 0.2126 * ch[0][i] + 0.7152 * ch[1][i] + 0.0722 * ch[2][i]; mean += lum[i]; }
    mean /= N;
    const k = Number(o.neutral === true ? 0.82 : o.neutral) / Math.max(1e-3, mean);
    for (const a of ch) for (let i = 0; i < N; i++) a[i] = Math.min(1, lum[i] * k);
  }

  // height from linear luminance, stretched to 0..1 (dark = low)
  let hgt = new Float32Array(N), lo = Infinity, hi = -Infinity;
  for (let i = 0; i < N; i++) {
    const v = 0.2126 * toLin(ch[0][i]) + 0.7152 * toLin(ch[1][i]) + 0.0722 * toLin(ch[2][i]);
    hgt[i] = o.invert ? -v : v;
  }
  hgt = blur(hgt, w, h, Math.max(1, Math.round(w / 1024)));
  for (const v of hgt) { if (v < lo) lo = v; if (v > hi) hi = v; }
  for (let i = 0; i < N; i++) hgt[i] = (hgt[i] - lo) / Math.max(1e-6, hi - lo);

  const strength = Number(o.strength ?? 2) * (w / 1024);
  const [rMin, rMax] = String(o.rough ?? '0.45,0.85').split(',').map(Number);
  const aoAmt = Number(o.ao ?? 1);
  const cavity = blur(hgt, w, h, Math.max(2, Math.round(w / 128)));
  const albedo = new Uint8Array(N * 3), normal = new Uint8Array(N * 3), rough = new Uint8Array(N * 3), ao = new Uint8Array(N * 3);
  const at = (x, y) => hgt[((y + h) % h) * w + ((x + w) % w)];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = y * w + x;
    // Sobel; OpenGL convention (green = up the image), as three.js expects
    const dx = (at(x + 1, y - 1) + 2 * at(x + 1, y) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x - 1, y) + at(x - 1, y + 1));
    const dy = (at(x - 1, y + 1) + 2 * at(x, y + 1) + at(x + 1, y + 1)) - (at(x - 1, y - 1) + 2 * at(x, y - 1) + at(x + 1, y - 1));
    let nx = -dx * strength, ny = dy * strength, nz = 1;
    const l = Math.hypot(nx, ny, nz);
    nx /= l; ny /= l; nz /= l;
    normal.set([(nx * 0.5 + 0.5) * 255, (ny * 0.5 + 0.5) * 255, (nz * 0.5 + 0.5) * 255], i * 3);
    // high points are worn smooth, recesses stay rough
    const r = (rMax + (rMin - rMax) * hgt[i]) * 255;
    rough.set([r, r, r], i * 3);
    const a = Math.max(0, Math.min(1, 1 - aoAmt * 3 * Math.max(0, cavity[i] - hgt[i]))) * 255;
    ao.set([a, a, a], i * 3);
    albedo.set([ch[0][i] * 255, ch[1][i] * 255, ch[2][i] * 255], i * 3);
  }
  return { albedo, normal, roughness: rough, ao };
}

// How a surface is asked for: the surface itself, not a picture of it. A
// matcap is one lit sphere, which carries the whole material (MeshMatcapMaterial).
const SURFACE = (p) => `albedo (base colour) map of ${p}. Flat orthographic top-down view filling the whole square frame, perfectly even diffuse lighting, no shadows, no highlights, no reflections, no vignette, no perspective, no objects, no borders, seamless tileable.`;
const MATCAP = (p) => `a matcap: one perfect sphere of ${p}, seen straight on through an orthographic camera, centred and touching all four edges of the square frame, on pure black, lit by a soft key from the upper left and a thin rim from behind, no cast shadow, no floor, no text.`;

// one image from Codex CLI's image generation into file (absolute), or null
function codexImage(prompt, file, log) {
  if (spawnSync('codex', ['--version'], { stdio: 'ignore' }).status !== 0) return { error: 'Codex CLI is not installed' };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.rmSync(file, { force: true });
  log('▸ generating with Codex (about a minute)…');
  const r = spawnSync('codex', ['exec', '--skip-git-repo-check', '--ephemeral', '--enable', 'image_generation', '-s', 'workspace-write', '-C', path.dirname(file),
    `Use your image generation tool to create ONE square image and save it as ${file}. Subject: ${prompt} Do nothing else; reply with the saved path.`],
  { encoding: 'utf8', timeout: 600000, maxBuffer: 1 << 26 });
  if (!fs.existsSync(file)) return { error: `Codex did not save ${path.basename(file)}${r.status ? ` (exit ${r.status})` : ''}: ${(r.stderr || r.stdout || '').trim().split('\n').slice(-3).join(' / ')}` };
  return { file };
}

async function generateCmd(opts, { log, die, resolveProject }) {
  const { dir } = resolveProject(opts._[1]);
  const name = String(opts.name || die('--name <name> is the folder in assets/ (e.g. --name stoneware)'));
  if (!/^[a-z0-9][a-z0-9_-]*$/i.test(name)) die('--name: letters, digits, - and _ only');
  const prompt = String(opts.prompt);
  const assets = path.join(dir, 'assets');
  const raw = path.join(dir, 'build', 'generated', `${name}${opts.matcap ? '-matcap' : ''}.png`);
  const g = codexImage(opts.matcap ? MATCAP(prompt) : SURFACE(prompt), raw, log);
  if (g.error) die(`${g.error}.\n  Generate it with any image model instead, asking for: ${opts.matcap ? MATCAP(prompt) : SURFACE(prompt)}\n  then: ${opts.matcap
    ? `save it as ${path.relative(process.cwd(), path.join(assets, `${name}.png`))}`
    : `gaga texture <image> --out ${path.relative(process.cwd(), path.join(assets, name))} --seamless`} and add the prompt to assets/CREDITS.md`);
  if (opts.matcap) {
    const out = path.join(assets, `${name}.png`), kept = path.join(assets, 'src', `${name}.png`);
    fs.mkdirSync(path.dirname(kept), { recursive: true });
    const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-i', raw, '-vf', 'scale=512:512:flags=lanczos', kept]);
    if (r.status !== 0) die(`ffmpeg could not write ${kept}`);
    fs.copyFileSync(kept, out);
    record(assets, `${name}.png`, { source: `src/${name}.png`, prompt });
    credit(assets, `- \`${name}.png\`: matcap generated with Codex image generation, prompt: "${prompt}"`);
    log(`✔ ${path.relative(process.cwd(), out)}  (the picture: ${path.relative(process.cwd(), raw)})\n  new THREE.MeshMatcapMaterial({ matcap: gl.map('assets/${name}.png') })`);
    return;
  }
  const flags = textureFlags(opts);
  fs.mkdirSync(assets, { recursive: true });
  if (!fs.existsSync(path.join(dir, 'video.html'))) die(`no video.html in ${dir}`);
  await textureCmd({ ...opts, _: ['texture', raw], out: path.join(assets, name), prompt: undefined }, { log, die, resolveProject });
  record(assets, name, { prompt });
  credit(assets, `- \`${name}\`: albedo generated with Codex image generation, prompt: "${prompt}"; maps by \`gaga texture${flags ? ' ' + flags : ''}\``);
  log(`  look at the albedo before you use it: a highlight or shadow in it will fight the scene's light (${path.relative(process.cwd(), raw)})`);
}

// an image → the PBR folder out (albedo, normal, roughness, ao)
function deriveTexture(src, out, opts, log) {
  const size = opts.size === 'source' ? 0 : Number(opts.size || 1024);
  const img = readRGB(src, size);
  log(`▸ ${path.basename(src)} → ${img.w}×${img.h}${opts.seamless ? ', seamless' : ''}${opts.delight ? ', delit' : ''}${opts.neutral ? ', neutral' : ''}`);
  const maps = deriveMaps(img, opts);
  const only = opts.only ? String(opts.only).split(',') : null;
  fs.mkdirSync(out, { recursive: true });
  for (const [name, px] of Object.entries(maps)) {
    if (only && !only.includes(name)) continue;
    writeRGB(path.join(out, `${name}.jpg`), img.w, img.h, px);
    log(`  ${name}.jpg`);
  }
}

// keep the original picture in assets/src/ (at the size the maps are made at,
// as a jpg: it is what git keeps) → its path relative to assets/
function keepSource(assets, src, name, size) {
  const rel = `src/${name}.jpg`, dst = path.join(assets, rel);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  const vf = size ? ['-vf', `scale=${size}:${size}:flags=lanczos`] : [];
  const r = spawnSync('ffmpeg', ['-y', '-v', 'error', '-i', src, ...vf, '-q:v', '2', dst]);
  if (r.status !== 0) throw new Error(`ffmpeg could not write ${dst}`);
  return rel;
}

export async function textureCmd(opts, { log, die, resolveProject }) {
  if (opts.prompt) return generateCmd(opts, { log, die, resolveProject });
  let src = path.resolve(opts._[1] || die('usage: gaga texture <image> [--out dir] [--size 1024] [--seamless] [--delight]  ·  gaga texture <project> --prompt "<surface>" --name <name> [--matcap]'));
  if (!fs.existsSync(src)) die(`not found: ${src}`);
  const out = path.resolve(opts.out || path.join(path.dirname(src), path.basename(src, path.extname(src))));
  const assets = assetsDirOf(out);
  const key = assets && path.relative(assets, out).split(path.sep).join('/');
  const flags = textureFlags(opts);
  if (assets) {
    const entry = readManifest(assets)[key];
    if (entry?.source?.startsWith('polyhaven:') && path.dirname(src) === out) {
      // reworking a fetched set in place (e.g. --neutral --only albedo): restore repeats it after the download
      deriveTexture(src, out, opts, log);
      record(assets, key, { texture: flags });
    } else {
      // the picture goes into src/ and the maps are made from that copy, so a restore makes the same maps
      const size = opts.size === 'source' ? 0 : Number(opts.size || 1024);
      const kept = src.startsWith(path.join(assets, 'src') + path.sep) ? path.relative(assets, src).split(path.sep).join('/') : keepSource(assets, src, key.replace(/\//g, '_'), size);
      deriveTexture(path.join(assets, kept), out, opts, log);
      record(assets, key, { source: kept, texture: flags });
    }
  } else deriveTexture(src, out, opts, log);
  // the path gl.pbr() takes is relative to the composition's video.html
  const rel = assets ? `assets/${key}` : path.relative(process.cwd(), out).split(path.sep).join('/');
  log(`✔ ${path.relative(process.cwd(), out)}${assets ? '  (recorded in assets/assets.json)' : ''}\n  new THREE.MeshPhysicalMaterial({ ...gl.pbr('${rel}') })`);
}
