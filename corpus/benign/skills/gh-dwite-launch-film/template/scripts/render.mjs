// seek(t) renderer: headless Chrome paints any moment, ffmpeg stitches the frames.
//
//   node scripts/render.mjs stills 1.5,8.2,12.3 [--scale 1] [--fmt 16x9] [--dir review/stills]
//   node scripts/render.mjs video --fps 30 --scale 0.5 --out out/animatic.mp4         (length from timeline.json)
//   node scripts/render.mjs video --fps 60 --sub 4 --shutter 0.5 --workers 12 --out out/master.mp4
//
// Each video worker is its own process (Node + Chrome + ffmpeg) rendering a contiguous frame range.
// Motion blur: each output frame averages `sub` samples spread over `shutter` of the frame interval.
import { chromium } from "playwright-core";
import { createServer } from "node:http";
import { readFile, mkdir, writeFile, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { cpus } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(HERE), "..");
const args = process.argv.slice(2);
const mode = args[0];
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i >= 0 ? args[i + 1] : def;
};
const FMT = opt("fmt", "16x9");
const [W, H] = { "16x9": [1920, 1080], "9x16": [1080, 1920], "1x1": [1080, 1080] }[FMT];
const SCALE = Number(opt("scale", "1"));
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const MIME = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".json": "application/json", ".otf": "font/otf", ".ttf": "font/ttf", ".woff2": "font/woff2", ".svg": "image/svg+xml" };

async function startServer() {
  const server = createServer(async (req, res) => {
    try {
      const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
      const body = await readFile(p);
      res.writeHead(200, { "content-type": MIME[path.extname(p)] || "application/octet-stream", "cache-control": "max-age=3600" });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end();
    }
  });
  await new Promise((r) => server.listen(0, r));
  return server;
}

async function openBrowser(port) {
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ["--force-color-profile=srgb", "--font-render-hinting=none", "--hide-scrollbars", "--disable-lcd-text", "--enable-gpu-rasterization", "--ignore-gpu-blocklist"],
  });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: SCALE });
  page.on("console", (m) => {
    const tx = m.text();
    if ((m.type() === "error" && !tx.includes("Failed to load resource")) || tx.startsWith("[stage]")) console.log("page:", tx);
  });
  page.on("pageerror", (e) => console.log("pageerror:", e.message));
  await page.goto(`http://127.0.0.1:${port}/src/index.html?fmt=${FMT}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 180000 });
  return { browser, page };
}

async function shot(page, t, type) {
  await page.evaluate((tt) => window.__seek(tt), t);
  return page.screenshot({ type, ...(type === "jpeg" ? { quality: 94 } : {}) });
}

if (mode === "stills") {
  const server = await startServer();
  const { browser, page } = await openBrowser(server.address().port);
  const times = args[1].split(",").map(Number);
  const dir = path.join(ROOT, opt("dir", "review/stills"));
  await mkdir(dir, { recursive: true });
  for (const t of times) {
    const buf = await shot(page, t, "png");
    const name = `${FMT}_t${t.toFixed(2).padStart(6, "0")}.png`;
    await writeFile(path.join(dir, name), buf);
    console.log("still", name);
  }
  await browser.close();
  server.close();
} else if (mode === "worker") {
  // worker <seg path> <first frame> <end frame>
  const [seg, a, b] = [args[1], Number(args[2]), Number(args[3])];
  const from = Number(opt("from", "0"));
  const fps = Number(opt("fps", "30"));
  const sub = Number(opt("sub", "1"));
  const shutter = Number(opt("shutter", "0.5"));
  const crf = opt("crf", "12");
  const server = await startServer();
  const { browser, page } = await openBrowser(server.address().port);
  const vf = sub > 1 ? [`tmix=frames=${sub}`, `select='not(mod(n+1\\,${sub}))'`, `setpts=N/(${fps}*TB)`].join(",") : "null";
  const ff = spawn("ffmpeg", ["-y", "-v", "error", "-f", "image2pipe", "-framerate", String(fps * sub), "-i", "-", "-vf", vf, "-r", String(fps), "-c:v", "libx264", "-preset", "fast", "-crf", crf, "-pix_fmt", "yuv420p", seg], { stdio: ["pipe", "inherit", "inherit"] });
  const ffDone = new Promise((r) => ff.on("close", r));
  for (let i = a; i < b; i++) {
    const T = from + i / fps;
    for (let k = 0; k < sub; k++) {
      const t = sub > 1 ? T + ((k + 0.5) / sub - 0.5) * (shutter / fps) : T;
      const buf = await shot(page, Math.max(0, t), "jpeg");
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    }
    if ((i - a) % 30 === 29) process.stdout.write(`tick ${i - a + 1}\n`);
  }
  ff.stdin.end();
  await ffDone;
  await browser.close();
  server.close();
} else if (mode === "video") {
  const from = Number(opt("from", "0"));
  const tl = JSON.parse(await readFile(path.join(ROOT, "timeline.json"), "utf8"));
  const to = Number(opt("to", String(typeof tl.T?.dur === "number" ? tl.T.dur : tl.dur)));
  const fps = Number(opt("fps", "30"));
  const sub = opt("sub", "1");
  const workers = Number(opt("workers", String(Math.max(2, cpus().length - 4))));
  const out = path.join(ROOT, opt("out", "out/animatic.mp4"));
  const n = Math.round((to - from) * fps);
  const tmp = path.join(ROOT, "out", `.seg_${Date.now()}`);
  await mkdir(tmp, { recursive: true });
  const per = Math.ceil(n / workers);
  const started = Date.now();
  let done = 0;
  const jobs = [];
  for (let w = 0; w < workers; w++) {
    const a = w * per;
    const b = Math.min(n, a + per);
    if (a >= b) break;
    const seg = path.join(tmp, `seg_${String(w).padStart(2, "0")}.mp4`);
    const child = spawn(process.execPath, [HERE, "worker", seg, String(a), String(b), "--from", String(from), "--fps", String(fps), "--sub", sub, "--shutter", opt("shutter", "0.5"), "--scale", String(SCALE), "--fmt", FMT, "--crf", opt("crf", "12")], { stdio: ["ignore", "pipe", "inherit"] });
    child.stdout.on("data", (d) => {
      for (const line of String(d).split("\n")) {
        if (line.startsWith("tick")) {
          done += 30;
          if (done % 150 === 0) {
            const el = (Date.now() - started) / 1000;
            console.log(`frames ${done}/${n}  ${(done / el).toFixed(1)} fps  eta ${(((n - done) / done) * el).toFixed(0)}s`);
          }
        } else if (line.trim()) console.log(`[w${w}] ${line}`);
      }
    });
    jobs.push(new Promise((r) => child.on("close", () => r(seg))));
  }
  const segs = await Promise.all(jobs);
  const list = path.join(tmp, "list.txt");
  await writeFile(list, segs.map((s) => `file '${s}'`).join("\n"));
  await new Promise((r) => spawn("ffmpeg", ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", out], { stdio: "inherit" }).on("close", r));
  await rm(tmp, { recursive: true, force: true });
  console.log(`wrote ${out} (${n} frames in ${((Date.now() - started) / 1000).toFixed(0)}s)`);
}
