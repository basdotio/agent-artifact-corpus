#!/usr/bin/env node
/**
 * Final render: an oversampled master from HyperFrames, real motion blur in
 * ffmpeg, then the deliverables, versioned so nothing is overwritten.
 *
 *   node scripts/render.mjs videos/<film> --name acme-launch [--blur 4] [--poster b9.1]
 *        [--loop] [--webm] [--fps 60] [--draft]
 *
 * 1. Master: `hyperframes render --fps <fps * blur>` (240 by default), with the mix.
 * 2. Motion blur: tmix averages each group of <blur> subframes, select keeps
 *    one per group -> <fps>. BT.709 limited range in and out (HyperFrames tags
 *    its output; we keep the tags so nothing shifts). --blur 1 skips it.
 * 3. Deliverables in out/<name>/vN/:
 *      <name>.mp4         H.264 + AAC 48 kHz, yuv420p, BT.709, +faststart (social, review)
 *      <name>-muted.mp4   the same without audio (landing loops: with --loop)
 *      <name>.webm        VP9 (with --webm)
 *      poster.jpg         from --poster (default: 80% of the film)
 *      loop-seam.png      last 8 + first 8 frames (with --loop)
 * --draft: 30 fps, no blur, --quality draft, for a quick full-length check.
 */
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readdirSync, rmSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { loadCues, seconds } from "./cues-lib.mjs";

const args = process.argv.slice(2);
const film = resolve(args[0] || ".");
const has = (n) => args.includes(n);
const val = (n, d) => (has(n) ? args[args.indexOf(n) + 1] : d);
const cues = loadCues(film);
const name = val("--name", cues.name || "film");
const draft = has("--draft");
const fps = Number(val("--fps", draft ? 30 : 60));
const blur = draft ? 1 : Number(val("--blur", 4));
const ff = process.env.HYPERFRAMES_FFMPEG_PATH || "ffmpeg";
const posterArg = val("--poster", null);
const posterAt = posterArg ? (posterArg.startsWith("b") ? seconds(cues, posterArg.slice(1).split(/[.:]/).map(Number)) : Number(posterArg)) : cues.duration * 0.8;

const root = join(film, "out", name);
mkdirSync(root, { recursive: true });
const versions = readdirSync(root).filter((d) => /^v\d+$/.test(d)).map((d) => Number(d.slice(1)));
const out = join(root, draft ? "draft" : `v${(versions.length ? Math.max(...versions) : 0) + 1}`);
rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
const run = (cmd, list) => execFileSync(cmd, list, { stdio: "inherit", cwd: film });
const master = join(out, "_master.mp4");
const inter = join(out, "_blurred.mov");
const tags = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"];

console.log(`\n[1/3] master at ${fps * blur} fps ...`);
run("npx", ["hyperframes", "render", film, "--fps", String(fps * blur), "--quality", draft ? "draft" : "high", ...(draft ? [] : ["--crf", "10"]), "--output", master, "--strict"]);

const hasAudio = execFileSync("ffprobe", ["-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", master], { encoding: "utf8" }).trim() !== "";
let source = master;
if (blur > 1) {
  console.log(`[2/3] motion blur: ${blur} subframes -> ${fps} fps ...`);
  run(ff, ["-v", "error", "-y", "-i", master, "-vf",
    `tmix=frames=${blur}:weights='${Array(blur).fill(1).join(" ")}',select='not(mod(n+1\\,${blur}))',setpts=N/(${fps}*TB),format=yuv422p10le`,
    "-r", String(fps), "-an", "-c:v", "prores_ks", "-profile:v", "3", ...tags, inter]);
  source = inter;
}

console.log("[3/3] deliverables ...");
const h264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", String(fps),
  "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", ...tags, "-movflags", "+faststart"];
const main = join(out, `${name}.mp4`);
if (hasAudio) run(ff, ["-v", "error", "-y", "-i", source, "-i", master, "-map", "0:v", "-map", "1:a", ...h264, "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-t", String(cues.duration), main]);
else run(ff, ["-v", "error", "-y", "-i", source, ...h264, "-an", "-t", String(cues.duration), main]);
if (has("--loop") || !hasAudio) {
  if (hasAudio) run(ff, ["-v", "error", "-y", "-i", main, "-map", "0:v", "-c", "copy", "-an", join(out, `${name}-muted.mp4`)]);
}
if (has("--webm")) run(ff, ["-v", "error", "-y", "-i", source, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "30", "-row-mt", "1", "-pix_fmt", "yuv420p", "-an", "-t", String(cues.duration), join(out, `${name}.webm`)]);
run(ff, ["-v", "error", "-y", "-ss", posterAt.toFixed(3), "-i", main, "-frames:v", "1", "-q:v", "2", join(out, "poster.jpg")]);
if (has("--loop")) {
  const frames = Math.round(cues.duration * fps);
  const w = 320, h = Math.round((320 * cues.height) / cues.width / 2) * 2;
  run(ff, ["-v", "error", "-y", "-stream_loop", "1", "-i", main, "-vf", `select='between(n\\,${frames - 8}\\,${frames + 7})',scale=${w}:${h},tile=8x2`, "-frames:v", "1", "-fps_mode", "vfr", join(out, "loop-seam.png")]);
}
rmSync(master, { force: true });
rmSync(inter, { force: true });
for (const f of readdirSync(out)) console.log(`  ${join(out, f)}  ${(statSync(join(out, f)).size / 1e6).toFixed(2)} MB`);
console.log(`\nnext: uv run --with numpy python3 <skill>/scripts/verify.py ${out} --duration ${cues.duration} --bg <r,g,b>`);
