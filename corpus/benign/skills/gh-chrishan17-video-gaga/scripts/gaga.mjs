#!/usr/bin/env node
// gaga, the video-gaga CLI — HTML Canvas composition → MP4 (+ Edge TTS narration, subtitles).
//
//   node scripts/gaga.mjs render <project|video.html> [options]
//   node scripts/gaga.mjs still  <project> [--at 1,2.5] [--sheet] [--phone]
//   node scripts/gaga.mjs moodboard <preview> <preview> … [--wait]
//   node scripts/gaga.mjs tts    <project>
//   node scripts/gaga.mjs music  <project>
//   node scripts/gaga.mjs check  <video.mp4> [--srt file.srt]
//   node scripts/gaga.mjs gif    <video.mp4> [--out x.gif] [--width 480] [--fps 12]
//   node scripts/gaga.mjs init   <dir> [--preset <slug>]
//   node scripts/gaga.mjs voices [--lang zh-CN]
//   node scripts/gaga.mjs asset  <project> polyhaven:<id> [--res 1k]
//   node scripts/gaga.mjs asset  find <words…> [--type textures]
//   node scripts/gaga.mjs texture <image> [--seamless] [--delight]
//   node scripts/gaga.mjs texture <project> --prompt "<surface>" --name <name> [--matcap]
//
// Run `node scripts/gaga.mjs help` for all options.

import { spawn, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { assetCmd, textureCmd, readManifest, writeManifest, restoreAssets } from './assets.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// ---------------------------------------------------------------------------
// tiny arg parser
// ---------------------------------------------------------------------------
function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const [k, v] = a.slice(2).split('=');
      const key = k.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      if (v !== undefined) out[key] = v;
      else if (argv[i + 1] && !argv[i + 1].startsWith('--')) out[key] = argv[++i];
      else out[key] = true;
    } else out._.push(a);
  }
  return out;
}

const log = (...a) => console.log(...a);
const die = (msg) => { console.error(`\n✖ ${msg}`); process.exit(1); };
const has = (bin) => spawnSync(bin, [bin.startsWith('ff') ? '-version' : '--version'], { stdio: 'ignore' }).status === 0;

function resolveProject(p) {
  if (!p) die('missing <project> argument');
  const abs = path.resolve(p);
  if (!fs.existsSync(abs)) die(`not found: ${abs}`);
  if (fs.statSync(abs).isDirectory()) {
    const html = path.join(abs, 'video.html');
    if (!fs.existsSync(html)) die(`no video.html in ${abs}`);
    return { dir: abs, html };
  }
  return { dir: path.dirname(abs), html: abs };
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args, { stdio: opts.stdio || ['ignore', 'inherit', 'inherit'], ...opts });
    p.on('error', reject);
    p.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(`${cmd} exited with ${code}`))));
  });
}

function ffprobe(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', file], { encoding: 'utf8' });
  if (r.status !== 0) die(`ffprobe failed on ${file}: ${r.stderr}`);
  return JSON.parse(r.stdout);
}

// ---------------------------------------------------------------------------
// TTS
// ---------------------------------------------------------------------------
async function tts(dir) {
  const spec = path.join(dir, 'narration.json');
  if (!fs.existsSync(spec)) return false;
  // One take: the voice is a recorded or separately synthesized track, cut by `gaga voicetrack`
  if (JSON.parse(fs.readFileSync(spec, 'utf8')).track) {
    if (!fs.existsSync(path.join(dir, 'build', 'narration.js'))) die('narration.json has a "track": cut the take first with `gaga voicetrack <project> --audio <take>`');
    log('▸ narration: one take (build/narration.js from `gaga voicetrack`), Edge TTS skipped');
    return true;
  }
  const script = path.join(ROOT, 'scripts', 'tts.py');
  log('▸ narration (Edge TTS)');
  if (has('uv')) await run('uv', ['run', '--quiet', '--no-project', '--with', 'edge-tts>=7.2', 'python', script, dir]);
  else if (has('python3')) await run('python3', [script, dir]);
  else die('need `uv` or `python3` with edge-tts installed (pip install edge-tts)');
  return true;
}

// One take: align a whole recorded or synthesized narration to narration.json,
// lengthen its pauses and cut it into one slice per scene (scripts/voicetrack.py).
async function voicetrack(o) {
  const { dir } = resolveProject(o._[1]);
  if (!fs.existsSync(path.join(dir, 'narration.json'))) die('voicetrack needs narration.json (one segment per scene)');
  const script = path.join(ROOT, 'scripts', 'voicetrack.py');
  const args = [script, dir];
  if (o.audio) args.push('--audio', path.resolve(String(o.audio)));
  for (const c of String(o.cut || '').split(',').filter(Boolean)) args.push('--cut', c);
  if (o.clean) args.push('--clean');
  if (o.model) args.push('--model', String(o.model));
  log('▸ narration: one take');
  const asr = process.platform === 'darwin' && process.arch === 'arm64' ? 'mlx-whisper' : 'faster-whisper';
  if (!has('uv')) die('voicetrack needs `uv` (it runs Whisper in a throwaway environment)');
  await run('uv', ['run', '--quiet', '--no-project', '--with', asr, '--with', 'numpy', '--with', 'soundfile', '--with', 'pypinyin', '--with', 'jieba', 'python', '-W', 'ignore::SyntaxWarning', ...args]);
}

// ---------------------------------------------------------------------------
// Music: the score is arranged from the resolved timeline (scripts/music.mjs)
// ---------------------------------------------------------------------------
async function synthMusic(dir, score, { quiet } = {}) {
  const { renderScore, writeWav } = await import('./music.mjs');
  const { soundfontPath } = await import('./soundfont.mjs');
  const voiceDb = score.voice.length ? speechLevel(dir) : null;
  const sf = soundfontPath();
  // a written score (music.script) is a module next to video.html
  if (score.script) score = { ...score, script: path.resolve(dir, score.script) };
  if (score.script && !fs.existsSync(score.script)) throw new Error(`music.script not found: ${score.script}`);
  const key = crypto.createHash('sha1').update(fs.readFileSync(path.join(ROOT, 'scripts', 'music.mjs'))).update(fs.readFileSync(path.join(ROOT, 'scripts', 'soundfont.mjs')))
    .update(fs.readFileSync(path.join(ROOT, 'scripts', 'samples.mjs'))).update(JSON.stringify(score)).update(score.script ? fs.readFileSync(score.script) : '').update(String(voiceDb)).update(fs.existsSync(sf) ? `${sf}:${fs.statSync(sf).size}` : 'synth').digest('hex').slice(0, 16);
  const file = path.join(dir, 'build', 'music.wav'), bed = path.join(dir, 'build', 'music-bed.wav');
  const meta = path.join(dir, 'build', 'music.json');
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if ([file, bed, meta].every((f) => fs.existsSync(f)) && JSON.parse(fs.readFileSync(meta, 'utf8')).key === key) {
    if (!quiet) log('▸ music (cached)');
    return { file, bed, report: JSON.parse(fs.readFileSync(meta, 'utf8')).report };
  }
  const t0 = Date.now();
  const mix = await renderScore(score, { voiceDb: voiceDb ?? undefined, log: quiet ? () => {} : log });
  writeWav(file, mix);
  writeWav(bed, { left: mix.bed.left, right: mix.bed.right, sampleRate: mix.sampleRate });
  mix.report.voiceDb = voiceDb;
  // a score that fell back to cheaper instruments is not cached: the next render tries again
  const degraded = mix.report.engine !== 'samples' || (mix.report.warnings || []).some((w) => /could not be loaded/.test(w));
  fs.writeFileSync(meta, JSON.stringify({ key: degraded ? null : key, report: mix.report }, null, 1));
  if (!quiet) log(`▸ music: ${mix.report.key} · ${mix.report.bpm} BPM · ${mix.report.layers} layers · ${mix.report.placedSfx?.length ?? score.sfx.length} sfx · ${mix.report.engine === 'samples' ? 'sampled instruments' : 'built-in synth'} (${Date.now() - t0} ms)`);
  if (!quiet) for (const w of mix.report.warnings || []) log(`  ⚠ music: ${w}`);
  return { file, bed, report: mix.report };
}

// RMS (dBFS) of the narration while it speaks (frames above a −45 dB gate),
// so the score can sit at a fixed distance under *this* voice.
function speechLevel(dir) {
  const vdir = path.join(dir, 'build', 'voice');
  if (!fs.existsSync(vdir)) return null;
  let sum = 0, count = 0;
  for (const f of fs.readdirSync(vdir).filter((x) => x.endsWith('.mp3')).sort()) {
    const r = spawnSync('ffmpeg', ['-v', 'error', '-i', path.join(vdir, f), '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], { maxBuffer: 1 << 28 });
    if (r.status !== 0) continue;
    const x = new Float32Array(r.stdout.buffer, r.stdout.byteOffset, Math.floor(r.stdout.byteLength / 4));
    for (let i = 0; i + 320 <= x.length; i += 320) { // 20 ms frames
      let e = 0;
      for (let j = i; j < i + 320; j++) e += x[j] * x[j];
      if (e / 320 > 3.2e-5) { sum += e; count += 320; }
    }
  }
  return count ? +(10 * Math.log10(sum / count)).toFixed(1) : null;
}

// ---------------------------------------------------------------------------
// Browser
// ---------------------------------------------------------------------------
async function launch() {
  let chromium;
  try {
    ({ chromium } = await import('playwright'));
  } catch {
    die('playwright is not installed. Run `npm install` in the video-gaga folder (then `npx playwright install chromium` if needed).');
  }
  const args = ['--allow-file-access-from-files', '--force-color-profile=srgb', '--hide-scrollbars', '--mute-audio', '--disable-renderer-backgrounding', '--disable-background-timer-throttling', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader'];
  try {
    return await chromium.launch({ args });
  } catch (e) {
    try {
      return await chromium.launch({ args, channel: 'chrome' });
    } catch {
      die(`could not launch Chromium: ${e.message.split('\n')[0]}\nRun: npx playwright install chromium`);
    }
  }
}

// A project keeps the runtime `gaga init` copied. After the skill is updated that
// copy is stale, and newer options (music.parts, scene.part …) are silently ignored.
const staleWarned = new Set();
function checkRuntime(html) {
  const local = path.join(path.dirname(html), 'video-gaga.js');
  if (staleWarned.has(local) || !fs.existsSync(local) || !/src="video-gaga\.js"/.test(fs.readFileSync(html, 'utf8'))) return;
  staleWarned.add(local);
  if (!fs.readFileSync(local).equals(fs.readFileSync(path.join(ROOT, 'runtime', 'video-gaga.js')))) log(`  ⚠ ${path.relative(process.cwd(), local)} differs from the skill's runtime (copied by an older \`gaga init\`?): newer options may be ignored. Update it: cp ${path.relative(process.cwd(), path.join(ROOT, 'runtime', 'video-gaga.js'))} ${path.relative(process.cwd(), local)}`);
}

// assets/ is rebuilt from assets/assets.json where it lacks something (a fresh
// clone keeps only the manifest and the original pictures in git)
async function ensureAssets(dir) {
  if (!Object.keys(readManifest(path.join(dir, 'assets'))).length) return;
  const { restored, failed } = await restoreAssets(dir, { log: () => {} });
  if (restored.length) log(`  assets restored from assets.json: ${restored.join(', ')}`);
  for (const f of failed) log(`  ⚠ could not restore ${f.key}: ${f.error}`);
}

async function openComposition(browser, html, q) {
  checkRuntime(html);
  await ensureAssets(path.dirname(html));
  const page = await browser.newPage({ viewport: { width: 800, height: 600 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  const url = `${pathToFileURL(html).href}?${new URLSearchParams(q)}`;
  await page.goto(url, { waitUntil: 'load', timeout: 120000 });
  const ok = await page.waitForFunction(() => !!window.__CV, null, { timeout: 30000 }).then(() => true, () => false);
  if (!ok) die(`composition did not call CV.create() — page errors:\n  ${errors.join('\n  ') || '(none)'}`);
  await page.evaluate(() => window.__CV.ready());
  const info = await page.evaluate(() => window.__CV.info());
  // a map, environment or model that failed would render a flat or empty shot
  if (info.missingAssets?.length) die(`assets failed to load (paths are relative to video.html):\n  ${info.missingAssets.join('\n  ')}${errors.length ? `\n${errors.join('\n  ')}` : ''}`);
  return { page, info, errors };
}

// ---------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------
async function render(opts) {
  const t0 = Date.now();
  const { dir, html } = resolveProject(opts._[1]);
  if (!has('ffmpeg')) die('ffmpeg not found (macOS: brew install ffmpeg)');
  const name = path.basename(dir);
  const out = path.resolve(opts.out || path.join(dir, 'out', `${name}.mp4`));
  fs.mkdirSync(path.dirname(out), { recursive: true });

  if (!opts.noTts) await tts(dir);

  const subsMode = String(opts.subs ?? 'file'); // file | burn | soft | burn+soft | none
  const burn = subsMode.includes('burn');
  const scale = Number(opts.scale || 1);
  const mb = Math.max(1, Number(opts.motionBlur || 1) | 0);
  const shutter = Number(opts.shutter ?? 0.5); // fraction of a frame the shutter is open
  const fmt = opts.format === 'jpeg' ? 'jpeg' : 'png';
  const quality = Number(opts.quality ?? 0.95);

  log('▸ loading composition');
  const browser = await launch();
  const q = { render: '1', scale: String(scale), subs: burn ? '1' : '0' };
  const probe = await openComposition(browser, html, q);
  const info = probe.info;
  if (probe.errors.length) log(`  ⚠ page errors:\n    ${probe.errors.join('\n    ')}`);
  if (info.missingFonts?.length) log(`  ⚠ fonts not loaded (fallback used): ${info.missingFonts.join(', ')}`);
  const est = info.scenes.filter((s) => s.estimated);
  if (est.length) log(`  ⚠ ${est.length} scene(s) use estimated speech timing (no TTS audio): ${est.map((s) => s.id).join(', ')}`);
  await probe.page.close();

  const { fps } = info;
  const from = Math.max(0, Math.round(Number(opts.from || 0) * fps));
  const to = Math.min(info.totalFrames, opts.to ? Math.round(Number(opts.to) * fps) : info.totalFrames);
  const frames = to - from;
  if (frames <= 0) die('nothing to render (check --from/--to)');
  const pw = info.pixelWidth, ph = info.pixelHeight;
  if (pw % 2 || ph % 2) die(`output size must be even for H.264 (got ${pw}x${ph})`);
  log(`  ${info.width}x${info.height} @${fps}fps${scale !== 1 ? ` (x${scale} → ${pw}x${ph})` : ''}, ${(frames / fps).toFixed(2)}s, ${frames} frames, ${info.scenes.length} scenes`);

  const cpu = os.cpus().length;
  const workers = Math.max(1, Math.min(Number(opts.workers || Math.min(6, Math.max(1, Math.floor(cpu / 2)))), Math.ceil(frames / 15)));
  fs.mkdirSync(path.join(dir, 'build'), { recursive: true });
  const tmp = fs.mkdtempSync(path.join(dir, 'build', '.render-'));
  const crf = String(opts.crf ?? 18);
  const x264preset = String(opts.x264Preset || 'medium');

  log(`▸ rendering with ${workers} worker(s)${mb > 1 ? `, motion blur ${mb} subframes` : ''} [${fmt}]`);
  const chunk = Math.ceil(frames / workers);
  let done = 0;
  const tFrames = Date.now();
  const tick = () => {
    done++;
    const every = process.stdout.isTTY ? 10 : Math.max(1, Math.round(frames / 4));
    if (done % every === 0 || done === frames) {
      const pct = ((done / frames) * 100).toFixed(0);
      const el = (Date.now() - t0) / 1000;
      // long renders: say how long is left (from the frame rate so far)
      const eta = done < frames && done > workers * 5 ? `, ~${Math.ceil(((frames - done) * (Date.now() - tFrames)) / (done * 1000))}s left` : '';
      process.stdout.write(`\r  ${done}/${frames} frames (${pct}%)  ${el.toFixed(1)}s${eta}   `);
    }
  };

  const segFiles = [];
  const jobs = [];
  for (let w = 0; w < workers; w++) {
    const a = from + w * chunk, b = Math.min(to, a + chunk);
    if (a >= b) continue;
    const seg = path.join(tmp, `seg-${String(w).padStart(3, '0')}.mp4`);
    segFiles.push(seg);
    jobs.push(renderChunk({ browser, html, q, a, b, fps, mb, shutter, fmt, quality, seg, crf, x264preset, tick }));
  }
  // errors a scene or transition logs while frames render (the probe page only saw boot)
  const renderErrors = [...new Set((await Promise.all(jobs)).flat())].filter((e) => !probe.errors.includes(e));
  process.stdout.write('\n');
  await browser.close();
  if (renderErrors.length) log(`  ⚠ page errors while rendering:\n    ${renderErrors.slice(0, 10).join('\n    ')}${renderErrors.length > 10 ? `\n    … ${renderErrors.length - 10} more` : ''}`);

  // concat video segments
  const list = path.join(tmp, 'list.txt');
  fs.writeFileSync(list, segFiles.map((f) => `file '${f.replace(/'/g, "'\\''")}'`).join('\n'));
  const videoOnly = path.join(tmp, 'video.mp4');
  await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', videoOnly]);

  // subtitles
  const base = out.replace(/\.mp4$/i, '');
  const cues = info.cues.map((c) => ({ ...c, start: c.start - from / fps, end: c.end - from / fps })).filter((c) => c.end > 0 && c.start < frames / fps);
  if (cues.length && subsMode !== 'none') {
    fs.writeFileSync(`${base}.srt`, toSRT(cues));
    fs.writeFileSync(`${base}.vtt`, toVTT(cues));
  }

  // audio mix + mux
  log('▸ muxing');
  const dur = frames / fps;
  const voice = info.voice.map((v) => ({ ...v, start: v.start - from / fps })).filter((v) => v.start + v.duration > 0 && v.start < dur);
  // music: --music <file> (licensed track, side-chain ducked) > music.file in
  // the composition > the generated score (already arranged around the voice)
  let music = null, generated = false;
  if (!opts.noMusic) {
    if (opts.music && opts.music !== true) music = path.resolve(opts.music);
    else if (info.music) music = path.resolve(dir, info.music);
    else if (info.score) { const sm = await synthMusic(dir, info.score); music = sm.file; generated = sm; }
  }
  const args = ['-y', '-loglevel', 'error', '-i', videoOnly];
  let filter = [];
  let idx = 1;
  const voiceLabels = [];
  for (const v of voice) {
    const f = path.resolve(dir, v.file);
    if (!fs.existsSync(f)) { log(`  ⚠ missing voice file ${f}`); continue; }
    const skip = Math.max(0, -v.start);
    args.push('-i', f);
    const delay = Math.round(Math.max(0, v.start) * 1000);
    filter.push(`[${idx}:a]atrim=start=${skip.toFixed(3)},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,adelay=${delay}:all=1[v${idx}]`);
    voiceLabels.push(`[v${idx}]`);
    idx++;
  }
  let aout = null;
  if (voiceLabels.length) {
    filter.push(`${voiceLabels.join('')}amix=inputs=${voiceLabels.length}:normalize=0:dropout_transition=0,apad[voice]`);
    aout = '[voice]';
  }
  // remembered to render a voice-only stem for the sync and balance checks
  // (args.slice(3) keeps the video as input 0 so the stream labels still match)
  const voiceStemSpec = voiceLabels.length ? { inputs: args.slice(3), filter: filter.slice() } : null;
  if (music && fs.existsSync(music)) {
    if (generated) {
      // the score already fades, ducks under the voice and ends on the last frame
      args.push('-ss', (from / fps).toFixed(3), '-i', music);
      filter.push(`[${idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume=${Number(opts.musicVolume ?? 1)}[mus]`);
    } else {
      args.push('-stream_loop', '-1', '-i', music);
      const mv = Number(opts.musicVolume ?? 0.22);
      filter.push(`[${idx}:a]aresample=48000,aformat=channel_layouts=stereo,volume=${mv},afade=t=in:d=0.8,afade=t=out:st=${Math.max(0, dur - 1.5).toFixed(2)}:d=1.5[mus]`);
    }
    idx++;
    if (aout && generated) {
      filter.push(`[voice][mus]amix=inputs=2:normalize=0,apad[mixed]`);
      aout = '[mixed]';
    } else if (aout) {
      filter.push(`[voice]asplit=2[vk][vm]`);
      filter.push(`[mus][vk]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[duck]`);
      filter.push(`[vm][duck]amix=inputs=2:normalize=0,apad[mixed]`);
      aout = '[mixed]';
    } else {
      filter.push(`[mus]apad[mixed]`);
      aout = '[mixed]';
    }
  }
  const soft = subsMode.includes('soft') && cues.length;
  if (soft) args.push('-i', `${base}.srt`);
  if (aout) {
    filter.push(`${aout}loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]`);
    args.push('-filter_complex', filter.join(';'), '-map', '0:v', '-map', '[aout]', '-c:a', 'aac', '-b:a', '192k');
  } else args.push('-map', '0:v');
  if (soft) args.push('-map', `${idx}:s`, '-c:s', 'mov_text', '-metadata:s:s:0', `language=${/^zh/.test(info.lang) ? 'chi' : /^ja/.test(info.lang) ? 'jpn' : 'eng'}`);
  args.push('-c:v', 'copy', '-t', dur.toFixed(3), '-movflags', '+faststart', out);
  await run('ffmpeg', args);

  // stems for the checks: speech onsets can't be found under music, and the
  // music/voice balance needs both signals separately
  let stems = null;
  if (voiceStemSpec) {
    const vf = path.join(tmp, 'voice.f32');
    await run('ffmpeg', ['-y', '-loglevel', 'error', ...voiceStemSpec.inputs, '-filter_complex', voiceStemSpec.filter.join(';'), '-map', '[voice]', '-t', dur.toFixed(3), '-ac', '1', '-ar', '48000', '-f', 'f32le', vf]);
    // spans = the spoken part of each line (not the clip's trailing silence), as the score ducks
    stems = { voice: fs.readFileSync(vf), spans: voice.map((v) => [v.start, v.start + (v.speech ?? v.duration)]) };
    if (music && fs.existsSync(music)) {
      const mf = path.join(tmp, 'music.f32');
      const mvol = generated ? Number(opts.musicVolume ?? 1) : Number(opts.musicVolume ?? 0.22);
      // generated: measure the bed without sound effects (word-synced ticks aren't "music")
      await run('ffmpeg', ['-y', '-loglevel', 'error', ...(generated ? ['-ss', (from / fps).toFixed(3)] : ['-stream_loop', '-1']), '-i', generated ? generated.bed : music, '-af', `volume=${mvol}`, '-t', dur.toFixed(3), '-ac', '1', '-ar', '48000', '-f', 'f32le', mf]);
      stems.music = fs.readFileSync(mf);
      stems.ducked = !generated; // a plain track is side-chain ducked in the real mix
    }
    // keep the voice stem next to the build so a later `gaga check <mp4>` can measure sync too
    const wav = path.join(dir, 'build', 'voice-stem.wav');
    await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'f32le', '-ar', '48000', '-ac', '1', '-i', vf, wav]);
    stems.voiceWav = wav;
    fs.writeFileSync(path.join(dir, 'build', 'voice-stem.json'), JSON.stringify({ video: path.basename(out), from: from / fps, music: !!music }));
  }

  const secs = ((Date.now() - t0) / 1000).toFixed(1);
  log(`✔ ${path.relative(process.cwd(), out)}  (${secs}s)`);
  if (cues.length && subsMode !== 'none') log(`  subtitles: ${path.relative(process.cwd(), base)}.srt / .vtt (${cues.length} cues${burn ? ', burned in' : ''}${soft ? ', soft track' : ''})`);
  // the words on screen at a few moments (captions left out: they go with the voice)
  const textAt = async (times) => {
    const b = await launch();
    try {
      const { page } = await openComposition(b, html, { render: '1', scale: '0.25', subs: '0' });
      const out = [];
      for (const t of times) {
        const boxes = await page.evaluate((f) => (window.__CV.textBoxes ? window.__CV.textBoxes(f) : null), Math.min(info.totalFrames - 1, Math.round(t * fps) + from));
        out.push((boxes || []).filter((x) => x.y1 - x.y0 >= 9 && x.x0 >= 0 && x.y0 >= 0 && x.x1 <= info.width && x.y1 <= info.height).map((x) => x.text));
      }
      return out;
    } finally { await b.close(); }
  };
  await report(out, cues.length ? `${base}.srt` : null, stems, voice.map((v) => ({ ...v, file: path.resolve(dir, v.file) })), info.scenes.map((s) => ({ ...s, start: s.start - from / fps })), textAt);
  if (!opts.keepTemp) fs.rmSync(tmp, { recursive: true, force: true });
}

async function renderChunk({ browser, html, q, a, b, fps, mb, shutter, fmt, quality, seg, crf, x264preset, tick }) {
  const { page, errors } = await openComposition(browser, html, q);
  const rate = fps * mb;
  const vf = [];
  if (mb > 1) vf.push(`tmix=frames=${mb}`, `select='eq(mod(n\\,${mb})\\,${mb - 1})'`, `setpts=N/(${fps}*TB)`);
  vf.push('scale=out_color_matrix=bt709:out_range=tv', 'format=yuv420p');
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(rate), '-c:v', fmt === 'png' ? 'png' : 'mjpeg', '-i', '-',
    '-vf', vf.join(','),
    '-c:v', 'libx264', '-preset', x264preset, '-crf', crf, '-r', String(fps),
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
    seg,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });
  const exited = new Promise((res, rej) => ff.on('exit', (c) => (c === 0 ? res() : rej(new Error(`ffmpeg exited ${c}`)))));
  const type = fmt === 'png' ? 'image/png' : 'image/jpeg';
  for (let f = a; f < b; f++) {
    for (let k = 0; k < mb; k++) {
      // subframe offsets centred on the frame time, spanning `shutter` of a frame
      const sub = mb > 1 ? (k / (mb - 1) - 0.5) * shutter : 0;
      const dataUrl = await page.evaluate(async ([f, sub, type, qv]) => { await window.__CV.renderFrame(f, sub); return window.__CV.capture(type, qv); }, [f, sub, type, quality]);
      const buf = Buffer.from(dataUrl.slice(dataUrl.indexOf(',') + 1), 'base64');
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    }
    tick();
  }
  ff.stdin.end();
  await exited;
  await page.close();
  return errors;
}

// ---------------------------------------------------------------------------
// subtitles
// ---------------------------------------------------------------------------
function ts(t, sep) {
  const ms = Math.max(0, Math.round(t * 1000));
  const h = Math.floor(ms / 3600000), m = Math.floor((ms % 3600000) / 60000), s = Math.floor((ms % 60000) / 1000);
  const pad = (n, w = 2) => String(n).padStart(w, '0');
  return `${pad(h)}:${pad(m)}:${pad(s)}${sep}${pad(ms % 1000, 3)}`;
}
const toSRT = (cues) => cues.map((c, i) => `${i + 1}\n${ts(c.start, ',')} --> ${ts(c.end, ',')}\n${c.text}\n`).join('\n');
const toVTT = (cues) => `WEBVTT\n\n${cues.map((c) => `${ts(c.start, '.')} --> ${ts(c.end, '.')}\n${c.text}\n`).join('\n')}`;

// ---------------------------------------------------------------------------
// check / report
// ---------------------------------------------------------------------------
// Speech onsets (s) in an audio/video file: the ends of silences.
function speechOnsets(file, minSilence) {
  const sd = spawnSync('ffmpeg', ['-hide_banner', '-i', file, '-map', '0:a', '-af', `silencedetect=noise=-38dB:d=${minSilence}`, '-f', 'null', '-'], { encoding: 'utf8' });
  const onsets = [0, ...[...sd.stderr.matchAll(/silence_end: ([\d.]+)/g)].map((m) => Number(m[1]))];
  const firstSilence = sd.stderr.match(/silence_start: ([\d.]+)/);
  if (!firstSilence || Number(firstSilence[1]) > 0.05) return onsets; // audio did not start silent
  return onsets.slice(1);
}

// stems: { voiceWav, music, voice, spans, noSync } from the renderer (speech
// onsets can't be found under music, so they're measured on the voice stem).
// voice: [{id, file, start}] from the renderer. Lets sync be checked for every
// clip, including lines that have no caption cue.
// Picture checks on the encoded video, for what no single probe shows: a hold
// where nothing moves, a one-frame glitch, flashing, blank frames. One decoding
// pass over a small grey copy (long side 192 px), no re-render.
const PIX_DIFF = 6; // grey levels at 192 px that count as "this pixel changed"
const STILL = 0.0005; // fraction of pixels changed below which two frames are the same
async function scanPicture(file, v) {
  const [n, d] = (v.r_frame_rate || v.avg_frame_rate || '30/1').split('/').map(Number);
  const fps = n / d;
  const k = 192 / Math.max(v.width, v.height);
  const w = Math.max(2, Math.round((v.width * k) / 2) * 2), h = Math.max(2, Math.round((v.height * k) / 2) * 2), N = w * h;
  // linear-light luminance per grey level, for the flash rule (WCAG: a 10% swing)
  const lin = Float64Array.from({ length: 256 }, (_, i) => { const c = i / 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; });
  const moved = [0], skip = [0, 0], blank = [], luma = []; // luma[i] = [whole, 4 quadrants]
  const frames = [Buffer.alloc(N), Buffer.alloc(N), Buffer.alloc(N)];
  let i = 0, fill = 0;
  const changed = (a, b) => { let c = 0; for (let p = 0; p < N; p++) if (Math.abs(a[p] - b[p]) > PIX_DIFF) c++; return c / N; };
  const frame = (f) => {
    if (i > 0) moved.push(changed(f, frames[(i - 1) % 3]));
    if (i > 1) skip.push(changed(f, frames[(i - 2) % 3]));
    const hist = new Uint32Array(256), q = [0, 0, 0, 0, 0];
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const g = f[y * w + x], l = lin[g];
      hist[g]++; q[0] += l; q[1 + (y >= h / 2) * 2 + (x >= w / 2)] += l;
    }
    luma.push([q[0] / N, ...q.slice(1).map((s) => (s * 4) / N)]);
    let med = 0;
    for (let acc = 0; med < 255 && (acc += hist[med]) < N / 2; med++);
    // blank: almost no pixel stands out from the background (a thin rule or a
    // small dot still leaves a few at this size, so count pixels, not area)
    let off = 0;
    for (let g = 0; g < 256; g++) if (Math.abs(g - med) > 16) off += hist[g];
    blank.push(off < 8);
    i++;
  };
  await new Promise((resolve, reject) => {
    const ff = spawn('ffmpeg', ['-v', 'error', '-i', file, '-vf', `scale=${w}:${h}:flags=area,format=gray`, '-f', 'rawvideo', '-'], { stdio: ['ignore', 'pipe', 'inherit'] });
    ff.stdout.on('data', (chunk) => {
      for (let o = 0; o < chunk.length;) {
        const cur = frames[i % 3], take = Math.min(N - fill, chunk.length - o);
        chunk.copy(cur, fill, o, o + take);
        fill += take; o += take;
        if (fill === N) { frame(cur); fill = 0; }
      }
    });
    ff.on('error', reject);
    ff.on('exit', (c) => (c === 0 ? resolve() : reject(new Error(`ffmpeg exited ${c} while scanning the picture`))));
  });
  const total = i;
  // runs of frames where a test holds, as [first, last] frame indices
  const runs = (test) => {
    const out = [];
    for (let j = 0, s = -1; j <= total; j++) {
      if (j < total && test(j)) { if (s < 0) s = j; } else if (s >= 0) { out.push([s, j - 1]); s = -1; }
    }
    return out;
  };
  // frame j is still when it matches the one before; the run starts on the frame before that
  const still = runs((j) => j > 0 && moved[j] < STILL).map(([a, b]) => [a - 1, b]);
  // the render is encoded in chunks, and the keyframe that starts each one shifts a
  // few edge pixels: bridge a gap of a frame or two that barely changed
  for (let k = still.length - 1; k > 0; k--) {
    const gap = [];
    for (let j = still[k - 1][1] + 1; j <= still[k][0]; j++) gap.push(moved[j]);
    if (gap.length <= 2 && gap.every((m) => m < STILL * 10)) still.splice(k - 1, 2, [still[k - 1][0], still[k][1]]);
  }
  // a one-frame glitch: frame j differs from both neighbours, which match each other
  const blips = [];
  for (let j = 1; j < total - 1; j++) {
    const lo = Math.min(moved[j], moved[j + 1]);
    if (lo > 0.02 && skip[j + 1] < 0.25 * lo) blips.push(j);
  }
  // flashing: opposing luminance swings of ≥ 0.1 (darker state < 0.8) in any one second,
  // in the whole frame or a quarter of it; two swings make a flash
  let flash = { count: 0, at: 0 };
  for (let r = 0; r < 5; r++) {
    const swings = [];
    let hi = luma[0]?.[r] ?? 0, lo = hi, dir = 0; // dir: the last swing went up (1) or down (-1)
    for (let j = 1; j < total; j++) {
      const l = luma[j][r];
      if (dir >= 0) hi = Math.max(hi, l);
      if (dir <= 0) lo = Math.min(lo, l);
      if (dir >= 0 && hi - l >= 0.1 && l < 0.8) { swings.push(j); dir = -1; lo = l; }
      else if (dir <= 0 && l - lo >= 0.1 && lo < 0.8) { swings.push(j); dir = 1; hi = l; }
    }
    for (let a = 0, b = 0; b < swings.length; b++) {
      while (swings[b] - swings[a] >= fps) a++;
      const count = Math.floor((b - a + 1) / 2);
      if (count > flash.count) flash = { count, at: swings[a] / fps };
    }
  }
  return { fps, total, still, blips, flash, blank: runs((j) => blank[j]) };
}

// Seconds it takes to read the words on screen (motion-design.md §4: about 3 English
// words or 4–5 CJK characters a second), plus half a second to find them.
const readingTime = (texts) => {
  const s = texts.join(' ');
  const cjk = (s.match(/[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]/g) || []).length;
  const latin = (s.match(/[A-Za-z0-9]/g) || []).length; // ≈ 5 per word, whether a box holds a word or a letter
  return 0.5 + cjk / 4.5 + latin / 5 / 3;
};

async function pictureReport(file, v, scenes, issues, textAt) {
  let r;
  try { r = await scanPicture(file, v); } catch (e) { log(`  picture: not scanned (${e.message})`); return; }
  const { fps, total } = r;
  const t = (f) => `${(f / fps).toFixed(2)}s`;
  const at = (f) => { const s = scenes?.filter((x) => x.start <= f / fps + 1e-6).pop(); return s ? `, "${s.id}"` : ''; };
  // the last run of still frames is the closing hold the contract asks for
  let holds = r.still.filter(([a, b]) => b < total - 1 && (b - a) / fps >= 1.5).map(([a, b]) => ({ a, b }));
  // a hold with words on screen is the viewer reading them: fine for as long as that takes
  const texts = textAt && holds.length ? await textAt(holds.map((h) => (h.a + h.b) / 2 / fps)).catch(() => null) : null;
  holds.forEach((h, k) => { if (texts?.[k]?.length) Object.assign(h, { words: texts[k], need: readingTime(texts[k]) }); });
  const reads = holds.filter((h) => h.need && (h.b - h.a) / fps <= h.need + 1);
  holds = holds.filter((h) => !reads.includes(h));
  const longest = r.still.filter(([, b]) => b < total - 1).reduce((m, [a, b]) => Math.max(m, (b - a) / fps), 0);
  const blank = r.blank.filter(([a, b]) => (b - a + 1) / fps >= 0.3);
  log(`  picture: ${holds.length ? `${holds.length} still stretch${holds.length > 1 ? 'es' : ''} ≥ 1.5 s` : `still ≤ ${longest.toFixed(1)}s at a stretch`}${reads.length ? `, ${reads.length} reading hold${reads.length > 1 ? 's' : ''}` : ''}, ${r.blips.length} one-frame glitch${r.blips.length === 1 ? '' : 'es'}, ${r.flash.count > 3 ? 'FLASHING' : 'no flashing'}, ${blank.length ? `${blank.length} blank stretch${blank.length > 1 ? 'es' : ''}` : 'no blank frames'}`);
  const quote = (w) => `"${w.join(' ').replace(/\s+/g, ' ').slice(0, 40)}"`;
  for (const h of reads.slice(0, 6)) log(`    read: still ${t(h.a)}–${t(h.b)} (${((h.b - h.a) / fps).toFixed(1)}s${at(h.a)}) while ${quote(h.words)} is read (≈ ${h.need.toFixed(1)}s)`);
  // pointers to frames worth a look, not failures (a breath before the big hit is a still)
  for (const h of holds.slice(0, 6)) log(`    look: nothing moves ${t(h.a)}–${t(h.b)} (${((h.b - h.a) / fps).toFixed(1)}s${at(h.a)})${h.need ? `, longer than the ≈ ${h.need.toFixed(1)}s ${quote(h.words)} takes to read` : ''}: is the hold alive, or meant to stop?`);
  for (const j of r.blips.slice(0, 6)) log(`    look: frame at ${t(j)}${at(j)} differs from both neighbours (a one-frame glitch?)`);
  for (const [a, b] of blank.slice(0, 4)) log(`    look: blank ${t(a)}–${t(b + 1)}${at(a)}`);
  if (r.flash.count > 3) issues.push(`flashing: ${r.flash.count} flashes within one second at ${r.flash.at.toFixed(2)}s (keep it to 3 or fewer: photosensitivity)`);
}

async function report(file, srt, stems = null, voice = [], scenes = null, textAt = null) {
  const speechSrc = stems?.voiceWav || file;
  const p = ffprobe(file);
  const v = p.streams.find((s) => s.codec_type === 'video');
  const a = p.streams.find((s) => s.codec_type === 'audio');
  const s = p.streams.find((x) => x.codec_type === 'subtitle');
  const dur = Number(p.format.duration);
  // r_frame_rate is the stream's nominal rate; avg_frame_rate drifts (30.001) after concat
  const [n, d] = (v.r_frame_rate || v.avg_frame_rate || '0/1').split('/').map(Number);
  const issues = [];
  log(`  video: ${v.codec_name} ${v.width}x${v.height} ${(n / d).toFixed(3)}fps ${v.pix_fmt}, ${v.nb_frames ?? '?'} frames, ${dur.toFixed(3)}s`);
  if (a) {
    const ad = Number(a.duration || dur);
    log(`  audio: ${a.codec_name} ${a.sample_rate}Hz ${a.channels}ch, ${ad.toFixed(3)}s`);
    if (Math.abs(ad - Number(v.duration || dur)) > 0.1) issues.push(`audio/video duration differ by ${(ad - Number(v.duration)).toFixed(3)}s`);
    const vd = spawnSync('ffmpeg', ['-hide_banner', '-i', file, '-map', '0:a', '-af', 'volumedetect', '-f', 'null', '-'], { encoding: 'utf8' });
    const mean = vd.stderr.match(/mean_volume: ([-\d.]+) dB/)?.[1], max = vd.stderr.match(/max_volume: ([-\d.]+) dB/)?.[1];
    if (mean) log(`  loudness: mean ${mean} dB, peak ${max} dB`);
    if (mean && Number(mean) < -50) issues.push('audio track is (near) silent');
  } else log('  audio: none');
  if (s) log(`  subtitle track: ${s.codec_name}`);
  if (srt && fs.existsSync(srt)) {
    const body = fs.readFileSync(srt, 'utf8');
    const times = [...body.matchAll(/(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})/g)];
    const toS = (m, o) => Number(m[o]) * 3600 + Number(m[o + 1]) * 60 + Number(m[o + 2]) + Number(m[o + 3]) / 1000;
    let prevEnd = 0, overlaps = 0;
    for (const m of times) { if (toS(m, 1) < prevEnd - 1e-3) overlaps++; prevEnd = toS(m, 5); }
    log(`  srt: ${times.length} cues, first ${times.length ? toS(times[0], 1).toFixed(2) : '-'}s, last ends ${prevEnd.toFixed(2)}s`);
    if (prevEnd > dur + 0.05) issues.push(`last subtitle ends after video (${prevEnd.toFixed(2)}s > ${dur.toFixed(2)}s)`);
    if (overlaps) issues.push(`${overlaps} overlapping subtitle cues`);
    // A/V sync: every cue that follows a pause should start where speech starts.
    if (a && times.length && stems?.noSync) log('  a/v sync: n/a (the track has music; re-run `gaga render` to measure on the voice stem)');
    else if (a && times.length) {
      const onsets = speechOnsets(speechSrc, 0.18);
      const offs = [];
      let lastEnd = -1;
      for (const m of times) {
        const st = toS(m, 1);
        if (st - lastEnd > 0.3) {
          const near = onsets.reduce((b, o) => (Math.abs(o - st) < Math.abs(b - st) ? o : b), Infinity);
          if (Number.isFinite(near)) offs.push(st - near);
        }
        lastEnd = toS(m, 5);
      }
      if (offs.length) {
        const abs = offs.map(Math.abs).sort((x, y) => x - y);
        const med = abs[Math.floor(abs.length / 2)], worst = abs[abs.length - 1];
        log(`  a/v sync: ${offs.length} cue onsets vs speech onsets — median ${(med * 1000).toFixed(0)} ms, worst ${(worst * 1000).toFixed(0)} ms`);
        if (worst > 0.3) issues.push(`subtitle/speech onset mismatch up to ${(worst * 1000).toFixed(0)} ms`);
      }
    }
  }
  // music ↔ voice balance (from the stems): the bed should sit well under speech
  if (stems?.music && stems.voice) {
    const v = new Float32Array(stems.voice.buffer, stems.voice.byteOffset, stems.voice.byteLength / 4);
    const m = new Float32Array(stems.music.buffer, stems.music.byteOffset, stems.music.byteLength / 4);
    const inSpan = (i) => stems.spans.some(([a, b]) => i >= a * 48000 && i < b * 48000);
    let vs = 0, ms = 0, mg = 0, nv = 0, ng = 0;
    for (let i = 0; i < Math.min(v.length, m.length); i += 4) {
      if (inSpan(i)) { vs += v[i] * v[i]; ms += m[i] * m[i]; nv++; } else { mg += m[i] * m[i]; ng++; }
    }
    const dB = (x, n) => 10 * Math.log10(x / Math.max(1, n) + 1e-12);
    const under = dB(vs, nv) - dB(ms, nv), gaps = dB(mg, ng) - dB(vs, nv);
    log(`  music: ${under.toFixed(1)} dB under the voice while it speaks${stems.ducked ? ' (before side-chain ducking)' : ''}, ${gaps >= 0 ? '+' : ''}${gaps.toFixed(1)} dB vs the voice in the gaps`);
    if (!stems.ducked && nv && under < 9) issues.push(`music is only ${under.toFixed(1)} dB under the voice (aim for 10–18 dB; lower music.volume or deepen music.duck)`);
    if (!stems.ducked && nv && under > 22) issues.push(`music is ${under.toFixed(1)} dB under the voice — probably inaudible (raise music.volume)`);
  }
  // Voice placement: each clip's own speech onset, shifted to where the timeline
  // put it, should match an onset in the final mix (covers uncaptioned lines).
  const clips = a ? voice.filter((c) => fs.existsSync(c.file) && c.start >= 0 && c.start < dur) : [];
  if (clips.length) {
    const onsets = speechOnsets(speechSrc, 0.1);
    const offs = clips.map((c) => {
      const expect = c.start + (speechOnsets(c.file, 0.05)[0] ?? 0);
      const near = onsets.reduce((b, o) => (Math.abs(o - expect) < Math.abs(b - expect) ? o : b), Infinity);
      return { id: c.id, off: near - expect };
    });
    const abs = offs.map((o) => Math.abs(o.off)).sort((x, y) => x - y);
    const med = abs[Math.floor(abs.length / 2)], worst = offs.reduce((b, o) => (Math.abs(o.off) > Math.abs(b.off) ? o : b));
    log(`  voice sync: ${clips.length} clips vs speech onsets — median ${(med * 1000).toFixed(0)} ms, worst ${(Math.abs(worst.off) * 1000).toFixed(0)} ms (${worst.id})`);
    if (Math.abs(worst.off) > 0.15) issues.push(`voice clip "${worst.id}" starts ${(worst.off * 1000).toFixed(0)} ms off its timeline position`);
  }
  await pictureReport(file, v, scenes, issues, textAt);
  if (issues.length) log(`  ⚠ ${issues.join('\n  ⚠ ')}`);
  else log('  checks: ok');
  return issues;
}

// ---------------------------------------------------------------------------
// still frames / contact sheet (for self-review before a full render)
// ---------------------------------------------------------------------------
const PHONE_W = 390; // CSS px across a phone held upright

// Runs in the page: draws frame f and returns its text boxes, each with the
// contrast between the text and what is behind it, measured on the pixels: those
// nearest the text's colour are the text, the far third around it the ground.
async function measureText(f) {
  const cv = window.__CV;
  if (!cv.textBoxes) return null;
  const boxes = await cv.textBoxes(f);
  let img = null;
  try { img = cv.ctx.getImageData(0, 0, cv.canvas.width, cv.canvas.height); } catch { return boxes; }
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const { width: cw, height: ch, data } = img, S = cv.scale;
  for (const b of boxes) {
    const rgb = b.color?.startsWith('#') ? [1, 3, 5].map((i) => parseInt(b.color.slice(i, i + 2), 16)) : b.color?.match(/[\d.]+/g)?.slice(0, 3).map(Number);
    if (!rgb || rgb.length < 3 || rgb.some(Number.isNaN)) continue;
    const pad = (b.y1 - b.y0) * 0.25;
    const x0 = Math.max(0, Math.floor((b.x0 - pad) * S)), x1 = Math.min(cw, Math.ceil((b.x1 + pad) * S));
    const y0 = Math.max(0, Math.floor((b.y0 - pad) * S)), y1 = Math.min(ch, Math.ceil((b.y1 + pad) * S));
    const px = [];
    for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) {
      const i = (y * cw + x) * 4, r = data[i], g = data[i + 1], bl = data[i + 2];
      px.push([(r - rgb[0]) ** 2 + (g - rgb[1]) ** 2 + (bl - rgb[2]) ** 2, lum(r, g, bl)]);
    }
    if (px.length < 32) continue;
    px.sort((p, q) => p[0] - q[0]);
    const near = px.slice(0, Math.max(1, Math.round(px.length * 0.03)));
    const lt = near.reduce((s, p) => s + p[1], 0) / near.length;
    const far = px.slice(Math.floor(px.length * (2 / 3))).map((p) => p[1]).sort((p, q) => p - q);
    const lb = far[Math.floor(far.length / 2)];
    b.contrast = (Math.max(lt, lb) + 0.05) / (Math.min(lt, lb) + 0.05);
  }
  return boxes;
}

async function still(opts) {
  const { dir, html } = resolveProject(opts._[1]);
  if (!opts.noTts && opts.tts) await tts(dir);
  const outDir = path.resolve(opts.out || path.join(dir, 'build', 'stills'));
  fs.mkdirSync(outDir, { recursive: true });
  for (const f of fs.readdirSync(outDir)) if (/^(again-)?t[\d.]+\.png$|^contact-sheet(-\d+)?\.png$|^text\.txt$/.test(f)) fs.rmSync(path.join(outDir, f));
  const browser = await launch();
  const { page, info, errors } = await openComposition(browser, html, { render: '1', scale: String(opts.scale || 0.5), subs: opts.subs ? '1' : '0' });
  if (errors.length) log(`⚠ page errors:\n  ${errors.join('\n  ')}`);
  if (info.missingFonts?.length) log(`⚠ fonts not loaded: ${info.missingFonts.join(', ')}`);
  let times;
  if (opts.at) times = String(opts.at).split(',').map(Number);
  else {
    // default: 3 probes per scene (entering, middle, just before exit)
    // --scenes hook,curve or --scenes rule..wonky: probe only those scenes (long videos)
    const pick = opts.scenes ? String(opts.scenes).split(',').flatMap((x) => {
      const [a, b] = x.split('..');
      const ia = info.scenes.findIndex((s) => s.id === a), ib = b ? info.scenes.findIndex((s) => s.id === b) : ia;
      if (ia < 0 || ib < 0) die(`--scenes: no scene "${ia < 0 ? a : b}" (scenes: ${info.scenes.map((s) => s.id).join(', ')})`);
      return info.scenes.slice(Math.min(ia, ib), Math.max(ia, ib) + 1).map((s) => s.id);
    }) : null;
    times = [];
    info.scenes.forEach((s, i) => {
      if (pick && !pick.includes(s.id)) return;
      const next = info.scenes[i + 1];
      const settled = (next && next.start < s.start + s.dur ? next.start : s.start + s.dur) - 0.1;
      times.push(s.start + Math.min(0.5, s.dur * 0.2), s.start + s.dur * 0.5, settled);
    });
  }
  const files = [];
  // text on each probe: cut off by the frame edge, sitting where captions go,
  // too small on a phone, or too close in value to what is behind it
  const band = info.captionBand;
  const phone = PHONE_W / info.width; // a phone held upright shows the frame this wide
  // glyphs drawn one by one (a letter-by-letter reveal) are checked as the line they make
  const lines = (boxes) => {
    const out = [];
    for (const b of [...(boxes || [])].sort((p, q) => p.x0 - q.x0)) {
      const h = b.y1 - b.y0;
      const l = out.find((o) => o.color === b.color && Math.abs(o.y1 - b.y1) < h * 0.35 && Math.abs((o.y1 - o.y0) - h) < h * 0.5 && b.x0 - o.x1 < h * 0.8);
      if (!l) { out.push({ ...b, contrasts: b.contrast ? [b.contrast] : [] }); continue; }
      l.text += b.x0 - l.x1 > h * 0.25 ? ` ${b.text}` : b.text;
      Object.assign(l, { x0: Math.min(l.x0, b.x0), y0: Math.min(l.y0, b.y0), x1: Math.max(l.x1, b.x1), y1: Math.max(l.y1, b.y1) });
      if (b.contrast) l.contrasts.push(b.contrast);
    }
    for (const l of out) l.contrast = l.contrasts.sort((p, q) => p - q)[Math.floor(l.contrasts.length / 2)];
    return out;
  };
  const textIssues = (boxes) => lines(boxes).flatMap((b) => {
    const w = b.x1 - b.x0, h = b.y1 - b.y0;
    if (w <= 0 || h < 9) return [];
    const vw = Math.min(b.x1, info.width) - Math.max(b.x0, 0), vh = Math.min(b.y1, info.height) - Math.max(b.y0, 0);
    const shown = vw > 0 && vh > 0 ? (vw * vh) / (w * h) : 0;
    const out = [];
    if (shown > 0.1 && shown < 0.9) out.push({ text: b.text, what: 'cut off by the frame edge' });
    if (band && shown > 0.1 && b.y1 > band.y0 + 4 && b.y0 < band.y1 && b.x1 > band.x0 && b.x0 < band.x1) out.push({ text: b.text, what: `in the caption band (text ${Math.round(b.y0)}–${Math.round(b.y1)} px, captions from ${Math.round(band.y0)})` });
    if (shown >= 0.9 && h * phone < 6) out.push({ text: b.text, what: `small on a phone (${(h * phone).toFixed(1)} px tall at ${PHONE_W} px wide)` });
    // large text (WCAG: 3:1) is about 14 px tall at phone width; the rest needs 4.5:1
    const need = h * phone >= 14 ? 3 : 4.5;
    if (shown >= 0.9 && b.contrast && b.contrast < need) out.push({ text: b.text, what: `contrast ${b.contrast.toFixed(1)}:1 against what is behind it (needs ${need}:1)` });
    return out;
  });
  const probeText = (f) => page.evaluate(measureText, f);
  // the same string with the same kind of problem, whatever the exact numbers
  const issueKey = (x) => `${x.text}|${x.what.replace(/[\d.]+/g, '#')}`;
  const flagged = [];
  const shots = new Map(); // frame → hash of the probe, to draw it again in a fresh page
  let boxesSeen = 0;
  for (const t of times) {
    const f = Math.min(info.totalFrames - 1, Math.max(0, Math.round(t * info.fps)));
    const boxes = await probeText(f);
    if (!boxes) await page.evaluate((f) => window.__CV.renderFrame(f), f);
    const url = await page.evaluate(() => window.__CV.capture('image/png'));
    shots.set(f, crypto.createHash('sha1').update(url).digest('hex'));
    const file = path.join(outDir, `t${(f / info.fps).toFixed(2).padStart(6, '0')}.png`);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    // --phone: the probe at the size a phone shows it
    if (opts.phone) await run('ffmpeg', ['-y', '-loglevel', 'error', '-i', file, '-vf', `scale=${PHONE_W}:-2:flags=area`, '-update', '1', `${file}.png`]).then(() => fs.renameSync(`${file}.png`, file));
    files.push(file);
    boxesSeen += boxes?.length || 0;
    const found = textIssues(boxes);
    // still there 0.3 s later: not text on its way in or out
    if (found.length) {
      const later = textIssues(await probeText(Math.min(info.totalFrames - 1, f + Math.round(0.3 * info.fps)))).map(issueKey);
      for (const x of found) if (later.includes(issueKey(x))) flagged.push({ t: f / info.fps, ...x });
    }
  }
  // every frame is a pure function of time: a few probes drawn again in a fresh
  // page, in reverse order, must come out identical
  const again = await openComposition(browser, html, { render: '1', scale: String(opts.scale || 0.5), subs: opts.subs ? '1' : '0' });
  const picks = [...shots.keys()].filter((_, i, a) => a.length <= 3 || i % Math.ceil(a.length / 3) === 0).reverse();
  const differs = [];
  for (const f of picks) {
    await again.page.evaluate((f) => window.__CV.renderFrame(f), f);
    const url = await again.page.evaluate(() => window.__CV.capture('image/png'));
    if (crypto.createHash('sha1').update(url).digest('hex') === shots.get(f)) continue;
    const file = path.join(outDir, `again-t${(f / info.fps).toFixed(2)}.png`);
    fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
    differs.push({ t: f / info.fps, file });
  }
  await browser.close();
  log(`✔ ${files.length} stills → ${path.relative(process.cwd(), outDir)}`);
  if (boxesSeen) {
    // each string once, with the probes it was seen on
    const groups = new Map();
    for (const x of flagged) {
      const g = groups.get(issueKey(x)) || groups.set(issueKey(x), { ...x, at: [] }).get(issueKey(x));
      g.at.push(x.t);
    }
    const rows = [...groups.values()].map((g) => `"${g.text}" ${g.what} (${g.at.slice(0, 4).map((t) => `${t.toFixed(2)}s`).join(', ')}${g.at.length > 4 ? ` +${g.at.length - 4}` : ''})`);
    log(`  text: ${rows.length ? `${rows.length} to look at` : `clear of the frame edges${band ? ' and the caption band' : ''}, readable on a phone`} (${boxesSeen} strings on ${files.length} probes)`);
    for (const r of rows.slice(0, 12)) log(`    look: ${r}`);
    if (rows.length > 12) {
      fs.writeFileSync(path.join(outDir, 'text.txt'), `${rows.join('\n')}\n`);
      log(`    … ${rows.length - 12} more in ${path.relative(process.cwd(), path.join(outDir, 'text.txt'))}`);
    }
  }
  if (!differs.length) log(`  repeat: ${picks.length} probe${picks.length === 1 ? '' : 's'} drawn again in a fresh page, in reverse order: identical`);
  for (const d of differs) log(`  ⚠ repeat: the frame at ${d.t.toFixed(2)}s comes out different when drawn again in a fresh page (state kept between frames, Math.random, the clock?): ${path.relative(process.cwd(), d.file)}`);
  if (opts.sheet) {
    // a long video makes one sheet too tall to read: split it into pages of
    // `--rows` rows (default 6, i.e. 6 scenes at 3 probes each)
    const cols = Number(opts.cols || 3), perPage = cols * Number(opts.rows || 6);
    const sorted = files.slice().sort();
    const pages = Math.ceil(sorted.length / perPage);
    const tmpList = path.join(outDir, '.sheet.txt');
    for (let k = 0; k < pages; k++) {
      const part = sorted.slice(k * perPage, (k + 1) * perPage);
      const sheet = path.join(outDir, pages > 1 ? `contact-sheet-${k + 1}.png` : 'contact-sheet.png');
      fs.writeFileSync(tmpList, part.map((f) => `file '${f.replace(/'/g, "'\\''")}'`).join('\n'));
      await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', tmpList, '-vf', `scale=${opts.phone ? PHONE_W : 640}:-2,tile=${cols}x${Math.ceil(part.length / cols)}:padding=6:color=0x222222`, '-frames:v', '1', sheet]);
      const span = (f) => path.basename(f).slice(1, -4).replace(/^0+(?=\d)/, '');
      log(`  contact sheet → ${path.relative(process.cwd(), sheet)}${pages > 1 ? `  (${span(part[0])}–${span(part[part.length - 1])}s)` : ''}`);
    }
    fs.rmSync(tmpList, { force: true });
  }
  log(`  timeline: ${info.scenes.map((s) => `${s.id} ${s.start.toFixed(2)}–${(s.start + s.dur).toFixed(2)}s`).join(' | ')}`);
}

// ---------------------------------------------------------------------------
// gif preview (for READMEs)
// ---------------------------------------------------------------------------
async function gif(opts) {
  const src = path.resolve(opts._[1] || die('missing <video.mp4>'));
  const out = path.resolve(opts.out || src.replace(/\.mp4$/i, '.gif'));
  const width = Number(opts.width || 480), rate = Number(opts.fps || 12);
  const trim = [];
  if (opts.from) trim.push('-ss', String(opts.from));
  if (opts.dur) trim.push('-t', String(opts.dur));
  const vf = `fps=${rate},scale=${width}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=${opts.colors || 128}:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle`;
  await run('ffmpeg', ['-y', '-loglevel', 'error', ...trim, '-i', src, '-vf', vf, '-loop', '0', out]);
  log(`✔ ${path.relative(process.cwd(), out)} (${(fs.statSync(out).size / 1024).toFixed(0)} KB)`);
}

// ---------------------------------------------------------------------------
// init — a blank project (the render contract only), or a preset's style
// (not its example video) with --preset
// ---------------------------------------------------------------------------
async function init(opts) {
  const dir = path.resolve(opts._[1] || die('missing <dir>'));
  const slug = opts.preset && opts.preset !== true ? String(opts.preset) : null;
  const tpl = slug ? path.join(ROOT, 'presets', slug, 'video.html') : path.join(ROOT, 'scripts', 'templates', 'blank.html');
  if (!fs.existsSync(tpl)) die(`unknown preset "${slug}". Available: ${fs.readdirSync(path.join(ROOT, 'presets')).filter((d) => fs.existsSync(path.join(ROOT, 'presets', d, 'video.html'))).join(', ')}`);
  if (fs.existsSync(path.join(dir, 'video.html')) && !opts.force) die(`${dir}/video.html exists (use --force)`);
  fs.mkdirSync(dir, { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'runtime', 'video-gaga.js'), path.join(dir, 'video-gaga.js'));
  // (older compositions loaded canvas-video.js)
  let html = fs.readFileSync(tpl, 'utf8'), kept = [], dropped = [];
  if (slug) {
    const { scaffoldFromPreset } = await import('./scaffold.mjs');
    ({ html, kept, dropped } = scaffoldFromPreset(html, { slug }));
  }
  let htmlSrc = html.replace(/src="[^"]*(?:video-gaga|canvas-video)\.js"/, 'src="video-gaga.js"');
  htmlSrc = htmlSrc.replace(/<title>[^<]*<\/title>/, `<title>${path.basename(dir)}</title>`);
  if (opts.ratio) {
    const [w, h] = { '16:9': [1920, 1080], '9:16': [1080, 1920], '1:1': [1080, 1080], '4:5': [1080, 1350] }[opts.ratio] || die('ratio must be 16:9, 9:16, 1:1 or 4:5');
    htmlSrc = htmlSrc.replace(/width:\s*\d+/, `width: ${w}`).replace(/height:\s*\d+/, `height: ${h}`);
  }
  fs.writeFileSync(path.join(dir, 'video.html'), htmlSrc);
  // the preset's assets (maps, HDRIs, models) that the kept code still names: their
  // manifest entries, original pictures and credits; the files are then restored
  const srcAssets = path.join(path.dirname(tpl), 'assets'), dstAssets = path.join(dir, 'assets');
  const manifest = readManifest(srcAssets);
  const used = Object.keys(manifest).filter((k) => new RegExp(`['"\`]assets/${k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"\`]`).test(htmlSrc));
  if (used.length) {
    writeManifest(dstAssets, Object.fromEntries(used.map((k) => [k, manifest[k]])));
    for (const k of used) {
      const src = manifest[k].source;
      if (src?.startsWith('src/')) fs.cpSync(path.join(srcAssets, src), path.join(dstAssets, src));
    }
    const credits = path.join(srcAssets, 'CREDITS.md');
    if (fs.existsSync(credits)) {
      const lines = fs.readFileSync(credits, 'utf8').split('\n').filter((l) => !l.startsWith('- `') || used.includes(l.slice(3, l.indexOf('`', 3))));
      fs.writeFileSync(path.join(dstAssets, 'CREDITS.md'), lines.join('\n'));
    }
    const { failed } = await restoreAssets(dir);
    for (const f of failed) log(`  ⚠ could not restore ${f.key} (render will retry): ${f.error}`);
  }
  // the example's narration.json is not copied: the words are written for this brief
  fs.writeFileSync(path.join(dir, '.gitignore'), 'build/\nout/\n');
  if (slug) {
    log(`✔ scaffolded ${path.relative(process.cwd(), dir) || '.'} from the "${slug}" style`);
    log(`  kept:     ${kept.join(' · ')} · CV.create look (size, fonts, transition, captions, overlay)`);
    log(`  left out: the example's scenes, score and narration${dropped.length ? ` · ${dropped.join(' · ')}` : ''}`);
  } else {
    log(`✔ scaffolded ${path.relative(process.cwd(), dir) || '.'} (blank: the render contract only)`);
    log('  look:     design it for this brief; a preset\'s KIT (presets/<slug>/video.html) can be borrowed');
  }
  log(`  next:     write the scenes, narration.json and the score (music: { … }) for this brief`);
  log(`  preview:  open ${path.join(dir, 'video.html')}`);
  log(`  render:   node ${path.relative(process.cwd(), path.join(ROOT, 'scripts', 'gaga.mjs'))} render ${path.relative(process.cwd(), dir) || '.'}`);
}

// ---------------------------------------------------------------------------
// moodboard — the style directions side by side on one page, for the user to pick
// ---------------------------------------------------------------------------
async function moodboard(opts) {
  const dirs = opts._.slice(1).map((p) => resolveProject(p));
  if (dirs.length < 2) die('give two or more preview projects: gaga moodboard .gaga-previews/style-a .gaga-previews/style-b .gaga-previews/style-c');
  if (!has('ffmpeg')) die('ffmpeg not found (macOS: brew install ffmpeg)');
  const { themeFromHtml, describeScore, buildMoodboardPage } = await import('./moodboard.mjs');
  const out = path.resolve(opts.out || path.join(path.dirname(dirs[0].dir), 'moodboard.html'));
  const outDir = path.dirname(out);
  fs.mkdirSync(outDir, { recursive: true });
  const clipMax = Number(opts.clip ?? 6);
  const rel = (f) => path.relative(outDir, f).split(path.sep).join('/');
  const directions = [], fontLinks = [];
  let lang = opts.lang ? String(opts.lang) : null;
  const browser = await launch();
  for (const [i, { dir, html }] of dirs.entries()) {
    const letter = String.fromCharCode(65 + i);
    const metaFile = path.join(dir, 'moodboard.json');
    const meta = fs.existsSync(metaFile) ? JSON.parse(fs.readFileSync(metaFile, 'utf8')) : {};
    const theme = themeFromHtml(fs.readFileSync(html, 'utf8'));
    fontLinks.push(...theme.fontLinks);
    const mb = path.join(dir, 'build', 'moodboard');
    fs.rmSync(mb, { recursive: true, force: true });
    fs.mkdirSync(mb, { recursive: true });

    // three frames (entering, middle, settled) from the preview, at half size
    const { page, info, errors } = await openComposition(browser, html, { render: '1', scale: '0.5', subs: '0' });
    if (errors.length) log(`  ⚠ ${letter} page errors:\n    ${errors.join('\n    ')}`);
    if (info.missingFonts?.length) log(`  ⚠ ${letter} fonts not loaded: ${info.missingFonts.join(', ')}`);
    lang ??= info.lang;
    const len = Math.min(info.duration, clipMax);
    const frames = [];
    for (const [k, t] of [len * 0.2, len * 0.5, Math.max(0, len - 0.1)].entries()) {
      const f = Math.min(info.totalFrames - 1, Math.round(t * info.fps));
      const url = await page.evaluate(async (f) => { await window.__CV.renderFrame(f); return window.__CV.capture('image/jpeg', 0.88); }, f);
      const file = path.join(mb, `frame-${k + 1}.jpg`);
      fs.writeFileSync(file, Buffer.from(url.split(',')[1], 'base64'));
      frames.push(file);
    }
    await page.close();

    // a looping motion sample (with the draft score, if this direction has one)
    let clip = null;
    if (!opts.noClip) {
      const scale = [0.5, 0.4, 0.25].find((s) => Math.round(info.width * s) % 2 === 0 && Math.round(info.height * s) % 2 === 0) || 1;
      const file = path.join(mb, 'clip.mp4');
      log(`▸ ${letter}: motion sample (${len.toFixed(1)}s)`);
      const r = spawnSync(process.execPath, [fileURLToPath(import.meta.url), 'render', dir, '--out', file, '--to', len.toFixed(2), '--scale', String(scale), '--subs', 'none', '--no-tts', '--format', 'jpeg', '--crf', '23'], { encoding: 'utf8' });
      if (fs.existsSync(file)) clip = file;
      else log(`  ⚠ ${letter}: no motion sample (render failed):\n${(r.stderr || r.stdout || '').trim().split('\n').slice(-4).join('\n')}`);
    }
    const hasSound = !!(clip && ffprobe(clip).streams.some((s) => s.codec_type === 'audio'));

    const palette = (meta.palette || theme.colors).slice(0, 8).map((c) => (typeof c === 'string' ? { hex: c } : { hex: c.hex, name: c.name ?? c.note ?? '' }));
    const type = (meta.type || theme.fonts.map((f) => ({ family: f.family, stack: f.stack, role: f.name }))).slice(0, 4);
    directions.push({
      id: path.basename(dir), letter, name: meta.name || path.basename(dir), pitch: meta.pitch, recommended: !!meta.recommended,
      keywords: meta.keywords, ratio: [info.width, info.height],
      clip: clip && rel(clip), poster: rel(frames[2]), frames: frames.map(rel), hasSound,
      palette, type: type.map((t) => ({ ...t, sample: t.sample ?? meta.title ?? opts.title })),
      motion: meta.motion, music: meta.music || describeScore(info.score),
    });
    log(`  ${letter}  ${directions.at(-1).name}${meta.recommended ? '  (recommended)' : ''}${fs.existsSync(metaFile) ? '' : '  · no moodboard.json: name, pitch, motion and music are missing'}`);
  }
  await browser.close();
  if (directions.filter((d) => d.recommended).length !== 1) log('  ⚠ mark exactly one direction "recommended": true in its moodboard.json');
  const title = opts.title ? String(opts.title) : '';
  // the page speaks the user's language: their title and the directions' names, else the composition's
  if (!opts.lang && !/^(ja|ko)/.test(lang || '') && /[\u3400-\u9fff]/.test([title, ...directions.flatMap((d) => [d.name, d.pitch])].join(''))) lang = 'zh';
  fs.writeFileSync(out, buildMoodboardPage({ title, lang: lang || 'en', directions, fontLinks }));
  log(`✔ moodboard → ${path.relative(process.cwd(), out)}  (${directions.length} directions)`);
  if (opts.wait) return waitForPick(out, dirs.map((d) => d.dir), opts);
  if (opts.open) openInBrowser(pathToFileURL(out).href);
}

function openInBrowser(url) {
  const [cmd, args] = process.platform === 'darwin' ? ['open', [url]] : process.platform === 'win32' ? ['cmd', ['/c', 'start', '', url]] : ['xdg-open', [url]];
  try { spawn(cmd, args, { stdio: 'ignore', detached: true }).on('error', () => {}).unref(); } catch {}
}

// Serve the page on localhost and wait for the user's click; prints the pick.
async function waitForPick(out, dirs, opts) {
  const http = await import('node:http');
  const root = [path.dirname(out), ...dirs].reduce((a, b) => { while (!(b + path.sep).startsWith(a + path.sep) && a !== path.dirname(a)) a = path.dirname(a); return a; });
  const types = { '.html': 'text/html; charset=utf-8', '.mp4': 'video/mp4', '.jpg': 'image/jpeg', '.png': 'image/png' };
  const page = '/' + path.relative(root, out).split(path.sep).map(encodeURIComponent).join('/');
  const pickPath = page.replace(/[^/]*$/, 'pick');
  const pickFile = path.join(path.dirname(out), 'pick.json');
  const pick = await new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const url = new URL(req.url, 'http://x');
      if (req.method === 'POST' && url.pathname === pickPath) {
        let body = '';
        req.on('data', (c) => { body += c; if (body.length > 1e5) req.destroy(); });
        req.on('end', () => {
          let p;
          try { p = JSON.parse(body); } catch { res.writeHead(400).end(); return; }
          res.writeHead(200, { 'content-type': 'application/json' }).end('{"ok":true}');
          server.close();
          resolve(p);
        });
        return;
      }
      const file = path.join(root, decodeURIComponent(url.pathname));
      if (!file.startsWith(root + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404).end(); return; }
      const size = fs.statSync(file).size, type = types[path.extname(file).toLowerCase()] || 'application/octet-stream';
      const range = req.headers.range?.match(/bytes=(\d*)-(\d*)/);
      if (range) { // video seeking
        const a = range[1] ? Number(range[1]) : Math.max(0, size - Number(range[2]));
        const b = range[1] && range[2] ? Math.min(size - 1, Number(range[2])) : size - 1;
        res.writeHead(206, { 'content-type': type, 'content-range': `bytes ${a}-${b}/${size}`, 'accept-ranges': 'bytes', 'content-length': b - a + 1 });
        fs.createReadStream(file, { start: a, end: b }).pipe(res);
      } else {
        res.writeHead(200, { 'content-type': type, 'content-length': size, 'accept-ranges': 'bytes' });
        fs.createReadStream(file).pipe(res);
      }
    });
    server.listen(Number(opts.port || 0), '127.0.0.1', () => {
      const url = `http://127.0.0.1:${server.address().port}${page}`;
      log(`▸ waiting for a pick at ${url}`);
      if (!opts.noOpen) openInBrowser(url);
    });
    const secs = Number(opts.timeout ?? 600);
    if (secs > 0) setTimeout(() => { server.close(); resolve(null); }, secs * 1000).unref();
  });
  if (!pick) { log('✖ no pick before the timeout: ask the user in the chat which direction they want'); process.exitCode = 3; return; }
  const dir = dirs.find((d) => path.basename(d) === pick.id);
  fs.writeFileSync(pickFile, JSON.stringify({ ...pick, dir }, null, 1));
  log(`✔ picked ${pick.letter}: ${pick.name}  (${dir ? path.relative(process.cwd(), dir) : pick.id})`);
  if (pick.note) log(`  note: ${pick.note}`);
}

// music — render the score on its own (for previewing in the player, or listening)
async function musicCmd(opts) {
  const { dir, html } = resolveProject(opts._[1]);
  const browser = await launch();
  const { page, info, errors } = await openComposition(browser, html, { render: '1', scale: '0.25', subs: '0' });
  if (errors.length) log(`⚠ page errors:\n  ${errors.join('\n  ')}`);
  await page.close();
  await browser.close();
  if (!info.score) die("this composition has no generated music (write one: music: { bpm, key, mode, script: 'score.mjs' } in CV.create and the piece in score.mjs, see docs/music-and-sound.md)");
  const { file, report } = await synthMusic(dir, info.score);
  log(`✔ ${path.relative(process.cwd(), file)}  ${info.duration.toFixed(2)}s`);
  if (report.script) log(`  ${report.key} · ${report.bpm} BPM · written score: ${report.script}`);
  else log(`  ${report.key} · ${report.bpm} BPM · chords ${report.progression} · ${report.layers} layers${report.lead ? ` + ${report.lead} lead` : ''} · bar energy ${report.bars.join(' ')}`);
  if (report.parts && !report.script) log(`  parts (name@bar): ${report.parts.join(' ')}`);
  if (report.mixDb) log(`  mix (dB of the whole): ${Object.entries(report.mixDb).map(([k, v]) => `${k} ${v}`).join(' · ')} · ${report.engine === 'samples' ? 'sampled instruments' : 'built-in synth (no samples: run gaga doctor)'}`);
  log(`  peak ${report.peakDb} dBFS · gaps ${report.gapDb ?? '—'} dB vs the voice (${report.voiceDb ?? '—'} dBFS speech), dips ${report.voiceDuckDb} dB while it speaks · final chord ${report.endChordAt != null ? `at ${report.endChordAt}s` : 'none'}`);
  const L = report.listen;
  if (L) log(`  listen: ${L.ghost ? `${L.ghost.length} ghostly 4-bar window(s)` : 'ghost check needs the samples'} · melody ${L.melodyDb ?? '—'} dB over the rest in 500 Hz–4 kHz (≥ 3) · loudness range ${L.rangeLU ?? '—'} LU · sfx ${L.sfxDb ? `${L.sfxDb.median} dB median over the music (${L.sfxDb.min} … ${L.sfxDb.max})` : '—'}`);
  log(`  sfx: ${(report.placedSfx ?? info.score.sfx.map((e) => `${e.type}@${e.t.toFixed(2)}`)).join(' ') || 'none'}`);
  log(`  cuts on the grid: ${info.scenes.slice(1).map((s) => s.start.toFixed(2)).join(' ')}`);
  if (report.unknownSfx) log(`  ⚠ unknown sfx types: ${report.unknownSfx.join(', ')}`);
}

async function voices(opts) {
  const lang = opts.lang ? String(opts.lang) : null;
  const cmd = has('uv') ? ['uv', ['run', '--quiet', '--no-project', '--with', 'edge-tts', 'edge-tts', '--list-voices']] : ['edge-tts', ['--list-voices']];
  const r = spawnSync(cmd[0], cmd[1], { encoding: 'utf8' });
  if (r.status !== 0) die(r.stderr || 'edge-tts failed');
  const lines = r.stdout.split('\n');
  log(lines.slice(0, 2).join('\n'));
  log(lines.slice(2).filter((l) => !lang || l.startsWith(lang)).join('\n'));
}

async function doctor() {
  let ok = true;
  const row = (good, name, detail) => { log(`  ${good ? '✔' : '✖'} ${name.padEnd(18)} ${detail}`); if (!good) ok = false; };
  const major = Number(process.versions.node.split('.')[0]);
  row(major >= 18, 'node', `v${process.versions.node}${major >= 18 ? '' : ' (need ≥ 18)'}`);
  const ff = spawnSync('ffmpeg', ['-hide_banner', '-encoders'], { encoding: 'utf8' });
  row(ff.status === 0 && /libx264/.test(ff.stdout), 'ffmpeg + libx264', ff.status === 0 ? (/libx264/.test(ff.stdout) ? 'ok' : 'ffmpeg found but libx264 missing') : 'not found — brew install ffmpeg / apt install ffmpeg');
  row(has('ffprobe'), 'ffprobe', has('ffprobe') ? 'ok' : 'not found (ships with ffmpeg)');
  let pw = null;
  try { pw = await import('playwright'); row(true, 'playwright', 'ok'); } catch { row(false, 'playwright', `not installed — cd ${ROOT} && npm install`); }
  if (pw) {
    try {
      const b = await pw.chromium.launch({ args: ['--allow-file-access-from-files'] });
      const v = b.version();
      await b.close();
      row(true, 'chromium', `headless ${v}`);
    } catch (e) {
      const msg = e.message.split('\n')[0];
      row(false, 'chromium', /EPERM|operation not permitted|sandbox/i.test(msg)
        ? `blocked by a sandbox: ${msg}\n${' '.repeat(23)}→ run doctor, still, render and tts with browser/filesystem permission`
        : `cannot launch: ${msg}\n${' '.repeat(23)}→ npx playwright install chromium`);
    }
  }
  const uv = has('uv');
  const py = spawnSync('python3', ['-c', 'import edge_tts;print(edge_tts.__version__)'], { encoding: 'utf8' });
  row(uv || py.status === 0, 'edge-tts', uv ? 'via uv (fetched on first use)' : py.status === 0 ? `python edge-tts ${py.stdout.trim()}` : 'install uv (recommended) or pip install edge-tts');
  // generated surfaces for three.js shots (not required: any image model will do)
  const codex = spawnSync('codex', ['--version'], { encoding: 'utf8' });
  log(`  ${'·'} ${'codex (optional)'.padEnd(18)} ${codex.status === 0 ? `${codex.stdout.trim()}: gaga texture --prompt generates surfaces` : 'not found: generate textures with any image model, then gaga texture <image>'}`);
  // the instrument samples for the score (downloaded once, 40 MB)
  const { loadSoundfont, SOUNDFONT } = await import('./soundfont.mjs');
  const sf = await loadSoundfont({ log });
  row(!sf.error, 'instrument samples', sf.error ? `${sf.error}\n${' '.repeat(23)}→ without them the score falls back to a much cheaper synth` : `${path.basename(sf.file)} (${SOUNDFONT.license})`);
  // the multi-sampled piano and strings: fetched per note on first use (not required)
  const { cacheReport } = await import('./samples.mjs');
  const cached = Object.entries(cacheReport()).map(([k, v]) => `${k} ${v.cached}/${v.total}`).join(' · ');
  log(`  ${'·'} ${'recorded piano/strings'.padEnd(18)} ${cached} cached (the rest download the first time a score plays them)`);
  log(ok ? '\nReady to render.' : '\nFix the ✖ items above, then re-run doctor.');
  process.exitCode = ok ? 0 : 1;
}

const HELP = `gaga (video-gaga) — Canvas motion graphics → MP4

doctor                        check node, ffmpeg, Playwright/Chromium, Edge TTS and the instrument samples

render <project|video.html>   render to MP4 (runs Edge TTS first if narration.json exists)
    --out <file.mp4>          default <project>/out/<name>.mp4
    --subs file|burn|soft|burn+soft|none   default file (.srt + .vtt next to the MP4)
    --music <file>            a licensed music track instead of the generated score (side-chain ducked)
    --music-volume <x>        default 1 for the generated score, 0.22 for a track
    --no-music                render without music and sound effects
    --motion-blur <n>         render n subframes per frame and blend (3–5 is plenty)
    --shutter 0.5             shutter angle as fraction of a frame (with --motion-blur)
    --scale 0.5               draft at half resolution (2 = 4K from a 1080p design)
    --from <s> --to <s>       render a time range only
    --workers <n>             parallel browser pages (default: min(6, cpus/2))
    --format png|jpeg         frame transfer format (png = lossless, jpeg = faster)
    --crf 18 --x264-preset medium
    --no-tts                  skip TTS even if narration.json exists
    --keep-temp
still <project>               export PNG probes (3 per scene) for review, and point at text cut off by
                              the frame edge, in the caption band, too small on a phone or low in
                              contrast; draws a few probes again in a fresh page to prove they repeat
    --at 1.2,3.4  --scenes a,b | a..c  --sheet [--rows 6]  --subs  --scale 0.5  --tts
    --phone                   probes and sheet at 390 px wide, the size a phone shows
moodboard <preview> <preview> …   the style directions side by side on one HTML page (motion
                              sample, frames, palette, type, music direction) for the user to pick
    --out <file.html>         default moodboard.html next to the previews
    --title "…"               type specimen text (the user's title)   --clip 6 (seconds)   --no-clip
    --open                    open it in the browser
    --wait                    serve it on localhost, open it, and wait for the click (prints the pick,
                              writes pick.json)  [--timeout 600 --port 0 --no-open]
tts <project>                 synthesize narration.json with Edge TTS (cached)
voicetrack <project> --audio <take>   one take: the whole narration recorded or synthesized in one pass;
                              aligns it to narration.json (Whisper), lengthens the pauses, cuts one
                              slice per scene and writes build/narration.js with the track, so the
                              scenes follow the take  [--cut id:0.4-0.8,… (drop a stray stretch of a
                              slice)  --clean (high-pass, de-noise, de-ess)  --model <whisper model>]
music <project>               render the generated score to build/music.wav (the preview player plays it)
check <video.mp4> [--srt f]   ffprobe summary + A/V + subtitle sanity checks, and a scan of the picture
                              (still stretches, one-frame glitches, blank frames, flashing)
                              (render runs it too, adding per-clip voice sync and telling reading
                              holds, where words on screen are being read, from dead ones)
gif <video.mp4>               palette GIF preview  [--out --width 480 --fps 12 --from --dur]
init <dir>                    scaffold a blank project: the render contract, no look [--ratio 9:16]
    --preset <slug>           start from a preset's style instead: its THEME and KIT helpers,
                              without the example's scenes, score or narration
voices [--lang zh-CN]         list Edge TTS voices
asset find <words…>           search Poly Haven (CC0) for ids  [--type hdris|textures|models --limit 12]
asset restore <project>       rebuild assets/ from assets/assets.json (render, still and moodboard do it
                              first): fetch from Poly Haven, derive maps from assets/src  [--force]
asset <project> polyhaven:<id>  a CC0 HDRI, PBR texture set or glTF model from Poly Haven into
                              <project>/assets (credited in assets/CREDITS.md, cached for every
                              project in ~/.cache/video-gaga/assets)  [--res 1k|2k|4k]
texture <project> --prompt "<surface>" --name <name>   generate the albedo with Codex CLI and derive
                              assets/<name>/ (the prompt goes into CREDITS.md); --matcap generates a lit
                              sphere instead → assets/<name>.png for MeshMatcapMaterial
texture <image>               an albedo image (generated or photographed) → a PBR folder: albedo,
                              normal, roughness and ao jpgs for gl.pbr()
    --out <dir>  --size 1024|source  --seamless (make it tile)  --delight (remove baked shading)
    --strength 2 (normal depth)  --rough 0.45,0.85 (high..low points)  --invert  --ao 1
    --neutral [0.82]          grey albedo with this mean, so material.color tints it (colourways)
    --only albedo,…           write only these maps (e.g. neutralise a scanned set's albedo in place)
`;

const opts = parseArgs(process.argv.slice(2));
const cmd = opts._[0];
// Standalone check: speech onsets can't be found on a track with music, so use
// the voice stem `gaga render` leaves in <project>/build when it belongs to this MP4.
async function checkCmd(o) {
  const file = path.resolve(o._[1] || die('missing file'));
  let stems = null;
  for (const b of [path.join(path.dirname(file), '..', 'build'), path.join(path.dirname(file), 'build')]) {
    const meta = path.join(b, 'voice-stem.json'), wav = path.join(b, 'voice-stem.wav');
    if (fs.existsSync(meta) && fs.existsSync(wav)) {
      const m = JSON.parse(fs.readFileSync(meta, 'utf8'));
      if (m.video === path.basename(file) && !m.from) stems = { voiceWav: wav };
      else if (m.music) stems = { noSync: true };
      break;
    }
  }
  const issues = await report(file, o.srt ? path.resolve(o.srt) : null, stems);
  process.exitCode = issues.length ? 2 : 0;
}

const main = { doctor, render, still, moodboard, music: musicCmd, tts: (o) => tts(resolveProject(o._[1]).dir), voicetrack, check: checkCmd, gif, init, voices,
  asset: (o) => assetCmd(o, { log, die, resolveProject }), texture: (o) => textureCmd(o, { log, die, resolveProject }) }[cmd];
if (!main) { log(HELP); process.exit(cmd && cmd !== 'help' ? 1 : 0); }
Promise.resolve(main(opts)).catch((e) => die(e.stack || e.message));
