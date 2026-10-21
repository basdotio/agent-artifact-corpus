// Surfaces for three.js shots: `gaga texture` derives maps that tile and tint,
// the renderer waits for maps, HDRIs and models read from file://, and a file
// that fails to load stops the render instead of leaving a plain surface.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { deriveMaps, rankAssets } from '../scripts/assets.mjs';

const ROOT = new URL('..', import.meta.url).pathname;
const gaga = path.join(ROOT, 'scripts', 'gaga.mjs');
let chromium;
try { ({ chromium } = await import('playwright')); } catch { /* skipped below */ }

const img = (w, h, f) => {
  const px = new Uint8Array(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) px.set(f(x, y), (y * w + x) * 3);
  return { w, h, px };
};
const at = (m, w, x, y) => Array.from(m.slice((y * w + x) * 3, (y * w + x) * 3 + 3));

test('a flat picture gives a flat normal map, full ao and one roughness', () => {
  const m = deriveMaps(img(32, 32, () => [180, 160, 140]));
  for (const [x, y] of [[0, 0], [16, 9], [31, 31]]) {
    assert.deepEqual(at(m.normal, 32, x, y), [127, 127, 255]);
    assert.equal(at(m.ao, 32, x, y)[0], 255);
  }
  assert.equal(new Set(Array.from(m.roughness)).size, 1);
});

test('normals follow the OpenGL convention three.js expects', () => {
  // brighter (higher) to the right and towards the top of the image
  const m = deriveMaps(img(64, 64, (x, y) => [x * 2 + (63 - y), x * 2 + (63 - y), x * 2 + (63 - y)]));
  const [r, g] = at(m.normal, 64, 32, 32);
  assert.ok(r < 127, `slope rising to the right tilts the normal left (r=${r})`);
  assert.ok(g < 127, `slope rising up the image tilts the normal down (g=${g})`);
});

test('--seamless makes opposite edges meet', () => {
  const w = 64;
  const ramp = img(w, w, (x) => [x * 4, x * 4, x * 4]); // a hard seam where x wraps
  const jump = (m) => Math.abs(at(m.albedo, w, 0, 20)[0] - at(m.albedo, w, w - 1, 20)[0]);
  assert.ok(jump(deriveMaps(ramp)) > 200);
  assert.ok(jump(deriveMaps(ramp, { seamless: true })) < 20);
});

test('--neutral gives a grey albedo with the asked mean, so material.color tints it', () => {
  const m = deriveMaps(img(32, 32, (x, y) => [40 + x, 90 + y, 200]), { neutral: 0.8 });
  let sum = 0;
  for (let i = 0; i < m.albedo.length; i += 3) {
    assert.ok(m.albedo[i] === m.albedo[i + 1] && m.albedo[i + 1] === m.albedo[i + 2]);
    sum += m.albedo[i];
  }
  assert.ok(Math.abs(sum / (m.albedo.length / 3) / 255 - 0.8) < 0.01);
});

test('gaga texture writes the folder gl.pbr reads', { skip: spawnSync('ffmpeg', ['-version']).status !== 0 && 'ffmpeg not installed' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-texture-'));
  const src = path.join(dir, 'speckle.png');
  spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'cellauto=s=128x128:rule=110,format=rgb24', '-frames:v', '1', src]);
  const r = spawnSync('node', [gaga, 'texture', src, '--size', '128', '--seamless'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  for (const f of ['albedo', 'normal', 'roughness', 'ao']) assert.ok(fs.existsSync(path.join(dir, 'speckle', `${f}.jpg`)), f);
});

test('a project keeps the picture and the recipe; restore rebuilds the same maps', { skip: spawnSync('ffmpeg', ['-version']).status !== 0 && 'ffmpeg not installed' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-manifest-'));
  fs.writeFileSync(path.join(dir, 'video.html'), '<!doctype html>');
  const pic = path.join(dir, 'gen.png');
  spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'cellauto=s=200x200:rule=30,format=rgb24', '-frames:v', '1', pic]);
  const assets = path.join(dir, 'assets');
  const r = spawnSync('node', [gaga, 'texture', pic, '--out', path.join(assets, 'speckle'), '--size', '128', '--seamless', '--neutral'], { encoding: 'utf8' });
  assert.equal(r.status, 0, r.stderr);
  assert.deepEqual(JSON.parse(fs.readFileSync(path.join(assets, 'assets.json'), 'utf8')), { speckle: { source: 'src/speckle.jpg', texture: '--size 128 --seamless --neutral' } });
  assert.ok(fs.existsSync(path.join(assets, 'src', 'speckle.jpg')));
  assert.match(fs.readFileSync(path.join(assets, '.gitignore'), 'utf8'), /^\/\*$[\s\S]*!\/assets\.json[\s\S]*!\/src\//m);
  const read = () => ['albedo', 'normal', 'roughness', 'ao'].map((m) => fs.readFileSync(path.join(assets, 'speckle', `${m}.jpg`)).toString('base64'));
  const made = read();
  fs.rmSync(path.join(assets, 'speckle'), { recursive: true });
  const back = spawnSync('node', [gaga, 'asset', 'restore', dir], { encoding: 'utf8' });
  assert.equal(back.status, 0, back.stdout + back.stderr);
  assert.deepEqual(read(), made, 'restored maps are byte-identical');
  // the original picture is the one thing restore can't make: it says so
  fs.rmSync(path.join(assets, 'speckle'), { recursive: true });
  fs.rmSync(path.join(assets, 'src'), { recursive: true });
  const lost = spawnSync('node', [gaga, 'asset', 'restore', dir], { encoding: 'utf8' });
  assert.equal(lost.status, 1);
  assert.match(lost.stdout, /speckle: src\/speckle\.jpg is missing: it is the original picture/);
});

test('asset search ranks by words matched, closeness, then downloads', () => {
  const list = {
    oak_veneer: { name: 'Oak Veneer', type: 1, tags: ['wood', 'oak'], categories: ['wood'], download_count: 5 },
    walnut_veneer: { name: 'Walnut Veneer', type: 1, tags: ['wood', 'walnut'], categories: ['wood'], download_count: 1 },
    dark_wood: { name: 'Dark Wood', type: 1, tags: ['planks'], categories: ['wood'], download_count: 99 },
    brick: { name: 'Brick', type: 1, tags: [], categories: ['brick'], download_count: 500 },
  };
  assert.deepEqual(rankAssets(list, ['walnut', 'wood']).map((a) => a.id), ['walnut_veneer', 'dark_wood', 'oak_veneer']);
  assert.equal(rankAssets(list, ['marble']).length, 0);
  assert.equal(rankAssets(list, ['walnut'])[0].type, 'texture');
});

test('without Codex, gaga texture --prompt says how to do it with any image model', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-prompt-'));
  fs.writeFileSync(path.join(dir, 'video.html'), '<!doctype html>');
  const env = { ...process.env, PATH: path.dirname(process.execPath) }; // node only: no codex, no ffmpeg
  const r = spawnSync(process.execPath, [gaga, 'texture', dir, '--prompt', 'speckled stoneware', '--name', 'glaze'], { encoding: 'utf8', env });
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /Codex CLI is not installed/);
  assert.match(r.stderr, /albedo \(base colour\) map of speckled stoneware.*seamless tileable/);
  assert.match(r.stderr, /gaga texture <image> --out .*assets\/glaze/);
});

test('the renderer waits for maps, an HDRI and a model, and reports a missing file', { skip: !chromium && 'playwright not installed', timeout: 120000 }, async (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-assets-'));
  fs.copyFileSync(path.join(ROOT, 'runtime', 'video-gaga.js'), path.join(dir, 'video-gaga.js'));
  // a 1×1 map, a 2×1 Radiance HDR and a one-triangle glTF with an external buffer
  fs.mkdirSync(path.join(dir, 'a'));
  spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', 'color=red:s=4x4', '-frames:v', '1', path.join(dir, 'a', 'red.png')]);
  fs.writeFileSync(path.join(dir, 'a', 'sky.hdr'), Buffer.concat([Buffer.from('#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 1 +X 2\n'), Buffer.from([128, 128, 128, 129, 128, 128, 128, 129])]));
  const tri = new Float32Array([0, 0, 0, 1, 0, 0, 0, 1, 0]);
  fs.writeFileSync(path.join(dir, 'a', 'tri.bin'), Buffer.from(tri.buffer));
  fs.writeFileSync(path.join(dir, 'a', 'tri.gltf'), JSON.stringify({
    asset: { version: '2.0' }, scene: 0, scenes: [{ nodes: [0] }], nodes: [{ mesh: 0 }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 } }] }],
    accessors: [{ bufferView: 0, componentType: 5126, count: 3, type: 'VEC3', min: [0, 0, 0], max: [1, 1, 0] }],
    bufferViews: [{ buffer: 0, byteLength: 36 }], buffers: [{ uri: 'tri.bin', byteLength: 36 }],
  }));
  const page = (missing) => `<!doctype html><html><head>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.min.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/"}}</script>
</head><body><script src="video-gaga.js"></script><script type="module">
import * as THREE from 'three';
const gl = CV.three(THREE, { width: 320, height: 180 });
const world = new THREE.Scene(), cam = new THREE.PerspectiveCamera(30, 16 / 9, 0.1, 10);
cam.position.set(0, 0, 3);
const red = gl.map('a/red.png');
${missing ? "gl.map('a/nope.jpg');" : ''}
gl.hdri('a/sky.hdr');
const model = gl.model('a/tri.gltf');
world.add(model, new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: red })));
window.probe = () => ({ map: !!red.image?.naturalWidth, env: !!gl.hdri('a/sky.hdr'), meshes: model.children.length });
CV.create({ width: 320, height: 180, fps: 30, scenes: [{ id: 'x', duration: 1, draw(ctx) { world.environment = gl.hdri('a/sky.hdr'); gl.render(ctx, world, cam); } }] });
</script></body></html>`;
  let browser;
  try { browser = await chromium.launch({ args: ['--allow-file-access-from-files', '--enable-unsafe-swiftshader'] }); }
  catch (e) { t.skip(`chromium unavailable: ${e.message.split('\n')[0]}`); return; }
  try {
    for (const missing of [false, true]) {
      fs.writeFileSync(path.join(dir, 'video.html'), page(missing));
      const p = await browser.newPage();
      await p.goto(`${pathToFileURL(path.join(dir, 'video.html')).href}?render=1`);
      await p.waitForFunction(() => !!window.__CV, null, { timeout: 60000 });
      await p.evaluate(() => window.__CV.ready());
      const info = await p.evaluate(() => ({ ...window.probe(), missing: window.__CV.missingAssets }));
      assert.deepEqual(info, { map: true, env: true, meshes: 1, missing: missing ? ['a/nope.jpg'] : [] });
      await p.close();
    }
  } finally { await browser.close(); }
  // gaga refuses to go on with a missing asset
  const r = spawnSync('node', [gaga, 'still', dir, '--at', '0.5'], { encoding: 'utf8' });
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /assets failed to load[\s\S]*a\/nope\.jpg/);
});
