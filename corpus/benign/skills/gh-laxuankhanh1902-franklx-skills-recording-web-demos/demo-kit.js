/*
 * demo-kit — record a scripted walk through any web UI as an mp4, with a visible cursor, click
 * ripples, captions drawn into the page, and the same captions written out as a transcript
 * (.srt, .vtt, .md) timed against the video.
 *
 * Copy this file next to your storyboard script; it requires `playwright` from the project.
 *
 *   const kit = require('./demo-kit');
 *   kit.run({ out: 'demo/out', name: 'my-demo' }, async d => {
 *     await d.card({ brand: 'Acme', title: 'Hello', lines: ['What this shows'] }, 5000);
 *     await d.goto('http://localhost:3000');
 *     await d.lead('Step 1 · Sign in', 'Type the demo user.');
 *     await d.type(d.page.getByLabel('Email'), 'demo@acme.test');
 *   });
 *
 * Playwright records WebM only; the mp4 needs an ffmpeg with libx264: `FFMPEG`, else
 * `ffmpeg-static`, else `ffmpeg` on the PATH. Without one the WebM is kept.
 */
const fs = require('fs');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const { chromium } = require('playwright');

const DEFAULTS = {
  out: 'demo-out',
  name: 'demo',
  width: 1440,
  height: 900,
  accent: '#9be15d',          // ripple, highlight, step label
  captionBg: 'rgba(9,32,29,.94)',
  cardBg: '#0a211e',
  trim: 0.5,                  // seconds cut off the start: the blank tab before the first page
  msPerChar: 58,              // reading time for say()
  minRead: 3000,
  embedSubtitles: false,      // also mux the .srt into the mp4 as a soft track
  headless: true,
  clickTargets: 'button, a, input, textarea, select, label, [role=button], [role=tab], [role=option], [role=menuitem]'
};

// ---------------------------------------------------------------- drawn into every page
function overlay(o) {
  return `
(() => {
  if (window.__demo) return;
  window.__demo = true;
  const css = \`
    #demo-cursor { position: fixed; left: 0; top: 0; width: 24px; height: 24px; z-index: 2147483647;
      pointer-events: none; transform: translate(-100px, -100px); opacity: 0; transition: opacity .2s; }
    #demo-cursor svg { filter: drop-shadow(0 1px 2px rgba(0,0,0,.45)); }
    .demo-ripple { position: fixed; z-index: 2147483646; pointer-events: none; width: 44px; height: 44px;
      margin: -22px 0 0 -22px; border-radius: 50%; border: 3px solid ${o.accent};
      animation: demo-ripple .55s ease-out forwards; }
    @keyframes demo-ripple { from { transform: scale(.3); opacity: 1; } to { transform: scale(1.4); opacity: 0; } }
    .demo-flash { outline: 3px solid ${o.accent} !important; outline-offset: 3px !important; }
    #demo-caption { position: fixed; left: 50%; bottom: 26px; transform: translate(-50%, 12px);
      z-index: 2147483645; pointer-events: none; width: min(1040px, calc(100vw - 80px));
      background: ${o.captionBg}; color: #f2f7f5; border-radius: 16px; padding: 16px 24px 18px;
      box-shadow: 0 12px 40px rgba(0,0,0,.35); text-align: left;
      font: 500 19px/1.45 -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
      opacity: 0; transition: opacity .35s, transform .35s; }
    #demo-caption.on { opacity: 1; transform: translate(-50%, 0); }
    #demo-caption .step { display: block; font: 700 12.5px/1 -apple-system, Arial, sans-serif;
      letter-spacing: .14em; text-transform: uppercase; color: ${o.accent}; margin-bottom: 8px; }
    #demo-caption code { font: 500 16px ui-monospace, "SF Mono", Menlo, monospace; }
  \`;
  const boot = () => {
    const style = document.createElement('style');
    style.textContent = css;
    document.documentElement.appendChild(style);
    const cur = document.createElement('div');
    cur.id = 'demo-cursor';
    cur.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24"><path d="M4 2 L4 19 L8.6 14.9 L11.6 21.6 L14.4 20.4 L11.4 13.8 L17.6 13.8 Z" fill="#fff" stroke="#10201d" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(cur);
    const cap = document.createElement('div');
    cap.id = 'demo-caption';
    document.documentElement.appendChild(cap);
    addEventListener('mousemove', e => {
      cur.style.opacity = '1';
      cur.style.transform = 'translate(' + (e.clientX - 3) + 'px,' + (e.clientY - 2) + 'px)';
    }, true);
    addEventListener('mousedown', e => {
      const r = document.createElement('div');
      r.className = 'demo-ripple';
      r.style.left = e.clientX + 'px';
      r.style.top = e.clientY + 'px';
      document.documentElement.appendChild(r);
      setTimeout(() => r.remove(), 700);
      const t = e.target.closest && e.target.closest(${JSON.stringify(o.clickTargets)});
      if (t) { t.classList.add('demo-flash'); setTimeout(() => t.classList.remove('demo-flash'), 650); }
    }, true);
  };
  if (document.documentElement) boot(); else addEventListener('DOMContentLoaded', boot);
  window.__caption = (step, html) => {
    const cap = document.getElementById('demo-caption');
    if (!cap) return;
    cap.classList.remove('on');
    if (!html) return;
    setTimeout(() => {
      cap.innerHTML = (step ? '<span class="step">' + step + '</span>' : '') + html;
      cap.classList.add('on');
    }, 180);
  };
})();`;
}

// ---------------------------------------------------------------- full-screen title / end cards
function cardUrl(o, c) {
  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const lines = (c.lines || []).map(l => '<p>' + l + '</p>').join('');
  const term = c.terminal
    ? '<div class="term">' + c.terminal.map(l => l.startsWith('$ ')
      ? '<div><span class="p">$</span> ' + esc(l.slice(2)) + '</div>'
      : '<div class="d">' + esc(l) + '</div>').join('') + '</div>'
    : '';
  const pills = c.pills ? '<div class="pills">' + c.pills.map(p => '<span class="pill">' + esc(p) + '</span>').join('') + '</div>' : '';
  return 'data:text/html;charset=utf-8,' + encodeURIComponent(`<!doctype html><html><head><style>
    html,body{margin:0;height:100%;background:${o.cardBg};color:#eef5f2;
      font-family:-apple-system,"SF Pro Display","Helvetica Neue",Arial,sans-serif}
    .wrap{height:100%;display:flex;flex-direction:column;justify-content:center;padding:0 140px;box-sizing:border-box}
    .brand{display:flex;align-items:center;gap:16px;color:${o.accent};font-weight:700;letter-spacing:.14em;text-transform:uppercase;font-size:15px;margin-bottom:26px}
    h1{font-size:${c.titleSize || 64}px;line-height:1.05;margin:0 0 22px;letter-spacing:-.02em}
    p{font-size:24px;line-height:1.5;margin:0 0 14px;color:#c4d6d0;max-width:1000px}
    .meta{margin-top:30px;font-size:17px;color:#8fb1a8}
    .term{margin:10px 0 24px;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.12);border-radius:14px;
      padding:26px 30px;font:500 19px/1.7 ui-monospace,"SF Mono",Menlo,monospace;color:#d6e6e1;max-width:1100px}
    .term .p{color:${o.accent}} .term .d{color:#8fa9a2}
    .pills{display:flex;gap:12px;margin-top:30px;flex-wrap:wrap}
    .pill{border:1px solid rgba(255,255,255,.25);border-radius:999px;padding:9px 18px;font-size:18px}
  </style></head><body><div class="wrap">
    ${c.brand ? '<div class="brand">' + c.brand + '</div>' : ''}
    ${c.title ? '<h1>' + c.title + '</h1>' : ''}${term}${lines}${pills}
    ${c.meta ? '<div class="meta">' + c.meta + '</div>' : ''}
  </div></body></html>`);
}

// ---------------------------------------------------------------- transcript
const plain = html => html.replace(/<br\s*\/?>/gi, ' ').replace(/<[^>]+>/g, '')
  .replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&')
  .replace(/\s+/g, ' ').trim();
function stamp(sec, sep) {
  const ms = Math.max(0, Math.round(sec * 1000));
  const p = (n, w) => String(n).padStart(w, '0');
  return p(Math.floor(ms / 3600000), 2) + ':' + p(Math.floor(ms / 60000) % 60, 2) + ':'
    + p(Math.floor(ms / 1000) % 60, 2) + sep + p(ms % 1000, 3);
}
function writeTranscript(cues, base, title) {
  const text = c => (c.step ? c.step + ' — ' : '') + c.text;
  fs.writeFileSync(base + '.srt', cues.map((c, i) =>
    (i + 1) + '\n' + stamp(c.start, ',') + ' --> ' + stamp(c.end, ',') + '\n' + text(c) + '\n').join('\n'));
  fs.writeFileSync(base + '.vtt', 'WEBVTT\n\n' + cues.map(c =>
    stamp(c.start, '.') + ' --> ' + stamp(c.end, '.') + '\n' + text(c) + '\n').join('\n'));
  fs.writeFileSync(base + '.md', '# ' + title + '\n\n' + cues.map(c =>
    '- **' + stamp(c.start, '.').slice(3, 8) + '** ' + (c.step ? '**' + c.step + '** — ' : '') + c.text).join('\n') + '\n');
}

// ---------------------------------------------------------------- ffmpeg
function findFfmpeg() {
  const candidates = [process.env.FFMPEG];
  try { candidates.push(require('ffmpeg-static')); } catch (e) { /* not installed */ }
  candidates.push('ffmpeg');
  return candidates.filter(Boolean).find(bin => {
    const r = spawnSync(bin, ['-hide_banner', '-encoders'], { encoding: 'utf8' });
    return r.status === 0 && /libx264/.test(r.stdout);
  }) || null;
}

// ---------------------------------------------------------------- a server the demo needs
/**
 * Starts a command and resolves once a line it prints matches `ready`; answers the child, the
 * match and everything printed. The child is stopped when the recording ends.
 */
function startServer(cmd, args, ready, opts) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, Object.assign({ stdio: ['ignore', 'pipe', 'pipe'] }, opts));
    let out = '';
    const timer = setTimeout(() => { child.kill(); reject(new Error(cmd + ' printed nothing matching ' + ready)); },
      (opts && opts.timeout) || 60000);
    const read = chunk => {
      out += chunk;
      const m = out.match(ready);
      if (m) { clearTimeout(timer); resolve({ child, match: m, printed: out }); }
    };
    child.stdout.on('data', read);
    child.stderr.on('data', read);
    child.on('exit', code => { clearTimeout(timer); reject(new Error(cmd + ' exited ' + code + '\n' + out)); });
  });
}

// ---------------------------------------------------------------- the recorder
async function run(options, storyboard) {
  const o = Object.assign({}, DEFAULTS, options);
  const out = path.resolve(o.out);
  const raw = path.join(out, 'video-raw');
  const base = path.join(out, o.name);
  fs.mkdirSync(out, { recursive: true });
  fs.rmSync(raw, { recursive: true, force: true });

  const browser = await chromium.launch({ headless: o.headless });
  const ctx = await browser.newContext({
    viewport: { width: o.width, height: o.height },
    recordVideo: { dir: raw, size: { width: o.width, height: o.height } },
    bypassCSP: true,           // a strict Content-Security-Policy would block the overlay's <style>
    ...(o.context || {})
  });
  await ctx.addInitScript(overlay(o));
  const page = await ctx.newPage();
  const t0 = Date.now();                      // the video's first frame, near enough
  const now = () => (Date.now() - t0) / 1000 - o.trim;
  const cues = [];
  const thrown = [];
  const cleanup = [];
  page.on('pageerror', e => thrown.push(e.message));
  let mouse = { x: o.width / 2, y: o.height / 2 };

  const closeCue = () => { const c = cues[cues.length - 1]; if (c && c.end == null) c.end = now(); };
  async function caption(step, html) {
    closeCue();
    await page.evaluate(([s, h]) => window.__caption && window.__caption(s, h), [step || null, html || null]);
    if (html) cues.push({ step: step || '', text: plain(html), start: now() + 0.18, end: null });
  }
  const wait = ms => page.waitForTimeout(ms);

  async function moveTo(locator, opts) {
    await locator.scrollIntoViewIfNeeded();
    const box = await locator.boundingBox();
    if (!box) throw new Error('no box for ' + locator);
    const x = box.x + Math.min(box.width / 2, (opts && opts.dx) || box.width / 2);
    const y = box.y + box.height / 2;
    const dist = Math.hypot(x - mouse.x, y - mouse.y);
    await page.mouse.move(x, y, { steps: Math.max(12, Math.round(dist / 18)) });
    mouse = { x, y };
    await wait(220);
  }

  const d = {
    page, ctx, options: o, wait, moveTo,
    /** Caption up, then the time it takes to read it. */
    async say(step, html, extra) {
      console.log('say  ' + (step || plain(html).slice(0, 60)));
      await caption(step, html);
      await wait(Math.max(o.minRead, plain(html).length * o.msPerChar) + (extra || 0));
    },
    /** Caption up, a beat, and the action follows while it is read. */
    async lead(step, html, ms) {
      console.log('lead ' + (step || plain(html).slice(0, 60)));
      await caption(step, html);
      await wait(ms == null ? 1600 : ms);
    },
    async clear() { await caption(null, null); await wait(400); },
    async goto(url, waitFor) {
      await page.goto(url);
      if (waitFor) await page.waitForSelector(waitFor, { timeout: 30000 });
      await wait(600);
    },
    async card(c, ms) { closeCue(); await page.goto(cardUrl(o, c)); await wait(ms || 6000); },
    async click(locator, opts) {
      await moveTo(locator.first ? locator.first() : locator, opts);
      await page.mouse.down(); await wait(70); await page.mouse.up();
      await wait(450);
    },
    async type(locator, text, delay) {
      await d.click(locator);
      await page.keyboard.type(text, { delay: delay || 55 });
      await wait(350);
    },
    /** A hover that only decorates: a missing element is logged and skipped, never fatal. */
    async point(locator, opts) {
      try {
        await locator.first().scrollIntoViewIfNeeded({ timeout: 4000 });
        await moveTo(locator.first(), opts);
      } catch (e) {
        console.log('     (skipped a hover: ' + e.message.split('\n')[0].slice(0, 80) + ')');
      }
    },
    async scroll(dy, ms) {
      const steps = Math.max(10, Math.round((ms || 900) / 16));
      for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await wait(16); }
      await wait(350);
    },
    async scrollTop() {
      await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
      await wait(700);
    },
    /** Text of the page with whitespace collapsed — for captions that quote live figures. */
    async text() { return (await page.locator('body').innerText()).replace(/\s+/g, ' '); },
    async server(cmd, args, ready, opts) {
      const s = await startServer(cmd, args, ready, opts);
      cleanup.push(() => s.child.kill());
      return s;
    }
  };

  let failed = null;
  try {
    await storyboard(d);
  } catch (e) {
    failed = e;
    await page.screenshot({ path: base + '.failure.png' }).catch(() => {});
  } finally {
    closeCue();
    const video = page.video();
    await ctx.close();
    await browser.close();
    cleanup.forEach(f => f());
    const total = (Date.now() - t0) / 1000 - o.trim;
    cues.forEach(c => { c.end = Math.min(c.end, total); });
    writeTranscript(cues.filter(c => c.end > c.start), base, o.title || o.name);

    const webm = video ? await video.path() : null;
    const bin = findFfmpeg();
    if (webm && bin) {
      const args = ['-hide_banner', '-loglevel', 'error', '-y', '-ss', String(o.trim), '-i', webm];
      if (o.embedSubtitles) args.push('-i', base + '.srt', '-map', '0:v', '-map', '1:s', '-c:s', 'mov_text');
      args.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '25',
        '-movflags', '+faststart', '-an', base + '.mp4');
      const r = spawnSync(bin, args, { stdio: 'inherit' });
      console.log(r.status === 0 ? 'video: ' + base + '.mp4' : 'ffmpeg failed; the recording is ' + webm);
    } else {
      console.log('video: ' + webm + (webm ? '  (no ffmpeg with libx264 for the mp4)' : ''));
    }
    console.log('transcript: ' + base + '.srt / .vtt / .md (' + cues.length + ' captions)');
    console.log('page errors: ' + thrown.length + (thrown.length ? '\n  ' + thrown.join('\n  ') : ''));
  }
  if (failed) {
    console.error('ERR ' + failed.message.split('\n')[0] + '  (last frame: ' + base + '.failure.png)');
    process.exitCode = 2;
  }
}

module.exports = { run, startServer, findFfmpeg };
