// Deterministic frame renderer. Seeks the composition to exact times in headless Chrome, screenshots each
// (sub)frame and pipes into FFmpeg. Motion blur is real shutter integration: the composition says how many
// samples each moment needs (window.samplesAt), they are spread across the shutter and averaged in LINEAR
// light, like a sensor. Output: lossless FFV1 (the master); encode deliverables with tools/assemble.py.
//
//   node tools/render.js --from 0 --to 12 --out renders/master.mkv [--workers 4] [--scale 1] [--sub N]
//        [--shutter 0.5] [--maxsub 24] [--page comp/index.html] [--query only=s01,s02] [--frames dir]
//   node tools/render.js --stills 0.5,3,7.25 --dir renders/stills/a [--blur] [--cues audio/cues.json]
//
// Config (size, fps, duration) comes from comp/config.json. Chrome: puppeteer's own (or CHROME_PATH).
// FFmpeg: FFMPEG_PATH, else ffmpeg-static.
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const puppeteer = require("puppeteer");
const sharp = require("sharp");
const { start, ROOT } = require("./server");

function parseArgs(argv) {
  const a = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith("--")) {
      const key = k.slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[++i] : true;
      a[key] = v;
    }
  }
  return a;
}

const A = parseArgs(process.argv.slice(2));
const CONFIG = JSON.parse(fs.readFileSync(path.join(ROOT, "comp", "config.json"), "utf8"));
const W = CONFIG.width, H = CONFIG.height;
const FPS = Number(A.fps || CONFIG.fps || 60);
const SUB = Number(A.sub || 1);
const SHUTTER = Number(A.shutter || CONFIG.shutter || 0.5); // 0.5 = 180° shutter
const SCALE = Number(A.scale || 1);
const WORKERS = Number(A.workers || 4);
const PAGE = A.page || "comp/index.html";
const QUERY = A.query || "";
const FFMPEG = process.env.FFMPEG_PATH || require("ffmpeg-static");
const W_PX = Math.round(W * SCALE), H_PX = Math.round(H * SCALE);

async function launch() {
  return puppeteer.launch({
    executablePath: process.env.CHROME_PATH || undefined,
    headless: true,
    protocolTimeout: 600000,
    args: [
      "--force-color-profile=srgb",
      "--hide-scrollbars",
      "--mute-audio",
      "--font-render-hinting=none",
      "--disable-lcd-text",
      "--disable-background-timer-throttling",
      "--disable-renderer-backgrounding",
      "--disable-backgrounding-occluded-windows",
      "--ignore-gpu-blocklist",
      "--enable-gpu-rasterization",
      "--disable-features=CalculateNativeWinOcclusion",
    ],
    defaultViewport: { width: W, height: H, deviceScaleFactor: SCALE },
  });
}

/** Close a browser without ever hanging the render (a stuck close once held a finished render for minutes). */
async function closeHard(browser) {
  const proc = browser.process();
  await Promise.race([browser.close().catch(() => {}), new Promise((r) => setTimeout(r, 8000))]);
  try {
    if (proc && proc.exitCode === null) proc.kill("SIGKILL");
  } catch {}
}

async function openPage(browser, port) {
  const page = await browser.newPage();
  page.on("console", (m) => {
    if (["error", "warning"].includes(m.type()) && !/favicon/.test(m.text())) console.log("[page]", m.type(), m.text());
  });
  let bootError = null;
  page.on("pageerror", (e) => {
    console.log("[pageerror]", e.message);
    bootError = bootError || e;
  });
  await page.goto(`http://127.0.0.1:${port}/${PAGE}${QUERY ? "?" + QUERY : ""}`, { waitUntil: "load" });
  const t0 = Date.now();
  while (!(await page.evaluate(() => window.__ready === true))) {
    if (bootError) throw new Error("page failed to boot: " + bootError.message);
    if (Date.now() - t0 > 120000) throw new Error("page boot timeout (is a scene's build() stuck?)");
    await new Promise((r) => setTimeout(r, 100));
  }
  return page;
}

// Gamma-correct shutter integration: average in linear light.
const TO_LIN = new Float32Array(256);
for (let i = 0; i < 256; i++) {
  const c = i / 255;
  TO_LIN[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}
const LUTN = 8192;
const TO_SRGB = new Uint8Array(LUTN + 1);
for (let i = 0; i <= LUTN; i++) {
  const l = i / LUTN;
  const c = l <= 0.0031308 ? l * 12.92 : 1.055 * Math.pow(l, 1 / 2.4) - 0.055;
  TO_SRGB[i] = Math.max(0, Math.min(255, Math.round(c * 255)));
}

async function shot(page, t) {
  await page.evaluate((tt) => window.renderAt(tt), t);
  return page.screenshot({ type: "png", optimizeForSpeed: true });
}
const rawOf = (png) => sharp(png).removeAlpha().raw().toBuffer();

/** One output frame: N shutter samples averaged in linear light (N from the composition unless --sub). */
async function renderFrame(page, frame) {
  let n = SUB;
  if (!A.sub) {
    n = await page.evaluate((t) => (window.samplesAt ? window.samplesAt(t) : 1), frame / FPS);
    n = Math.max(1, Math.min(Number(A.maxsub || 24), Math.round(n * Number(A.subscale || 1))));
  }
  if (n <= 1) return rawOf(await shot(page, frame / FPS));
  const acc = new Float32Array(W_PX * H_PX * 3);
  let times = Array.from({ length: n }, (_, j) => Math.max(0, (frame + ((j + 0.5) / n - 0.5) * SHUTTER) / FPS));
  times = await page.evaluate((t0, l) => (window.shutterClamp ? window.shutterClamp(t0, l) : l), frame / FPS, times);
  for (let j = 0; j < n; j++) {
    const raw = await rawOf(await shot(page, times[j]));
    for (let i = 0; i < acc.length; i++) acc[i] += TO_LIN[raw[i]];
  }
  const out = Buffer.allocUnsafe(acc.length);
  const k = LUTN / n;
  for (let i = 0; i < acc.length; i++) out[i] = TO_SRGB[(acc[i] * k + 0.5) | 0];
  return out;
}

function ffmpegChunk(outFile) {
  const args = ["-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", `${W_PX}x${H_PX}`, "-framerate", String(FPS), "-i", "-"];
  if (SCALE !== 1) args.push("-vf", `scale=${W}:${H}:flags=lanczos`);
  args.push("-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", outFile);
  return spawn(FFMPEG, args, { stdio: ["pipe", "inherit", "inherit"] });
}

function write(stream, buf) {
  return new Promise((res) => (stream.write(buf) ? res() : stream.once("drain", res)));
}

async function renderVideo(port) {
  const from = Number(A.from ?? 0), to = Number(A.to ?? CONFIG.duration);
  const f0 = Math.round(from * FPS), f1 = Math.round(to * FPS);
  const total = f1 - f0;
  const out = path.resolve(ROOT, A.out || "renders/out.mkv");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const tmpDir = out + ".chunks";
  fs.mkdirSync(tmpDir, { recursive: true });
  const NW = Math.min(WORKERS, total);
  const per = Math.ceil(total / NW);
  const t0 = Date.now();
  let done = 0;
  const chunks = [];
  await Promise.all(
    Array.from({ length: NW }, async (_, w) => {
      const a = f0 + w * per, b = Math.min(f1, a + per);
      if (a >= b) return;
      const browser = await launch();
      try {
        const page = await openPage(browser, port);
        const file = path.join(tmpDir, `c${String(w).padStart(3, "0")}.mkv`);
        chunks[w] = file;
        const ff = ffmpegChunk(file);
        const exited = new Promise((r) => ff.on("close", r));
        for (let f = a; f < b; f++) {
          const raw = await renderFrame(page, f);
          await write(ff.stdin, raw);
          if (A.frames) {
            const dir = path.resolve(ROOT, A.frames);
            fs.mkdirSync(dir, { recursive: true });
            await sharp(raw, { raw: { width: W_PX, height: H_PX, channels: 3 } }).png().toFile(path.join(dir, `f${String(f).padStart(5, "0")}.png`));
          }
          done++;
          if (done % 30 === 0 || done === total) {
            const el = (Date.now() - t0) / 1000;
            const eta = (el / done) * (total - done);
            process.stdout.write(`\r  ${done}/${total} frames  ${el.toFixed(0)}s  (${(el / done).toFixed(2)}s/frame, ~${eta.toFixed(0)}s left)   `);
          }
        }
        ff.stdin.end();
        await exited;
      } finally {
        await closeHard(browser);
      }
    })
  );
  console.log("");
  const list = path.join(tmpDir, "list.txt");
  fs.writeFileSync(list, chunks.filter(Boolean).map((c) => `file '${c.replace(/\\/g, "/")}'`).join("\n"));
  await new Promise((res, rej) => {
    const p = spawn(FFMPEG, ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", out], { stdio: "inherit" });
    p.on("close", (c) => (c === 0 ? res() : rej(new Error("concat failed"))));
  });
  fs.rmSync(tmpDir, { recursive: true, force: true });
  console.log(`wrote ${out}  (${total} frames) in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

async function renderStills(port) {
  const times = String(A.stills).split(",").map(Number);
  const dir = path.resolve(ROOT, A.dir || "renders/stills");
  fs.mkdirSync(dir, { recursive: true });
  const browser = await launch();
  try {
    const page = await openPage(browser, port);
    const t0 = Date.now();
    for (const t of times) {
      const file = path.join(dir, `t${t.toFixed(3).padStart(7, "0")}.png`);
      if (A.blur) {
        const raw = await renderFrame(page, t * FPS);
        await sharp(raw, { raw: { width: W_PX, height: H_PX, channels: 3 } }).png().toFile(file);
      } else fs.writeFileSync(file, await shot(page, t));
    }
    console.log(`${times.length} stills -> ${dir}  (${((Date.now() - t0) / Math.max(1, times.length)).toFixed(0)}ms each)`);
    if (A.cues) {
      const cues = await page.evaluate(() => window.getCues());
      fs.writeFileSync(path.resolve(ROOT, A.cues), JSON.stringify(cues, null, 1));
      console.log(`cues -> ${A.cues} (${cues.length})`);
    }
  } finally {
    await closeHard(browser);
  }
}

(async () => {
  const server = await start(0);
  const port = server.address().port;
  try {
    if (A.stills) await renderStills(port);
    else await renderVideo(port);
  } catch (e) {
    console.error(e);
    process.exitCode = 1;
  }
  server.close();
  process.exit(process.exitCode || 0);
})();
