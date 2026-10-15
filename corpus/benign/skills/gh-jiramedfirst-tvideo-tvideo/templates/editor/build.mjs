// TVideo editor: build a Hyperframes composition (index.html) for one tutorial clip.
//
//   node build.mjs            # reads tvideo.config.json + plan.json + timeline.json [+ clicks.json, voices.json]
//
// Each step plays its source range of the screen recording, then holds a still
// until the longest of: the action, the narration line (voices.json, optional),
// or the time to read the caption. Source ranges and click times come straight
// from the recorder (timeline.json, clicks.json), so a re-record only needs a
// re-run of this script. Every optional asset degrades gracefully: no logo →
// text-only cards; no assets/sfx → silent clicks; no music → no bed; no voices →
// caption-paced.
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const readJson = (f, fallback) => (existsSync(f) ? JSON.parse(readFileSync(f, 'utf8')) : fallback);
const cfg = readJson('tvideo.config.json', null);
if (!cfg) throw new Error('tvideo.config.json missing — copy tvideo.config.example.json and edit it.');
const plan = readJson('plan.json', null);
if (!plan) throw new Error('plan.json missing — copy plan.example.json and edit it.');
const timeline = readJson('timeline.json', null);
if (!timeline) throw new Error('timeline.json missing — import the recording first (scripts/new-clip.mjs or import.mjs).');
if (timeline.length !== plan.steps.length) {
  throw new Error(`plan.json has ${plan.steps.length} steps but timeline.json has ${timeline.length} — they must match 1:1, in order.`);
}
const voices = readJson('voices.json', {});
// clicks.json: v1 recorders wrote bare ms numbers; v1.1 writes {ms, box, gone}.
const clicks = readJson('clicks.json', []).map((c) => (typeof c === 'number' ? { t: c / 1000 } : { ...c, t: c.ms / 1000 }));

const probe = (file, entries) =>
  execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', entries, '-of', 'csv=p=0', file], { encoding: 'utf8' }).trim();
const footageEnd = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', plan.footage], { encoding: 'utf8' }));
const [SRC_W, SRC_H] = probe(plan.footage, 'stream=width,height').split(',').map(Number);

// Canvas 1920x1080; the footage is fitted (never cropped) into a 1440x900 stage
// so app chrome stays visible and the caption band below stays clear.
const fit = Math.min(1440 / SRC_W, 900 / SRC_H);
const K = fit;
const STAGE = { w: Math.round(SRC_W * fit), h: Math.round(SRC_H * fit) };
STAGE.x = Math.round((1920 - STAGE.w) / 2);
STAGE.y = 30;
const CAP_TOP = STAGE.y + STAGE.h + 16;

const INTRO_MIN = 3.5, OUTRO_MIN = 4.5;
const RING_MIN_HOLD = 2.4;   // a ringed control needs a still long enough to find it
const VOICE_LEAD = 0.15, BREATH = 0.5;
const CPS = cfg.readingCharsPerSec ?? 12;
// ponytail: chars/sec + 1 s to notice the caption changed; tune readingCharsPerSec per language.
const readDur = (text) => text.replace(/\s/g, '').length / CPS + 1;
const voiceDur = (id) => voices[id]?.duration ?? 0;
const r = (n) => Math.round(n * 1000) / 1000;
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');

mkdirSync('assets/holds', { recursive: true });
function holdFrame(id, t) {
  // Keyed on the time too: flipping holdFirst moves the sample point, and a
  // cache keyed on the id alone would keep serving the other moment's frame.
  const out = `assets/holds/${id}-${t.toFixed(2)}.png`;
  if (!existsSync(out)) {
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-ss', String(Math.max(0, t - 0.05)), '-i', plan.footage, '-frames:v', '1', out]);
  }
  return out;
}

const media = [], overlays = [], tweens = [], audios = [];
let aid = 0;
// Every <audio> carries its real length: an open-ended one counts as playing to the
// end of the composition, so every SFX would "overlap" every later one.
const probed = new Map();
const lengthOf = (src) => {
  if (!probed.has(src)) probed.set(src, Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], { encoding: 'utf8' })));
  return probed.get(src);
};
const sfx = (name) => (cfg.sfx === false ? null : existsSync(`assets/sfx/${name}.mp3`) ? `assets/sfx/${name}.mp3` : null);
const sound = (src, at, vol, track = 6, dur) => {
  if (!src) return;
  audios.push(`<audio id="a${++aid}" src="${src}" data-start="${r(at)}" data-duration="${r(dur ?? lengthOf(src))}" data-track-index="${track}" data-volume="${vol}"></audio>`);
};
const voice = (id, at) => voices[id] && sound(voices[id].path, at, 1, 3, voices[id].duration);

let T = 0;
const introDur = Math.max(INTRO_MIN, 0.4 + voiceDur('intro') + BREATH);
sound(sfx('whoosh-short'), 0.15, 0.35);
voice('intro', 0.4);
T = introDur;

const steps = plan.steps.map((s, i) => {
  const a0 = timeline[i].startMs / 1000;
  // The recording runs a little past the last step; never ask for frames past EOF.
  const b = Math.min(timeline[i].endMs / 1000, footageEnd - 0.1);
  if (b - a0 <= 0.05) {
    throw new Error(`step ${s.id}: its source range ${a0.toFixed(2)}–${(timeline[i].endMs / 1000).toFixed(2)} s is past the end of the footage (${footageEnd.toFixed(2)} s) — re-import the recording that wrote this timeline.json.`);
  }
  // `zoom: true` is shorthand for "zoom on, and ring the step's first click".
  const z = s.zoom === true ? { ring: true } : s.zoom;
  // ring: true / N → the box of the step's first / Nth tap, as the recorder saw
  // it — no pixel measuring, and it follows the control when the layout moves.
  const stepClicks = clicks.filter((c) => c.t >= a0 && c.t < b);
  const ringClick = typeof z?.ring === 'number' || z?.ring === true ? stepClicks[(z.ring === true ? 1 : z.ring) - 1] : null;
  if (ringClick && !ringClick.box) throw new Error(`step ${s.id}: ring: ${z.ring} but that click has no box (clicks.json from a v1 recorder, or a rehearsal take) — re-record, or give ring {x,y,w,h}.`);
  if ((z?.ring === true || typeof z?.ring === 'number') && !ringClick) throw new Error(`step ${s.id}: ring: ${z.ring} but the step has only ${stepClicks.length} tap(s).`);
  const ring = ringClick ? ringClick.box : z?.ring || null;
  // holdFirst: the step's subject is a control that vanishes once clicked (a
  // button that navigates away), so show the frame BEFORE the click first, then
  // play the action. Default: play the action, then hold its end state. Unset →
  // the recorder knows: a ringed control that disappeared after its click.
  const holdFirst = s.holdFirst ?? Boolean(ringClick?.gone);
  // holdFirst starts the action at the ringed click (just after the cursor
  // arrived), not at the step start: any scroll/glide before it would otherwise
  // play after a still that already shows the scrolled page — a visible jump back.
  const anchor = ringClick ?? stepClicks[0];
  const a = holdFirst && anchor ? Math.max(a0, anchor.t - 0.15) : a0;
  const seg = b - a;
  const minHold = ring ? RING_MIN_HOLD : 0.2;
  const dur = Math.max(seg + minHold, readDur(s.caption), VOICE_LEAD + voiceDur(s.id) + BREATH);
  const start = T;
  const hold = dur - seg;
  const vStart = holdFirst ? start + hold : start;
  const hStart = holdFirst ? start : start + seg;
  media.push(`<video id="v-${s.id}" class="clip shot" src="${plan.footage}" muted playsinline data-start="${r(vStart)}" data-duration="${r(seg)}" data-media-start="${r(a)}" data-track-index="0"></video>`);
  if (hold > 0.04) {
    // holdFirst: the frame the action starts from (no click data → just before
    // the step). Otherwise `b - 0.2`, the settled result.
    const still = holdFirst ? (a > a0 ? a : Math.max(0, a0 - 0.35)) : b - 0.2;
    media.push(`<img id="h-${s.id}" class="clip shot" src="${holdFrame(s.id, still)}" data-start="${r(hStart)}" data-duration="${r(hold)}" data-track-index="0" alt="" />`);
  }
  voice(s.id, start + VOICE_LEAD);
  // A click sound on every recorded press inside this step, mapped from source
  // time onto where that range plays in the composition.
  for (const c of stepClicks) if (c.t >= a) sound(sfx('click-soft'), vStart + (c.t - a), 0.5);
  if (z) {
    // The zoom origin is the one point that stays put while everything scales away
    // from it — so it belongs ON the control (defaults to the ring centre). Any
    // other point P lands at O + (P − O) × scale, which pushes an off-origin
    // control toward the frame edge and can crop it.
    const zx = z.x ?? ring?.x ?? SRC_W / 2, zy = z.y ?? ring?.y ?? SRC_H / 2;
    tweens.push(`tl.set('#zoom', { transformOrigin: '${r((zx / SRC_W) * 100)}% ${r((zy / SRC_H) * 100)}%' }, ${r(start)});`);
    tweens.push(`tl.to('#zoom', { scale: ${z.scale ?? 1.5}, duration: 0.7, ease: 'power2.inOut' }, ${r(start + (z.at ?? 0.3))});`);
    // holdFirst: zoom back out as the click plays — the page changes under it, and
    // staying zoomed would frame an empty corner of the next screen.
    const zoomOut = holdFirst ? Math.max(start + (z.at ?? 0.3) + 0.8, start + hold - 0.5) : start + dur - 0.6;
    tweens.push(`tl.to('#zoom', { scale: 1, duration: 0.6, ease: 'power2.inOut' }, ${r(zoomOut)});`);
    if (ring) {
      // Accent ring on the control to press; inside #zoom so it scales with the
      // footage. Only over the HOLD still — once the click plays, the page
      // changes under it and the ring would mark nothing.
      const g = ring, pad = 6;
      const rs = holdFirst ? start + (z.at ?? 0.3) + 0.4 : start + seg;
      const re = holdFirst ? start + hold : start + dur - 0.6;
      overlays.push(`<div id="ring-${s.id}" class="clip ring" data-start="${r(rs)}" data-duration="${r(re - rs)}" data-track-index="1" style="left:${r((g.x - g.w / 2 - pad) * K)}px;top:${r((g.y - g.h / 2 - pad) * K)}px;width:${r((g.w + pad * 2) * K)}px;height:${r((g.h + pad * 2) * K)}px"><div class="ring-inner"></div></div>`);
      tweens.push(`tl.fromTo('#ring-${s.id} .ring-inner', { opacity: 0, scale: 1.25 }, { opacity: 1, scale: 1, duration: 0.35, ease: 'power2.out' }, ${r(rs)});`);
      tweens.push(`tl.to('#ring-${s.id} .ring-inner', { scale: 1.08, duration: 0.45, ease: 'sine.inOut', yoyo: true, repeat: ${Math.max(1, Math.floor((re - rs - 0.35) / 0.45) - 1)} }, ${r(rs + 0.35)});`);
    }
  }
  if (s.mask) {
    // Cover on-screen text that must not ship (test ids, real names) with a
    // look-alike box. `after`: seconds into the step's source range when it appears.
    const m = s.mask;
    const from = (holdFirst ? start + hold : start) + (m.after ?? 0);
    overlays.push(`<div id="mask-${s.id}" class="clip mask" data-start="${r(from)}" data-duration="${r(start + dur - from)}" data-track-index="1" style="left:${r(m.x * K)}px;top:${r(m.y * K)}px;width:${r(m.w * K)}px;height:${r(m.h * K)}px;font-size:${r((m.fontSize ?? 15) * K)}px;justify-content:${m.align === 'left' ? 'flex-start' : 'flex-end'};background:${m.bg ?? '#fff'};color:${m.color ?? '#141414'}"><span>${esc(m.text)}</span></div>`);
  }
  // Own track: the chime rings ~2.5 s, so on the last step it runs into the outro
  // whoosh — a deliberate layer, not the overlap the click track must avoid.
  if (s.chimeAfter !== undefined) sound(sfx('chime'), (holdFirst ? start + hold : start) + s.chimeAfter, 0.45, 7);
  T += dur;
  return { ...s, holdFirst, ring, start, dur, n: i + 1, srcA: a, srcB: b, vStart, hStart, hold };
});

const outroStart = T;
const outroDur = Math.max(OUTRO_MIN, 0.3 + voiceDur('outro') + BREATH + 0.5);
sound(sfx('whoosh-short'), outroStart - 0.1, 0.35);
sound(sfx('sparkle'), outroStart + 0.5, 0.35); // after the whoosh ends — no overlap
voice('outro', outroStart + 0.3);
const total = outroStart + outroDur;

const music = cfg.music && existsSync(cfg.music.src) ? cfg.music : null;
if (music) {
  const v = music.volume ?? 0.22;
  audios.push(`<audio id="music-bed" src="${music.src}" data-start="0" data-duration="${r(total)}" data-track-index="5" data-volume="1" data-automation='${JSON.stringify({ version: 1, lanes: [{ target: 'volume', points: [{ t: 0, v: 0 }, { t: 1.5, v }, { t: r(total - 2.5), v }, { t: r(total), v: 0 }] }] })}'></audio>`);
}

const N = steps.length;
// The caption band is whatever the stage leaves below it: 120 px for 16:10
// footage, more for wider. A long caption wraps to two lines and would overflow
// at 40 px, so shrink it until the estimated lines fit.
// ponytail: width estimate is 0.55 em per character (Latin/Thai average); CJK
// runs ~1 em and may still wrap — keep captions short there, or measure in-page.
const CAP_BAND = 1080 - CAP_TOP - 14, CAP_TEXT_W = 1600;
const capSize = (text) => {
  let fs = 40;
  const lines = () => Math.ceil((text.length * 0.55 * fs) / CAP_TEXT_W);
  while (fs > 24 && lines() * fs * 1.25 + 34 > CAP_BAND) fs -= 2;
  return fs;
};
const captions = steps.map((s) => `
      <div id="cap-${s.id}" class="clip cap" data-start="${r(s.start)}" data-duration="${r(s.dur)}" data-track-index="2">
        <div class="cap-inner"><span class="badge">${s.n}/${N}</span><span class="cap-text" style="font-size:${capSize(s.caption)}px">${esc(s.caption)}</span></div>
      </div>`).join('');
for (const s of steps) {
  tweens.push(`tl.fromTo('#cap-${s.id} .cap-inner', { y: 18, opacity: 0 }, { y: 0, opacity: 1, duration: 0.4, ease: 'power3.out' }, ${r(s.start + 0.05)});`);
}

const b = cfg.brand ?? {};
const brand = {
  bg: b.bg ?? '#0f172a', bg2: b.bg2 ?? '#1e293b', glow: b.glow ?? '#334155', accent: b.accent ?? '#22c55e',
  onAccent: b.onAccent ?? '#052e16', ink: b.ink ?? '#f8fafc', capBg: b.captionBg ?? 'rgba(2,6,23,0.82)',
};
const font = cfg.font ?? {};
const family = font.family ?? 'TVideo Sans';
const faces = Object.entries(font.files ?? {})
  .map(([w, f]) => `@font-face { font-family: '${family}'; src: url('${f}'); font-weight: ${w}; }`).join('\n      ');
const logo = cfg.logo && existsSync(cfg.logo) ? cfg.logo : null;
const logoImg = (cls) => (logo ? `<img class="${cls}" src="${logo}" alt="${esc(cfg.logoAlt ?? '')}" />` : '');

const html = `<!doctype html>
<html lang="${esc(cfg.lang ?? 'en')}">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <title>${esc(plan.title)}</title>
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      ${faces}
      :root { --bg: ${brand.bg}; --bg2: ${brand.bg2}; --glow: ${brand.glow}; --accent: ${brand.accent}; --on-accent: ${brand.onAccent}; --ink: ${brand.ink}; --cap-bg: ${brand.capBg}; }
      body { margin: 0; background: var(--bg); font-family: '${family}', sans-serif; color: var(--ink); }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; }
      .bg { position: absolute; inset: 0; background: radial-gradient(1200px 700px at 78% 18%, var(--glow) 0%, var(--bg2) 40%, var(--bg) 100%); }
      .glow { position: absolute; width: 900px; height: 900px; left: -260px; top: 420px; border-radius: 50%;
              background: radial-gradient(circle, color-mix(in srgb, var(--accent) 16%, transparent) 0%, transparent 65%); }
      .stage { position: absolute; left: ${STAGE.x}px; top: ${STAGE.y}px; width: ${STAGE.w}px; height: ${STAGE.h}px;
               border-radius: 18px; overflow: hidden; background: #fff;
               box-shadow: 0 30px 80px rgba(0,0,0,0.45), 0 0 0 1px rgba(255,255,255,0.08); }
      #zoom { position: absolute; inset: 0; }
      .shot { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
      .mask { position: absolute; display: flex; align-items: center; font-weight: 600; padding: 0 2px; box-sizing: border-box; }
      .ring { position: absolute; }
      .ring-inner { position: absolute; inset: 0; border: 4px solid var(--accent); border-radius: 12px;
                    box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 25%, transparent), 0 0 24px color-mix(in srgb, var(--accent) 60%, transparent); }
      .corner-logo { position: absolute; left: 30px; top: 34px; width: ${Math.max(120, STAGE.x - 60)}px; max-width: 200px; }
      .cap { position: absolute; left: 0; right: 0; top: ${CAP_TOP}px; height: ${1080 - CAP_TOP - 14}px; display: flex; justify-content: center; align-items: center; }
      .cap-inner { display: flex; align-items: center; gap: 22px; padding: 16px 34px 18px 18px; border-radius: 999px;
                   background: var(--cap-bg); box-shadow: 0 10px 30px rgba(0,0,0,0.35); max-width: 1760px; }
      .badge { min-width: 76px; height: 54px; padding: 0 14px; box-sizing: border-box; border-radius: 999px; background: var(--accent);
               color: var(--on-accent); font-weight: 700; font-size: 28px; display: flex; align-items: center; justify-content: center; flex: none; }
      .cap-text { font-size: 40px; font-weight: 600; line-height: 1.25; }
      .card { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 0 120px; box-sizing: border-box; }
      .card .logo { width: 420px; padding: 26px 40px; background: #fff; border-radius: 24px; box-sizing: content-box; margin-bottom: 56px; }
      .card h1 { margin: 0; font-size: 92px; font-weight: 700; line-height: 1.2; }
      .card .credit { position: absolute; bottom: 36px; font-size: 20px; color: color-mix(in srgb, var(--ink) 60%, transparent); }
      .card .sub { margin-top: 22px; font-size: 36px; font-weight: 400; color: color-mix(in srgb, var(--ink) 82%, transparent); }
      .card .rule { margin-top: 40px; width: 140px; height: 6px; border-radius: 3px; background: var(--accent); }
      .card .check { width: 140px; height: 140px; border-radius: 50%; background: var(--accent); display: flex; align-items: center; justify-content: center; margin-bottom: 40px; }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="${r(total)}">
      <div class="bg"></div>
      <div id="glow" class="glow"></div>

      <section id="intro" class="clip card" data-start="0" data-duration="${r(introDur)}" data-track-index="4">
        ${logoImg('logo')}
        <h1 id="intro-title">${esc(plan.title)}</h1>
        <div id="intro-sub" class="sub">${esc(plan.subtitle ?? '')}</div>
        <div id="intro-rule" class="rule"></div>
      </section>

      <div id="stage-wrap" style="position:absolute;inset:0;opacity:0">
        ${logoImg('corner-logo')}
        <div id="stage" class="stage">
          <div id="zoom">
            ${media.join('\n            ')}
            ${overlays.join('\n            ')}
          </div>
        </div>
      </div>
${captions}

      <section id="outro" class="clip card" data-start="${r(outroStart)}" data-duration="${r(outroDur)}" data-track-index="4">
        <div id="outro-check" class="check"><svg viewBox="0 0 24 24" width="78" height="78" fill="none" stroke="currentColor" style="color:var(--on-accent)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></div>
        <h1 id="outro-title">${esc(plan.outro?.title ?? '')}</h1>
        <div id="outro-line" class="sub">${esc(plan.outro?.line ?? '')}</div>
        ${music?.credit ? `<div class="credit">${esc(music.credit)}</div>` : ''}
        <div id="outro-rule" class="rule"></div>
      </section>
      ${audios.join('\n      ')}
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      tl.fromTo('#glow', { scale: 1 }, { scale: 1.15, duration: ${r(total / 2)}, ease: 'sine.inOut', yoyo: true, repeat: 1 }, 0);
      ${logo ? "tl.fromTo('#intro .logo', { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }, 0.2);" : ''}
      tl.fromTo('#intro-title', { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }, 0.45);
      tl.fromTo('#intro-sub', { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: 'power2.out' }, 0.7);
      tl.fromTo('#intro-rule', { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: 'power2.out' }, 0.9);
      // stage-wrap is untimed (its videos carry the timing; a timed wrapper around
      // timed <video> breaks frame extraction), so its visibility is opacity-driven.
      tl.set('#stage-wrap', { opacity: 1 }, ${r(introDur)});
      tl.fromTo('#stage', { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }, ${r(introDur)});
      tl.to('#stage-wrap', { opacity: 0, duration: 0.4, ease: 'power2.in' }, ${r(outroStart - 0.4)});
      ${tweens.join('\n      ')}
      tl.fromTo('#outro-check', { scale: 0.4, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(1.8)' }, ${r(outroStart + 0.15)});
      tl.fromTo('#outro-title', { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.6, ease: 'power3.out' }, ${r(outroStart + 0.35)});
      tl.fromTo('#outro-line', { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.5, ease: 'power2.out' }, ${r(outroStart + 0.6)});
      tl.fromTo('#outro-rule', { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: 'power2.out' }, ${r(outroStart + 0.8)});
      window.__timelines['main'] = tl;
    </script>
  </body>
</html>
`;
writeFileSync('index.html', html);

// Sidecar subtitles on the output timeline: upload next to the mp4 (YouTube, LMS)
// so captions are selectable text for screen readers and translation.
const stamp = (t, sep) => {
  const ms = Math.round(t * 1000), p = (n, w = 2) => String(n).padStart(w, '0');
  return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)}${sep}${p(ms % 1000, 3)}`;
};
// One line per cue: a blank line or "-->" inside a caption would end/corrupt it.
const cue = (s, sep) => `${stamp(s.start, sep)} --> ${stamp(s.start + s.dur, sep)}\n${s.caption.replace(/\s+/g, ' ').replace(/-->/g, '→')}\n`;
writeFileSync('captions.srt', steps.map((s, i) => `${i + 1}\n${cue(s, ',')}`).join('\n'));
writeFileSync('captions.vtt', `WEBVTT\n\n${steps.map((s) => cue(s, '.')).join('\n')}`);
console.log(`built index.html — ${N} steps, ${r(total)}s${Object.keys(voices).length ? ', with narration' : ''}${music ? ', with music' : ''}`);
// Output times ≠ recording times (the intro and holds shift everything): print
// where each step lands so snapshots can be aimed (`hyperframes snapshot --at`).
console.log(`  intro      0.00–${introDur.toFixed(2)}`);
for (const s of steps) {
  const still = s.hold > 0.04 ? `still ${(s.holdFirst ? s.start : s.vStart + (s.srcB - s.srcA)).toFixed(2)}+${s.hold.toFixed(2)}` : '';
  console.log(`  ${s.id}  ${s.start.toFixed(2)}–${(s.start + s.dur).toFixed(2)}  (src ${s.srcA.toFixed(2)}–${s.srcB.toFixed(2)}) ${still}${s.holdFirst ? ' holdFirst' : ''}${s.zoom ? ' zoom' : ''}${s.ring ? '+ring' : ''}${s.mask ? ' mask' : ''}`);
}
console.log(`  outro      ${outroStart.toFixed(2)}–${total.toFixed(2)}`);

// Narration over a music bed: carve the bed so the voice sits clear. Needs the
// Hyperframes audio skill's carve.mjs and @hyperframes/core in this project.
if (music && Object.keys(voices).length) {
  const carve = [join(homedir(), '.claude/skills/hyperframes-audio/scripts/carve.mjs'), join(homedir(), '.agents/skills/hyperframes-audio/scripts/carve.mjs')].find(existsSync);
  if (!carve) console.warn('! narration + music but no carve.mjs found — run `npx hyperframes skills update hyperframes-audio`, then rebuild.');
  else {
    try {
      execFileSync('node', [carve, '--comp', 'index.html', '--bed', 'music-bed'], { stdio: 'inherit' });
    } catch {
      console.warn('! carve failed — `npm i -D @hyperframes/core` in this project, then rebuild.');
    }
  }
}
