'use strict';
// Fatima Voice Studio: the whole UI. Plain JS, no build step.

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const plural = (n, word, many) => `${n} ${n === 1 ? word : (many || word + 's')}`;
const S = { state: null, voices: [], settings: null, batches: [], detail: null, view: null, scripts: [], smode: 'list', cmode: 'single' };

// ---------- icons (inline SVG, follow the text colour) ----------
const ICONS = {
  mark: '<path d="M4 10v4M8 7v10M12 4v16M16 8v8M20 11v2"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6 6 0 0 1 3.5 5.5"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  plug: '<path d="M9 2v6M15 2v6M6 8h12v3a6 6 0 0 1-12 0V8ZM12 17v5"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  drive: '<rect x="2" y="13" width="20" height="8" rx="2"/><path d="M5 13 7.5 4h9L19 13M6 17h.01M10 17h.01"/>',
  upload: '<path d="M12 15V3M7 8l5-5 5 5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  play: '<path d="M7 4.5v15l12-7.5-12-7.5Z"/>',
  wave: '<path d="M2 12h2M6 8v8M10 5v14M14 9v6M18 7v10M22 12h0"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  folder: '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z"/>',
  pencil: '<path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4M21 4v5h-5"/>',
  sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
  up: '<path d="m6 15 6-6 6 6"/>', down: '<path d="m6 9 6 6 6-6"/>',
  pause: '<path d="M8 5v14M16 5v14"/>', stop: '<rect x="6" y="6" width="12" height="12" rx="1"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M5 7l1 13h12l1-13M9 7V4h6v3"/>',
  check: '<path d="m5 12 5 5 9-10"/>', alert: '<path d="M12 9v4M12 17h.01M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>',
  star: '<path d="m12 3 2.8 5.8 6.2.9-4.5 4.4 1 6.2L12 17.4 6.5 20.3l1-6.2L3 9.7l6.2-.9L12 3Z"/>',
  dice: '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 8h.01M16 8h.01M12 12h.01M8 16h.01M16 16h.01"/>',
  speaker: '<path d="M11 5 6 9H3v6h3l5 4V5ZM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12"/>',
  text: '<path d="M4 6h16M4 11h16M4 16h10"/>',
  gauge: '<path d="M12 14l4-4M4 18a9 9 0 1 1 16 0"/>',
  question: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/>',
  code: '<path d="m8 7-5 5 5 5M16 7l5 5-5 5"/>',
};
const icon = (name, cls = '') => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ''}</svg>`;
function paintIcons(root = document) { root.querySelectorAll('[data-icon]').forEach((el) => { el.outerHTML = icon(el.dataset.icon); }); }

// ---------- server ----------
async function api(path, opts = {}) {
  const init = { method: opts.method || 'GET', headers: { 'X-Studio': '1' } };
  if (opts.json !== undefined) { init.body = JSON.stringify(opts.json); init.headers['Content-Type'] = 'application/json'; }
  if (opts.form) init.body = opts.form;
  const r = await fetch(path, init);
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : (j.detail?.[0]?.msg || msg); } catch { /* not JSON */ }
    throw new Error(msg);
  }
  return opts.raw ? r : r.json();
}

let toastTimer;
function toast(msg, ok = false) {
  const t = $('toast');
  const host = [...document.querySelectorAll('dialog[open]')].pop() || document.body;
  if (t.parentElement !== host) host.append(t);
  t.innerHTML = `${icon(ok ? 'check' : 'alert')}<span>${esc(msg)}</span>`; t.className = 'toast' + (ok ? ' ok' : ''); t.hidden = false;
  t.style.animation = 'none'; void t.offsetWidth; t.style.animation = '';  // slide in again for each message
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, ok ? 2600 : 7000);
}
// Copy to the clipboard; the old way when the browser refuses the new one.
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); return; } catch { /* fall back below */ }
  const ta = Object.assign(document.createElement('textarea'), { value: text, readOnly: true });
  ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
  document.body.append(ta); ta.select();
  const ok = document.execCommand('copy'); ta.remove();
  if (!ok) throw new Error("Couldn't copy. Select the text and press Ctrl+C.");
}
const run = (fn) => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message); } };

// Polling redraws constantly: only touch the DOM when the markup changed, and not while a button is held.
let pointerHeld = false;
window.addEventListener('pointerdown', () => { pointerHeld = true; }, true);
window.addEventListener('pointerup', () => { pointerHeld = false; }, true);
function setHtml(el, html) {
  if (!el || el._html === html || pointerHeld) return;
  // Keep audio that's playing: redraws would stop it.
  if ([...el.querySelectorAll('audio')].some((a) => !a.paused)) return;
  el._html = html;
  el.innerHTML = html;
}

function fmtDur(sec) {
  if (sec == null) return '—';
  sec = Math.round(sec);
  if (sec < 60) return `${sec} s`;
  const m = Math.floor(sec / 60), s = sec % 60;
  if (m < 60) return `${m} min${s ? ` ${s} s` : ''}`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}
function fmtClock(sec) { sec = Math.round(sec || 0); return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`; }
function fmtWhen(iso) {
  if (!iso) return '';
  const d = new Date(iso), now = new Date();
  const time = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (d.toDateString() === now.toDateString()) return `today ${time}`;
  return `${d.toLocaleDateString([], { day: 'numeric', month: 'short' })} ${time}`;
}
const fmtSize = (b) => (b >= 1e9 ? `${(b / 1e9).toFixed(1)} GB` : b >= 1e6 ? `${Math.round(b / 1e6)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`);
const langName = (code) => S.state?.languages?.[code] || code || '—';
const voiceName = (id) => S.voices.find((v) => v.id === id)?.name || (id ? id : 'no voice');
const fileUrl = (b, rel, v, dl) => `/api/batches/${b}/files/${rel.split('/').map(encodeURIComponent).join('/')}?v=${encodeURIComponent(v || '')}${dl ? '&download=1' : ''}`;

// ---------- theme ----------
// Light, dark, or the same as Windows (''). Kept in this browser; index.html applies it before the page draws.
const THEME = 'fvs-theme';
function themePick() { try { return localStorage.getItem(THEME) || ''; } catch { return ''; } }
function setTheme(t) {
  try { if (t) localStorage.setItem(THEME, t); else localStorage.removeItem(THEME); } catch { /* storage off */ }
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  apRedrawAll();
}
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => apRedrawAll());

// ---------- audio players ----------
// Every player is ours: a hidden <audio>, a play button, a waveform to click or drag, and the time. The markup is a
// plain string (so setHtml can compare it); the waveform is drawn once the player scrolls into view.
// `seconds` (when the length is already known, as for parts): the audio loads only when played, so a batch page with
// a hundred parts doesn't open a hundred audio downloads at once.
const player = (src, { autoplay = false, small = false, seconds = null } = {}) => `<div class="ap${small ? ' sm' : ''}"${seconds ? ` data-seconds="${seconds}"` : ''}>
  <audio preload="${seconds && !autoplay ? 'none' : 'metadata'}" src="${esc(src)}"${autoplay ? ' autoplay' : ''}></audio>
  <button class="ap-play" type="button" aria-label="Play">${icon('play', 'i-play')}${icon('pause', 'i-pause')}</button>
  <div class="ap-wave" role="slider" tabindex="0" aria-label="Position" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0"><canvas></canvas></div>
  <span class="ap-time"><b>0:00</b> / ${fmtClock(seconds || 0)}</span></div>`;

const AP = { peaks: new Map(), queue: [], loading: 0 };
const apAudio = (ap) => ap.querySelector('audio');
const apFrac = (ap) => { const a = apAudio(ap); return a.duration ? a.currentTime / a.duration : 0; };
function apTime(ap) {
  const a = apAudio(ap), wave = ap.querySelector('.ap-wave');
  const dur = Number.isFinite(a.duration) ? a.duration : Number(ap.dataset.seconds) || 0;
  ap.querySelector('.ap-time').innerHTML = `<b>${fmtClock(a.currentTime)}</b> / ${fmtClock(dur)}`;
  wave.setAttribute('aria-valuemax', Math.round(dur)); wave.setAttribute('aria-valuenow', Math.round(a.currentTime));
  wave.setAttribute('aria-valuetext', `${fmtClock(a.currentTime)} of ${fmtClock(dur)}`);
}
function apDraw(ap) {
  const cv = ap?.querySelector('canvas'); if (!cv) return;
  const w = cv.clientWidth, h = cv.clientHeight; if (!w || !h) return;
  const dpr = window.devicePixelRatio || 1;
  if (cv.width !== Math.round(w * dpr) || cv.height !== Math.round(h * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
  const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
  const css = getComputedStyle(ap), accent = css.getPropertyValue('--accent').trim(), rest = css.getPropertyValue('--wave').trim();
  const peaks = AP.peaks.get(apAudio(ap).getAttribute('src'));
  const played = apFrac(ap) * w, hover = ap._hover == null ? -1 : ap._hover * w;
  if (peaks === null) {  // couldn't read the audio: a plain track
    ctx.fillStyle = rest; ctx.beginPath(); ctx.roundRect(0, h / 2 - 2, w, 4, 2); ctx.fill();
    ctx.fillStyle = accent; ctx.beginPath(); ctx.roundRect(0, h / 2 - 2, played, 4, 2); ctx.fill();
    return;
  }
  const step = 3, n = Math.max(1, Math.floor(w / step));
  for (let i = 0; i < n; i++) {
    let v = 0.07;  // flat while the waveform loads
    if (peaks) {
      const a = Math.floor(i * peaks.length / n), b = Math.max(a + 1, Math.floor((i + 1) * peaks.length / n));
      v = 0; for (let k = a; k < b; k++) v = Math.max(v, peaks[k]);
    }
    const bh = Math.max(2, v * h), x = i * step;
    ctx.fillStyle = x < played || x < hover ? accent : rest;
    ctx.globalAlpha = x >= played && x < hover ? 0.4 : 1;
    ctx.fillRect(x, (h - bh) / 2, 2, bh);
  }
  ctx.globalAlpha = 1;
}
// Peaks: decoded at a low sample rate (so a 30-minute take is a few MB), 800 buckets, cached by URL (URLs carry a version).
async function apPeaks(src) {
  const buf = await (await fetch(src)).arrayBuffer();
  let audio;
  for (const rate of [3000, 8000]) {
    try { audio = await new OfflineAudioContext(1, 1, rate).decodeAudioData(buf.slice(0)); break; } catch { /* try the next rate */ }
  }
  if (!audio) throw new Error('undecodable');
  const data = audio.getChannelData(0), N = 800, per = Math.max(1, Math.floor(data.length / N)), out = new Float32Array(N);
  let top = 0;
  for (let i = 0; i < N; i++) {
    let m = 0;
    for (let k = i * per, e = Math.min(data.length, k + per); k < e; k++) { const x = Math.abs(data[k]); if (x > m) m = x; }
    out[i] = m; if (m > top) top = m;
  }
  for (let i = 0; i < N; i++) out[i] = top ? Math.pow(out[i] / top, 0.8) : 0;
  return out;
}
function apPump() {
  while (AP.loading < 2 && AP.queue.length) {
    const src = AP.queue.shift(); AP.loading++;
    apPeaks(src).then((p) => AP.peaks.set(src, p), () => AP.peaks.set(src, null)).finally(() => {
      AP.loading--;
      document.querySelectorAll('.ap').forEach((ap) => { if (apAudio(ap).getAttribute('src') === src) apDraw(ap); });
      apPump();
    });
  }
}
const apSeen = new IntersectionObserver((entries) => entries.forEach((e) => {
  if (!e.isIntersecting) return;
  apSeen.unobserve(e.target);
  const src = apAudio(e.target).getAttribute('src');
  if (src && !AP.peaks.has(src) && !AP.queue.includes(src)) { AP.queue.push(src); apPump(); }
}), { rootMargin: '200px' });
const apSized = new ResizeObserver((entries) => entries.forEach((e) => apDraw(e.target.closest('.ap'))));
function apInit(root) {
  root.querySelectorAll('.ap:not([data-init])').forEach((ap) => {
    ap.dataset.init = '1';
    apSeen.observe(ap); apSized.observe(ap.querySelector('.ap-wave'));
    const a = apAudio(ap);
    if (a.readyState >= 1) apTime(ap);
    if (!a.paused) ap.classList.add('playing');
  });
}
// A player that leaves the page lets go of its audio at once (browsers allow only so many per tab, and a running
// batch redraws its page after every part).
function apRelease(node) {
  const aps = node.matches?.('.ap') ? [node] : [...(node.querySelectorAll?.('.ap') || [])];
  aps.forEach((ap) => {
    if (ap.isConnected) return;  // moved, not removed
    apSeen.unobserve(ap); const wave = ap.querySelector('.ap-wave'); if (wave) apSized.unobserve(wave);
    const a = apAudio(ap); if (!a) return;
    a.pause(); a.removeAttribute('src'); a.load();
  });
}
new MutationObserver((muts) => muts.forEach((m) => {
  m.removedNodes.forEach((n) => { if (n.nodeType === 1) apRelease(n); });
  m.addedNodes.forEach((n) => { if (n.nodeType === 1 && n.parentElement) apInit(n.parentElement); });
})).observe(document.body, { childList: true, subtree: true });
// While something plays, move the time and the waveform every frame.
function apTick() {
  const live = document.querySelectorAll('.ap.playing');
  live.forEach((ap) => { apTime(ap); apDraw(ap); });
  if (live.length) requestAnimationFrame(apTick);
}
// Media events don't bubble, but they can be caught on the way down.
['play', 'pause', 'ended', 'loadedmetadata', 'durationchange', 'seeked', 'emptied'].forEach((type) => document.addEventListener(type, (e) => {
  const ap = e.target.closest?.('.ap'); if (!ap) return;
  if (type === 'play') {
    document.querySelectorAll('audio').forEach((o) => { if (o !== e.target && !o.paused) o.pause(); });  // one at a time
    ap.classList.add('playing'); ap.querySelector('.ap-play').setAttribute('aria-label', 'Pause');
    ap.closest('.seg-row')?.classList.add('speaking');
    requestAnimationFrame(apTick);
  } else if (type === 'pause' || type === 'ended' || type === 'emptied') {
    ap.classList.remove('playing'); ap.querySelector('.ap-play').setAttribute('aria-label', 'Play');
    ap.closest('.seg-row')?.classList.remove('speaking');
  }
  apTime(ap); apDraw(ap);
}, true));
// Start the file again from scratch: an <audio> whose loading once failed (the server was busy, the page redrew
// mid-download) stays broken until it's told to load again.
function apReload(a) { const src = a.getAttribute('src'); a.removeAttribute('src'); a.load(); a.setAttribute('src', src); a.load(); }
async function apPlay(a) {
  if (a.error) apReload(a);
  try { await a.play(); return; } catch (err) { if (err.name === 'AbortError') return; }
  apReload(a);  // one more try with a fresh load
  try { await a.play(); } catch (err) {
    if (err.name !== 'AbortError') toast(`Couldn't play this audio. Reload the page and try again. (${err.message})`);
  }
}
const apToggle = (a) => { if (a.paused) apPlay(a); else a.pause(); };
document.addEventListener('click', (e) => { const b = e.target.closest('.ap-play'); if (b) apToggle(apAudio(b.closest('.ap'))); });
function apSeekTo(ap, frac) {
  const a = apAudio(ap);
  if (!Number.isFinite(a.duration)) {  // not loaded yet (parts load when first used): load, then jump
    if (a.preload === 'none' || a.error) {
      a.preload = 'metadata'; if (a.error) apReload(a); else a.load();
      a.addEventListener('loadedmetadata', () => apSeekTo(ap, frac), { once: true });
    }
    return;
  }
  a.currentTime = Math.min(Math.max(frac, 0), 1) * a.duration;
  apTime(ap); apDraw(ap);
}
const apAt = (wave, e) => { const r = wave.getBoundingClientRect(); return (e.clientX - r.left) / r.width; };
document.addEventListener('pointerdown', (e) => {
  const wave = e.target.closest('.ap-wave'); if (!wave || e.button !== 0) return;
  const ap = wave.closest('.ap');
  wave.setPointerCapture(e.pointerId); ap._drag = true; apSeekTo(ap, apAt(wave, e));
});
document.addEventListener('pointermove', (e) => {
  const wave = e.target.closest?.('.ap-wave'); if (!wave) return;
  const ap = wave.closest('.ap');
  if (ap._drag) apSeekTo(ap, apAt(wave, e));
  else if (e.pointerType === 'mouse') { ap._hover = apAt(wave, e); apDraw(ap); }
});
document.addEventListener('pointerup', (e) => { const ap = e.target.closest?.('.ap'); if (ap) ap._drag = false; });
document.addEventListener('pointerout', (e) => {
  const wave = e.target.closest?.('.ap-wave');
  if (wave && !wave.contains(e.relatedTarget)) { const ap = wave.closest('.ap'); ap._hover = null; apDraw(ap); }
});
const apRedrawAll = () => document.querySelectorAll('.ap').forEach(apDraw);
document.addEventListener('keydown', (e) => {
  const wave = e.target.closest?.('.ap-wave'); if (!wave) return;
  const ap = wave.closest('.ap'), a = apAudio(ap);
  const by = { ArrowLeft: -5, ArrowDown: -5, ArrowRight: 5, ArrowUp: 5 }[e.key];
  if (by) a.currentTime = Math.max(0, Math.min(a.duration || 0, a.currentTime + by));
  else if (e.key === 'Home') a.currentTime = 0;
  else if (e.key === 'End' && a.duration) a.currentTime = a.duration;
  else if (e.key === ' ' || e.key === 'Enter') apToggle(a);
  else return;
  e.preventDefault(); apTime(ap); apDraw(ap);
});
const isBusy = (st) => ['running', 'queued', 'finishing'].includes(st);

const STATUS = {
  running: ['accent live', 'Speaking'], queued: ['', 'Queued'], paused: ['warn', 'Paused'], finishing: ['accent live', 'Finishing'],
  done: ['ok', 'Done'], failed: ['red', 'Needs attention'], cancelled: ['', 'Cancelled'], pending: ['', 'Waiting'],
};
const chip = (st) => { const [c, t] = STATUS[st] || ['', st]; return `<span class="chip ${c}">${t}</span>`; };

function confirmDialog(title, body, okLabel = 'Delete') {
  return new Promise((resolve) => {
    const dlg = $('confirm');
    $('confirm-title').textContent = title;
    $('confirm-body').textContent = body;
    $('confirm-ok').textContent = okLabel;
    dlg.returnValue = '';
    dlg.addEventListener('close', () => resolve(dlg.returnValue === 'ok'), { once: true });
    dlg.showModal();
  });
}

// A general editor dialog: title + big text + optional extra fields. Resolves with the values or null.
function editDialog({ title, help = '', name = null, nameLabel = 'Title', text = null, rows = 14, extra = '', ok = 'Save', onOpen }) {
  return new Promise((resolve) => {
    const dlg = $('editor');
    $('editor-title').textContent = title;
    $('editor-help').textContent = help; $('editor-help').hidden = !help;
    $('editor-name-field').hidden = name === null;
    $('editor-name-field').querySelector('label').textContent = nameLabel;
    $('editor-name').value = name ?? '';
    $('editor-text').hidden = text === null;
    $('editor-text').value = text ?? '';
    $('editor-text').rows = rows;
    $('editor-extra').innerHTML = extra;
    paintIcons($('editor-extra'));
    $('editor-ok').textContent = ok;
    dlg.returnValue = '';
    dlg.addEventListener('close', () => {
      if (dlg.returnValue !== 'ok') return resolve(null);
      const extraVals = {};
      $('editor-extra').querySelectorAll('[name]').forEach((el) => { extraVals[el.name] = el.type === 'checkbox' ? el.checked : el.value; });
      resolve({ name: $('editor-name').value, text: $('editor-text').value, ...extraVals });
    }, { once: true });
    dlg.showModal();
    onOpen?.(dlg);
  });
}

function voiceOptions(selected, { blank } = {}) {
  const opts = S.voices.map((v) => `<option value="${esc(v.id)}"${v.id === selected ? ' selected' : ''}>${esc(v.name)}${v.language ? ` · ${esc(langName(v.language))}` : ''}</option>`);
  if (blank) opts.unshift(`<option value=""${!selected ? ' selected' : ''}>${esc(blank)}</option>`);
  if (!S.voices.length && !blank) opts.unshift('<option value="">No voices yet — add one on the Voices page</option>');
  return opts.join('');
}
// Languages for a voice model (only those it speaks), or every language the app knows (voices, pronunciation, transcripts).
function languageOptions(selected, model) {
  const all = S.state?.languages || {};
  const m = model && (S.state?.models || []).find((x) => x.key === model);
  const codes = m?.languages?.length ? Object.keys(all).filter((k) => m.languages.includes(k)) : Object.keys(all);
  if (selected && !codes.includes(selected) && !m) codes.unshift(selected);
  return codes.map((k) => `<option value="${k}"${k === selected ? ' selected' : ''}>${esc(all[k] || k)}</option>`).join('');
}
const createModel = () => $('model')?.value || S.state?.default_model;

// ---------- routing ----------
const VIEWS = ['create', 'batches', 'batch', 'voices', 'models', 'setup', 'connect', 'settings', 'words', 'transcribe', 'help', 'about'];
const MENU_VIEWS = ['settings', 'words', 'models', 'setup', 'connect', 'about'];  // the pages in the menu on the right
function route() {
  const [view, arg] = (location.hash.slice(1) || 'create').split('/');
  let v = VIEWS.includes(view) ? view : 'create';
  if (document.body.classList.contains('locked') && !['setup', 'help'].includes(v)) { v = 'setup'; history.replaceState(null, '', '#setup'); }
  S.view = v; S.arg = arg ? decodeURIComponent(arg) : null;
  VIEWS.forEach((x) => { $(`view-${x}`).hidden = x !== v; });
  const locked = document.body.classList.contains('locked');
  document.querySelectorAll('.nav a, .bar-tools a').forEach((a) => {
    const on = a.dataset.view === v || (v === 'batch' && a.dataset.view === 'batches');
    if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
  if (MENU_VIEWS.includes(v) && !locked) $('menu-btn').setAttribute('aria-current', 'page'); else $('menu-btn').removeAttribute('aria-current');
  document.querySelectorAll('#settings-menu a').forEach((a) => a.classList.toggle('on', a.dataset.view === v));
  closeMenu();
  ({ create: showCreate, batches: loadBatches, batch: loadDetail, voices: loadVoices, models: loadModels, setup: loadSetup,
     connect: loadConnect, settings: loadSettings, words: loadWords, transcribe: loadTranscribe, help: loadHelp, about: loadAbout })[v]?.();
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);

// The menu on the right of the top bar: Settings, Pronunciation, Models, Setup, Connect, About.
function closeMenu() { $('settings-menu').hidden = true; $('menu-btn').setAttribute('aria-expanded', 'false'); }
$('menu-btn').addEventListener('click', () => {
  const m = $('settings-menu');
  if (!m.hidden) { closeMenu(); return; }
  m.hidden = false;
  const r = $('menu-btn').getBoundingClientRect();
  m.style.left = `${Math.max(8, Math.min(r.right - m.offsetWidth, innerWidth - m.offsetWidth - 8))}px`; m.style.top = `${r.bottom + 6}px`;
  $('menu-btn').setAttribute('aria-expanded', 'true');
  m.querySelector('a').focus();
});
document.addEventListener('click', (e) => { if (!e.target.closest('#menu-btn, #settings-menu')) closeMenu(); });
$('settings-menu').addEventListener('keydown', (e) => {
  const items = [...$('settings-menu').querySelectorAll('a')], i = items.indexOf(document.activeElement);
  if (e.key === 'Escape') { closeMenu(); $('menu-btn').focus(); }
  else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); items[(i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus(); }
});

document.addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-open-folder]');
  if (b) await api('/api/open-folder', { method: 'POST', json: { which: b.dataset.openFolder } });
}));

// ---------- status poll ----------
async function pollState() {
  try {
    S.state = await api('/api/state');
  } catch {
    $('engine-text').textContent = 'Not running'; $('engine-dot').className = 'state-dot error';
    return;
  }
  const st = S.state;
  const wasLocked = document.body.classList.contains('locked');
  document.body.classList.toggle('locked', !st.setup_ready);
  if (!st.setup_ready && !['setup', 'help'].includes(S.view)) location.hash = '#setup';
  if (wasLocked && st.setup_ready) route();
  const eng = st.engine;
  let text, sub = '', dot = '';
  if (eng.state === 'error') { text = 'Engine problem'; sub = eng.error || ''; dot = 'error'; }
  else if (st.current || st.api_busy) {
    dot = 'busy';
    const pct = eng.frames_expected ? Math.min(99, Math.round(100 * eng.frames / eng.frames_expected)) : null;
    text = st.api_busy && !st.current ? 'Speaking · API / preview' : `Speaking${pct != null ? ` · ${pct}%` : ''}`;
    sub = st.current ? `“${st.current.text}”` : '';
  } else if (st.finishing) {
    dot = 'busy';
    const p = st.finishing.progress;
    text = `Writing files · subtitles${p != null ? ` · ${p}%` : ''}`;
    sub = st.finishing.gpu ? 'Whisper on the graphics card' : 'Whisper on the processor';
  }
  else { text = st.setup_ready ? `Ready · ${eng.engine.toUpperCase()}` : 'Setup needed'; dot = st.setup_ready ? '' : 'off'; }
  const finPct = st.finishing?.progress;
  const ring = dot === 'busy' && ((st.current && eng.frames_expected) || finPct != null);
  $('engine-text').textContent = text; $('engine-sub').textContent = sub; $('engine-sub').title = sub;
  $('engine-dot').className = `state-dot ${dot}${ring ? ' ring' : ''}`;
  $('engine-dot').style.setProperty('--p', !ring ? 0 : st.current ? Math.min(99, Math.round(100 * eng.frames / eng.frames_expected)) : finPct);
  $('foot-right').innerHTML = `<a href="#about">v${esc(st.version)}</a> · ${esc(st.api_base)}`;
  if (st.update?.status === 'available') $('foot-left').innerHTML = `Fatima Voice Studio · <a href="#about">update ${esc(st.update.latest)} available</a>`;
  renderUpdateBadge();
}

// An update: a dot on the menu button (and on About in the menu), and a one-time message.
let updToasted = null;
function renderUpdateBadge() {
  const available = S.state?.update?.status === 'available';
  for (const link of [$('menu-btn'), document.querySelector('#settings-menu a[href="#about"]')]) {
    let dot = link.querySelector('.badge');
    if (available && !dot) { dot = document.createElement('span'); dot.className = 'badge'; dot.title = 'Update available'; link.append(dot); }
    if (!available && dot) dot.remove();
  }
  const latest = S.state?.update?.latest;
  if (available && updToasted !== latest && !document.body.classList.contains('locked')) {
    updToasted = latest;
    toast(`Version ${latest} is available — see About in the menu at the top right`, true);
  }
}

// ---------- CREATE ----------
const DRAFT = 'fvs-draft-v1';
function saveDraft() {
  try { localStorage.setItem(DRAFT, JSON.stringify({ single: $('single-text').value, scripts: S.scripts, name: $('batch-name').value, cmode: S.cmode })); } catch { /* storage off */ }
}
function loadDraft() {
  try {
    const d = JSON.parse(localStorage.getItem(DRAFT) || '{}');
    $('single-text').value = d.single || '';
    S.scripts = Array.isArray(d.scripts) && d.scripts.length ? d.scripts : [{ title: '', text: '' }];
    $('batch-name').value = d.name || '';
    if (d.cmode) setCmode(d.cmode, false);
  } catch { S.scripts = [{ title: '', text: '' }]; }
}

function setCmode(mode, save = true) {
  S.cmode = mode;
  $('composer').dataset.cmode = mode; document.body.dataset.cmode = mode;
  $('create-mode').querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', b.dataset.cmode === mode));
  $('go-label').textContent = mode === 'single' ? 'Make it' : 'Start batch';
  if (save) saveDraft();
  updateSummary();
}
$('create-mode').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) setCmode(b.dataset.cmode); });

function setSmode(mode) {
  S.smode = mode;
  document.querySelectorAll('[data-smode]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.smode === mode));
  $('script-list').hidden = mode !== 'list'; $('list-tools').hidden = mode !== 'list';
  $('paste-box').hidden = mode !== 'paste';
}
document.querySelectorAll('[data-smode]').forEach((b) => b.addEventListener('click', () => setSmode(b.dataset.smode)));

function renderScripts() {
  $('script-list').innerHTML = S.scripts.map((s, i) => `
    <li class="script-row" data-i="${i}">
      <div class="head"><span class="num">${String(i + 1).padStart(2, '0')}</span>
        <input class="title" data-f="title" value="${esc(s.title)}" placeholder="Title (optional — taken from the first words)">
        <button type="button" class="icon-btn" data-act="del" aria-label="Remove script">${icon('x')}</button></div>
      <textarea data-f="text" rows="${Math.min(12, Math.max(3, Math.ceil((s.text || '').length / 70)))}" placeholder="Script text. Blank lines start a new paragraph.">${esc(s.text)}</textarea>
      <div class="foot">
        <span class="meta">${s.text ? `${s.text.length.toLocaleString()} characters · about ${fmtDur(s.text.length / 14)}` : ''}</span>
        <span class="row" style="gap:6px">
          <select class="mini" data-f="voice" aria-label="Voice for this script">${voiceOptions(s.voice || '', { blank: 'Batch voice' })}</select>
          <select class="mini" data-f="language" aria-label="Language for this script"><option value="">Batch language</option>${languageOptions(s.language || '', createModel())}</select>
        </span></div>
    </li>`).join('');
  $('script-count').textContent = plural(S.scripts.filter((s) => s.text.trim()).length, 'script');
}
$('script-list').addEventListener('input', (e) => {
  const row = e.target.closest('.script-row'); if (!row) return;
  const f = e.target.dataset.f;
  S.scripts[row.dataset.i][f] = e.target.value;
  if (f === 'voice' && e.target.value) {  // a voice brings its own language
    const v = S.voices.find((x) => x.id === e.target.value);
    if (v?.language) { S.scripts[row.dataset.i].language = v.language; row.querySelector('[data-f="language"]').value = v.language; }
  }
  if (f === 'text') row.querySelector('.meta').textContent = e.target.value ? `${e.target.value.length.toLocaleString()} characters · about ${fmtDur(e.target.value.length / 14)}` : '';
  $('script-count').textContent = plural(S.scripts.filter((s) => s.text.trim()).length, 'script');
  saveDraft(); updateSummary();
});
$('script-list').addEventListener('click', (e) => {
  const b = e.target.closest('[data-act="del"]'); if (!b) return;
  S.scripts.splice(Number(b.closest('.script-row').dataset.i), 1);
  if (!S.scripts.length) S.scripts.push({ title: '', text: '' });
  renderScripts(); saveDraft(); updateSummary();
});
$('add-script').addEventListener('click', () => {
  S.scripts.push({ title: '', text: '' }); renderScripts(); saveDraft();
  $('script-list').lastElementChild?.querySelector('textarea')?.focus();
});

// "Paste and split": ### headings or --- lines separate scripts.
function splitPasted(text) {
  const out = [];
  let cur = null;
  for (const line of text.replace(/\r\n?/g, '\n').split('\n')) {
    const h = line.match(/^\s*#{1,3}\s+(.+?)\s*$/);
    if (h || /^\s*-{3,}\s*$/.test(line)) {
      if (cur && cur.text.trim()) out.push(cur);
      cur = { title: h ? h[1] : '', text: '' };
    } else {
      cur = cur || { title: '', text: '' };
      cur.text += line + '\n';
    }
  }
  if (cur && cur.text.trim()) out.push(cur);
  return out.map((s) => ({ title: s.title, text: s.text.trim() }));
}
$('paste-text').addEventListener('input', () => {
  const found = splitPasted($('paste-text').value);
  $('paste-found').textContent = found.length ? `${plural(found.length, 'script')} found: ${found.slice(0, 4).map((s) => s.title || s.text.slice(0, 24) + '…').join(' · ')}${found.length > 4 ? ' …' : ''}` : 'No scripts found yet.';
  $('paste-apply').disabled = !found.length;
});
$('paste-apply').addEventListener('click', () => {
  const found = splitPasted($('paste-text').value);
  const keep = S.scripts.filter((s) => s.text.trim());
  S.scripts = [...keep, ...found];
  $('paste-text').value = ''; $('paste-apply').disabled = true; $('paste-found').textContent = 'No scripts found yet.';
  setSmode('list'); renderScripts(); saveDraft(); updateSummary();
  toast(`Added ${plural(found.length, 'script')}.`, true);
});

// Import: each .txt/.md file is a script (title = file name); a .csv has columns text,title,voice,language.
function parseCSV(text) {
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') q = false; else cell += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const head = (rows.shift() || []).map((h) => h.trim().toLowerCase());
  const col = (name) => head.indexOf(name);
  if (col('text') < 0 && col('script') < 0) throw new Error('The CSV needs a "text" column (and optionally title, voice, language).');
  const ti = col('text') >= 0 ? col('text') : col('script');
  return rows.filter((r) => (r[ti] || '').trim()).map((r) => {
    const s = { title: (r[col('title')] || '').trim(), text: r[ti].trim() };
    const v = (r[col('voice')] || '').trim(); if (v) s.voice = v;
    const l = (r[col('language')] || '').trim().toLowerCase(); if (l) s.language = l;
    return s;
  });
}
$('import-btn').addEventListener('click', () => $('import-file').click());
$('import-file').addEventListener('change', run(async (e) => {
  const added = [];
  for (const f of e.target.files) {
    const text = await f.text();
    if (/\.csv$/i.test(f.name)) added.push(...parseCSV(text));
    else added.push({ title: f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' '), text: text.trim() });
  }
  e.target.value = '';
  S.scripts = [...S.scripts.filter((s) => s.text.trim()), ...added.filter((s) => s.text)];
  setSmode('list'); renderScripts(); saveDraft(); updateSummary();
  toast(`Imported ${plural(added.length, 'script')}.`, true);
}));

function fillCreateSelects() {
  const st = S.state; if (!st) return;
  const s = S.settings || {};
  const keepVoice = $('voice').value || s.default_voice || st.default_voice;
  $('voice').innerHTML = voiceOptions(keepVoice);
  const v = S.voices.find((x) => x.id === $('voice').value);
  const keepModel = $('model').value || st.default_model;
  $('model').innerHTML = st.models.filter(speakable).map((m) => `<option value="${m.key}"${m.key === keepModel ? ' selected' : ''}${m.installed ? '' : ' disabled'}>${esc(m.label)}${m.installed ? '' : ' (not downloaded)'}</option>`).join('');
  const m = st.models.find((x) => x.key === $('model').value);
  const keepLang = $('language').dataset.touched ? $('language').value : (v?.language || st.default_language);
  $('language').innerHTML = languageOptions(keepLang, createModel());  // only what this model speaks
  $('model-license').innerHTML = (m ? licenseBadge(m) : '') + (m?.tags ? '<span class="tag-hint">This model follows <b>[tags]</b> in the text: <code>[whisper]</code>, <code>[excited]</code>, <code>[sad]</code>, <code>[low voice]</code>, or any short instruction in square brackets. Subtitles leave them out. <a href="#help/writing-scripts/emotion-tags-s2-pro">More</a></span>' : '');
  $('voice-help').innerHTML = !S.voices.length ? 'Add a voice first: <a href="#voices">Voices → Add a voice</a> (a 6–15 second clip), or find a new one there.'
    : (v?.advice?.length && v.source !== 'kokoro' ? `${icon('alert')} ${esc(v.advice[0])}` : '');
  if (!$('pause-paragraph').value) $('pause-paragraph').value = s.pause_paragraph ?? 0.7;
  if (!$('loudness').dataset.touched && s.loudness != null) {
    const val = String(Math.round(s.loudness));
    if ([...$('loudness').options].some((o) => o.value === val)) $('loudness').value = val;
  }
  if (!$('fmt-wav').dataset.touched && s.formats) { $('fmt-wav').checked = s.formats.includes('wav'); $('fmt-mp3').checked = s.formats.includes('mp3'); }
  if (!$('opt-srt').dataset.touched && s.subtitles != null) $('opt-srt').checked = s.subtitles;
  if (!$('speed').dataset.touched && s.speed != null) setSelect($('speed'), s.speed);
  if (!$('opt-numbers').dataset.touched && s.spell_numbers != null) $('opt-numbers').checked = s.spell_numbers;
}
$('voice').addEventListener('change', () => {
  const v = S.voices.find((x) => x.id === $('voice').value);
  if (v?.language && !$('language').dataset.touched) $('language').value = v.language;
  fillCreateSelects(); updateSummary();
});
$('language').addEventListener('change', () => { $('language').dataset.touched = '1'; });
['loudness', 'fmt-wav', 'fmt-mp3', 'opt-srt'].forEach((id) => $(id).addEventListener('change', () => { $(id).dataset.touched = '1'; }));
$('model').addEventListener('change', () => { fillCreateSelects(); renderScripts(); });  // each script's languages follow the model

// Select the option closest to a value (speeds and loudness are numbers; options are a few steps).
function setSelect(sel, value) {
  const opts = [...sel.options];
  const best = opts.reduce((a, o) => (Math.abs(Number(o.value) - Number(value)) < Math.abs(Number(a.value) - Number(value)) ? o : a), opts[0]);
  if (best) sel.value = best.value;
}

function licenseBadge(m) {
  return m.noncommercial ? `<span class="license nc">${icon('alert')} ${esc(m.license)}</span>` : `<span class="license ok">${icon('check')} ${esc(m.license)}</span>`;
}

function createSettings() {
  const formats = [$('fmt-wav').checked && 'wav', $('fmt-mp3').checked && 'mp3'].filter(Boolean);
  const out = { voice: $('voice').value, language: $('language').value, model: $('model').value,
                formats: formats.length ? formats : ['mp3'], subtitles: $('opt-srt').checked,
                loudness: Number($('loudness').value), pause_paragraph: Number($('pause-paragraph').value || 0.7),
                speed: Number($('speed').value), spell_numbers: $('opt-numbers').checked };
  if ($('seed').value !== '') out.seed = Number($('seed').value);
  return out;
}

let summaryTimer;
function updateSummary() {
  clearTimeout(summaryTimer);
  summaryTimer = setTimeout(async () => {
    const texts = S.cmode === 'single' ? [$('single-text').value] : S.scripts.map((s) => s.text);
    const filled = texts.filter((t) => t.trim());
    if (!filled.length) { $('summary').innerHTML = S.cmode === 'single' ? 'Type something to hear it.' : 'Add a script, paste several, or import files.'; return; }
    try {
      let segs = 0, est = 0;
      for (const t of filled) {
        const r = await api('/api/split-preview', { method: 'POST', json: { text: t, pause_paragraph: Number($('pause-paragraph').value || 0.7) } });
        segs += r.segments; est += r.estimate_s + r.pauses_s;
      }
      const pace = Number($('speed').value) || 1;
      const make = est / (S.setupBench?.x_realtime || 2) + filled.length * 3;  // the engine speaks at natural pace
      est /= pace;
      $('summary').innerHTML = `${S.cmode === 'batch' ? `<b>${plural(filled.length, 'script')}</b> · ` : ''}<b>${plural(segs, 'part')}</b> · about <b>${fmtDur(est)}</b> of audio · ready in about <b>${fmtDur(make)}</b>${S.setupBench ? '' : ' (estimate; run the speed test in Setup for yours)'}`;
    } catch { /* server busy */ }
  }, 350);
}
$('single-text').addEventListener('input', () => { saveDraft(); updateSummary(); });
$('pause-paragraph').addEventListener('input', updateSummary);
$('speed').addEventListener('change', () => { $('speed').dataset.touched = '1'; updateSummary(); });
$('opt-numbers').addEventListener('change', () => { $('opt-numbers').dataset.touched = '1'; });
$('batch-name').addEventListener('input', saveDraft);
$('single-text').addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); $('go').click(); } });

$('go').addEventListener('click', run(async () => {
  if (!S.voices.length) { location.hash = '#voices'; throw new Error('Add a voice first (Voices page).'); }
  const settings = createSettings();
  $('go').disabled = true;
  try {
    if (S.cmode === 'single') {
      const text = $('single-text').value.trim();
      if (!text) throw new Error('Type the text to speak.');
      const r = await api('/api/singles', { method: 'POST', json: { text, settings } });
      S.single = { batch: r.batch.id, n: r.script.n };
      renderSingle();
    } else {
      const scripts = S.scripts.filter((s) => s.text.trim()).map((s) => ({ title: s.title || null, text: s.text, voice: s.voice || null, language: s.language || null }));
      if (!scripts.length) throw new Error('Add at least one script.');
      const b = await api('/api/batches', { method: 'POST', json: { name: $('batch-name').value.trim() || null, scripts, settings } });
      S.scripts = [{ title: '', text: '' }]; $('batch-name').value = ''; renderScripts(); saveDraft();
      toast(`Batch “${b.name}” started.`, true);
      location.hash = `#batch/${b.id}`;
    }
  } finally { $('go').disabled = false; }
}));

// The quick take's result card follows that single until it's done.
async function renderSingle() {
  if (!S.single) return;
  let d;
  try { d = await api(`/api/batches/${S.single.batch}`); } catch { return; }
  const s = d.scripts.find((x) => x.n === S.single.n);
  if (!s) return;
  $('single-empty').hidden = true; $('single-out').hidden = false;
  const out = s.output, v = out.finished || '';
  let html = `<div class="row between"><span class="micro">Quick take · ${esc(s.voice_name || '')} · ${esc(langName(s.language))}</span>${chip(s.status)}</div>
    <div class="take"><div class="text">${esc(s.text)}</div>`;
  if (s.status === 'done') {
    const main = out.files.mp3 || out.files.wav;
    html += `${player(fileUrl(d.id, main, v), { autoplay: true })}
      <div class="files">${Object.entries(out.files).map(([k, f]) => `<a class="btn sm" href="${fileUrl(d.id, f, v, 1)}" download>${icon('download')} ${k.toUpperCase()}</a>`).join('')}
      <button class="btn sm" data-single="again">${icon('dice')} Another take</button>
      <a class="btn sm" href="#batch/${d.id}">Open in Batches</a></div>
      <span class="micro">${fmtDur(out.seconds)} · ${out.match != null ? `Whisper heard ${Math.round(out.match * 100)}% of the words` : ''}</span>`;
  } else if (s.status === 'failed') {
    const it = d.items.find((x) => x.script === s.n && x.error);
    html += `<p class="err-note">${esc(it?.error || out.error || 'Something went wrong.')}</p><a class="btn sm" href="#batch/${d.id}">Open to retry</a>`;
  } else {
    const done = s.done, total = s.segments;
    html += `<div class="progress live"><div style="width:${Math.max(6, 100 * done / Math.max(1, total))}%"></div></div><span class="micro">${s.status === 'finishing' ? 'Writing the files…' : `Part ${Math.min(done + 1, total)} of ${total}…`}</span>`;
  }
  setHtml($('single-out'), html + '</div>');
  if (isBusy(s.status) || s.status === 'queued') setTimeout(renderSingle, 1200);
}
$('single-out').addEventListener('click', run(async (e) => {
  if (!e.target.closest('[data-single="again"]')) return;
  $('seed').value = '';
  $('go').click();
}));

// Audio made today, this week and in all, from the batch list (counted by the day a batch was made).
function madeStats(batches) {
  const day = new Date(); day.setHours(0, 0, 0, 0);
  const week = new Date(day); week.setDate(day.getDate() - ((day.getDay() + 6) % 7));  // since Monday
  const sum = (from) => batches.filter((b) => !from || new Date(b.created) >= from).reduce((t, b) => t + (b.audio_seconds || 0), 0);
  const all = sum(null);
  if (!all) return '<p class="made-empty">Your first voiceover will show up here.</p>';
  const short = (sec) => sec < 60 ? `${Math.round(sec)} s` : sec < 3600 ? `${Math.round(sec / 60)} min` : `${Math.floor(sec / 3600)} h ${Math.round(sec % 3600 / 60)} min`;
  const tile = (label, sec) => `<div><b>${sec ? short(sec) : '—'}</b><small>${label}</small></div>`;
  return `<div class="made">${tile('Made today', sum(day))}${tile('This week', sum(week))}${tile('In all', all)}</div>`;
}
async function renderQueue() {
  if (S.view !== 'create') return;
  try { S.batches = await api('/api/batches'); } catch { return; }
  const order = S.state?.queue || [];
  const active = S.batches.filter((b) => order.includes(b.id)).sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
  const recent = S.batches.filter((b) => !order.includes(b.id)).slice(0, 4);
  const row = (b, i) => `<div class="qitem">
      ${chip(b.status)}
      <a class="name" href="#batch/${b.id}">${esc(b.name)}</a>
      <span class="sub">${b.kind === 'singles' ? '' : `${b.scripts_done}/${b.scripts_total} scripts · `}${b.done}/${b.total} parts${b.eta_seconds ? ` · ~${fmtDur(b.eta_seconds)} left` : ''}</span>
      ${order.includes(b.id) ? `<button class="icon-btn" data-q="up" data-id="${b.id}" ${i === 0 ? 'disabled' : ''} aria-label="Move up">${icon('up')}</button>
      <button class="icon-btn" data-q="${b.paused ? 'resume' : 'pause'}" data-id="${b.id}" aria-label="${b.paused ? 'Resume' : 'Pause'}">${icon(b.paused ? 'play' : 'pause')}</button>` : ''}
    </div>`;
  setHtml($('queue-list'), madeStats(S.batches) + (active.length ? active.map(row).join('') : '<p class="help">Nothing waiting. New batches start right away.</p>')
    + (recent.length ? `<div class="micro" style="margin-top:12px">Recent</div>${recent.map(row).join('')}` : ''));
}
$('queue-list').addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-q]'); if (!b) return;
  const id = b.dataset.id;
  if (b.dataset.q === 'up') {
    const order = [...(S.state?.queue || [])];
    const i = order.indexOf(id); if (i > 0) { [order[i - 1], order[i]] = [order[i], order[i - 1]]; await api('/api/queue/order', { method: 'POST', json: { ids: order } }); }
  } else await api(`/api/batches/${id}/${b.dataset.q}`, { method: 'POST' });
  await pollState(); renderQueue();
}));

async function showCreate() {
  await loadVoicesList();
  loadPresets();
  fillCreateSelects(); renderScripts(); updateSummary(); renderQueue();
  if (S.single) renderSingle();
}

// ---------- BATCHES ----------
S.selecting = false;
S.selected = new Set();
async function loadBatches() {
  try { S.batches = await api('/api/batches'); } catch (e) { toast(e.message); return; }
  renderBatches();
}
function renderBatches() {
  const q = $('batch-search').value.trim().toLowerCase();
  const shown = S.batches.filter((b) => !q || b.name.toLowerCase().includes(q) || b.first_text.toLowerCase().includes(q));
  S.shown = shown;
  const html = shown.length ? shown.map((b) => `
    <div class="card bcard${S.selecting ? ' selectable' : ''}${S.selected.has(b.id) ? ' picked' : ''}" data-id="${b.id}">
      ${S.selecting ? `<input type="checkbox" ${S.selected.has(b.id) ? 'checked' : ''} ${isBusy(b.status) ? 'disabled' : ''} aria-label="Select">` : ''}
      <div class="main">
        <div class="row" style="gap:10px;min-width:0">${chip(b.status)}<a class="name" href="#batch/${b.id}">${esc(b.name)}</a></div>
        <div class="first">${esc(b.first_text)}</div>
        <div class="meta"><span>${fmtWhen(b.created)}</span>
          <span>${b.kind === 'singles' ? plural(b.scripts_total, 'quick take') : plural(b.scripts_total, 'script')}</span>
          ${b.audio_seconds ? `<span>${fmtDur(b.audio_seconds)} of audio</span>` : ''}
          ${isBusy(b.status) ? `<span>${b.done}/${b.total} parts${b.eta_seconds ? ` · ~${fmtDur(b.eta_seconds)} left` : ''}</span>` : ''}
          ${b.checks ? `<span style="color:var(--warn)">${plural(b.checks, 'part')} to check</span>` : ''}
          ${b.failed ? `<span style="color:var(--red-hi)">${b.failed} failed</span>` : ''}</div>
      </div>
      ${S.selecting ? '' : `<div class="acts">
        <a class="btn sm" href="#batch/${b.id}">View</a>
        <button class="btn sm" data-b="open" data-id="${b.id}">${icon('folder')} Folder</button>
        ${b.scripts_done ? `<a class="btn sm" href="/api/batches/${b.id}/export.zip?content=final">${icon('download')} ZIP</a>` : ''}
        <button class="btn sm" data-b="rerun" data-id="${b.id}">${icon('refresh')} Re-run</button>
        <button class="icon-btn" data-b="delete" data-id="${b.id}" aria-label="Delete">${icon('trash')}</button></div>`}
    </div>`).join('') : (q ? '<div class="card empty">No batch matches that search.</div>'
      : emptyCard('layers', 'No batches yet', 'Every voiceover you make is kept here as a batch: its files, its parts, and the script to edit later.', '<a class="btn accent" href="#create">Make your first voiceover</a>'));
  setHtml($('batch-list'), html);
  $('bulkbar').hidden = !S.selecting;
  $('bulk-count').textContent = `${S.selected.size} selected`;
  $('bulk-delete').disabled = !S.selected.size;
}
$('batch-search').addEventListener('input', renderBatches);
$('select-toggle').addEventListener('click', () => {
  S.selecting = !S.selecting; S.selected.clear();
  $('select-toggle').textContent = S.selecting ? 'Cancel' : 'Select';
  $('select-toggle').setAttribute('aria-pressed', S.selecting);
  $('batch-list')._html = ''; renderBatches();
});
$('select-all').addEventListener('click', () => { S.shown.filter((b) => !isBusy(b.status)).forEach((b) => S.selected.add(b.id)); $('batch-list')._html = ''; renderBatches(); });
$('bulk-delete').addEventListener('click', run(async () => {
  const n = S.selected.size;
  if (!await confirmDialog(`Delete ${plural(n, 'batch', 'batches')}?`, 'Their folders go to the Recycle Bin, so you can restore them from there.')) return;
  const r = await api('/api/batches-delete', { method: 'POST', json: { ids: [...S.selected] } });
  toast(`Deleted ${plural(r.deleted.length, 'batch', 'batches')}${r.skipped.length ? `; ${r.skipped.length} skipped (still working or in use)` : ''}.`, !r.skipped.length);
  S.selecting = false; S.selected.clear(); $('select-toggle').textContent = 'Select';
  loadBatches();
}));
$('batch-list').addEventListener('click', run(async (e) => {
  const card = e.target.closest('.bcard');
  if (S.selecting && card) {
    e.preventDefault();
    const b = S.batches.find((x) => x.id === card.dataset.id);
    if (!b || isBusy(b.status)) return;
    S.selected.has(b.id) ? S.selected.delete(b.id) : S.selected.add(b.id);
    $('batch-list')._html = ''; renderBatches(); return;
  }
  const btn = e.target.closest('[data-b]'); if (!btn) return;
  await batchAction(btn.dataset.id, btn.dataset.b);
  loadBatches();
}));

async function batchAction(id, act) {
  const b = S.batches.find((x) => x.id === id) || S.detail;
  if (act === 'delete') {
    if (!await confirmDialog(`Delete “${b?.name}”?`, 'The folder goes to the Recycle Bin, so you can restore it from there.')) return;
    await api(`/api/batches/${id}`, { method: 'DELETE' });
    toast('Moved to the Recycle Bin.', true);
    if (S.view === 'batch') location.hash = '#batches';
    return;
  }
  if (act === 'cancel' && !await confirmDialog('Stop this batch?', 'Parts not spoken yet are cancelled. Finished scripts are kept; you can Retry later.', 'Stop')) return;
  const r = await api(`/api/batches/${id}/${act}`, { method: 'POST' });
  if (act === 'rerun') { toast(`Re-running as “${r.name}”.`, true); location.hash = `#batch/${r.id}`; }
}

// ---------- ONE BATCH ----------
S.open = new Set();    // scripts whose parts the user opened
S.closed = new Set();  // ... or closed
async function loadDetail() {
  if (!S.arg) return;
  try { S.detail = await api(`/api/batches/${encodeURIComponent(S.arg)}`); } catch (e) { toast(e.message); location.hash = '#batches'; return; }
  if (!S.voices.length) await loadVoicesList();
  renderDetail();
}
function segRow(d, it) {
  const cur = S.state?.current;
  const running = cur && cur.batch === d.id && cur.item === it.id;
  return `<div class="seg-row st-${it.status}${it.check ? ' flag' : ''}${running ? ' running' : ''}" data-item="${it.id}">
    <span class="k">${it.k}</span>
    <div><div class="txt">${esc(it.text)}</div>
      ${it.spoken ? `<div class="read-as" title="What the voice reads: the pronunciation dictionary and numbers as words. Subtitles keep your text.">Read as: ${esc(it.spoken)}</div>` : ''}
      <div class="sub">${chip(running ? 'running' : it.status)}${it.audio_s ? `<span>${it.audio_s.toFixed(1)} s</span>` : ''}${it.duration ? `<span>made in ${it.duration.toFixed(1)} s</span>` : ''}<span>seed ${it.seed}</span>${it.pause_after ? `<span>then ${it.pause_after} s pause</span>` : ''}</div>
      ${it.check ? `<div class="flag-note">${icon('alert')} ${esc(it.check)}</div>` : ''}
      ${it.error ? `<div class="err-note">${esc(it.error)}</div>` : ''}</div>
    <div class="tools">${it.status === 'done' ? player(fileUrl(d.id, it.file, it.finished), { small: true, seconds: it.audio_s }) : ''}
      <div class="row" style="gap:6px">
        <button class="btn xs" data-seg="regen" ${running ? 'disabled' : ''} title="Speak this part again with a new seed">${icon('dice')} New take</button>
        <button class="btn xs" data-seg="edit" ${running ? 'disabled' : ''}>${icon('pencil')} Edit</button>
        ${['failed', 'cancelled'].includes(it.status) ? '<button class="btn xs accent" data-seg="retry">Retry</button>' : ''}</div></div>
  </div>`;
}
function renderDetail() {
  const d = S.detail; if (!d) return;
  $('b-name').textContent = d.name;
  const st = d.settings;
  $('b-meta').innerHTML = `${chip(d.status)} &nbsp;${fmtWhen(d.created)} · ${d.kind === 'singles' ? plural(d.scripts_total, 'quick take') : plural(d.scripts_total, 'script')} · ${d.done}/${d.total} parts`
    + `${d.audio_seconds ? ` · ${fmtDur(d.audio_seconds)} of audio` : ''}${d.eta_seconds ? ` · about ${fmtDur(d.eta_seconds)} left` : ''}`
    + (d.kind === 'singles' ? '' : ` · ${esc(voiceName(st.voice))} · ${esc(langName(st.language))} · seed ${st.seed}`);
  const busy = isBusy(d.status);
  setHtml($('b-actions'), [
    busy && !d.paused ? `<button class="btn sm" data-d="pause">${icon('pause')} Pause</button>` : '',
    d.paused ? `<button class="btn sm accent" data-d="resume">${icon('play')} Resume</button>` : '',
    busy || d.paused ? `<button class="btn sm" data-d="cancel">${icon('stop')} Stop</button>` : '',
    d.failed || d.cancelled ? `<button class="btn sm accent" data-d="retry">${icon('refresh')} Retry</button>` : '',
    d.scripts_done ? `<a class="btn sm" href="/api/batches/${d.id}/export.zip?content=final">${icon('download')} ZIP</a><a class="btn sm" href="/api/batches/${d.id}/export.zip?content=both" title="Finished files plus every part">${icon('download')} ZIP + parts</a>` : '',
    d.kind === 'singles' ? '' : `<button class="btn sm" data-d="output" title="Speed, loudness, files and subtitles — finished scripts are rebuilt, not spoken again">${icon('gauge')} Output</button>`,
    `<button class="btn sm" data-d="open">${icon('folder')} Folder</button>`,
    `<button class="btn sm" data-d="rerun">${icon('refresh')} Re-run</button>`,
    busy ? '' : `<button class="icon-btn" data-d="delete" aria-label="Delete batch">${icon('trash')}</button>`,
  ].join(''));
  const prog = $('b-progress');
  prog.className = `progress${busy ? ' live' : ''}`;
  prog.firstElementChild.style.width = `${100 * d.done / Math.max(1, d.total)}%`;
  const html = d.scripts.map((s) => {
    const items = d.items.filter((it) => it.script === s.n);
    const out = s.output, v = out.finished || '';
    const main = out.files?.mp3 || out.files?.wav;
    const open = S.open.has(s.n) || (!S.closed.has(s.n) && (d.scripts.length === 1 || s.checks || s.failed));
    return `<section class="card scard" data-n="${s.n}">
      <div class="top">${chip(s.status)}<span class="title">${esc(s.title)}</span><span class="stem">${esc(s.stem)}</span>
        <button class="btn xs" data-s="edit">${icon('pencil')} Edit script</button>
        ${d.kind === 'singles' ? `<button class="btn xs" data-s="output" title="Speed, loudness, files and subtitles of this take">${icon('gauge')} Output</button>` : ''}
        ${s.status === 'done' ? `<button class="btn xs" data-s="refinish" title="Rebuild the WAV/MP3/SRT from the parts (after changing loudness or formats in Settings)">${icon('refresh')} Rebuild files</button>` : ''}
        ${d.scripts.length > 1 ? `<button class="icon-btn" data-s="delete" aria-label="Delete script">${icon('trash')}</button>` : ''}</div>
      <div class="info"><span>${esc(s.voice_name || voiceName(s.voice))}</span><span>${esc(langName(s.language))}</span>
        <span>${plural(s.segments, 'part')}</span><span>${s.chars.toLocaleString()} characters</span>
        ${out.seconds ? `<span>${fmtClock(out.seconds)} long</span>` : `<span>about ${fmtDur(s.estimate_s)}</span>`}
        ${out.lufs_before != null ? `<span>levelled to ${st.loudness ?? -16} LUFS</span>` : ''}
        ${out.match != null ? `<span class="${out.match >= 0.95 ? 'good' : out.match >= 0.85 ? 'fair' : 'poor'}" title="Share of the script's words Whisper recognised in the audio">Whisper heard ${Math.round(out.match * 100)}%</span>` : ''}
        ${s.checks ? `<span class="fair">${plural(s.checks, 'part')} to check</span>` : ''}</div>
      ${s.status === 'done' && main ? `<div class="player">${player(fileUrl(d.id, main, v))}
        <div class="files">${Object.entries(out.files).map(([k, f]) => `<a class="btn sm" href="${fileUrl(d.id, f, v, 1)}" download>${icon('download')} ${k.toUpperCase()}</a>`).join('')}</div></div>` : ''}
      ${out.status === 'failed' ? `<p class="err-note">Writing the files failed: ${esc(out.error)}</p>` : ''}
      <details class="segs" ${open ? 'open' : ''} data-n="${s.n}"><summary>Parts (${s.done}/${s.segments})</summary>
        ${items.map((it) => segRow(d, it)).join('')}
      </details></section>`;
  }).join('');
  setHtml($('b-scripts'), html);
}
$('b-scripts').addEventListener('toggle', (e) => {
  const det = e.target.closest?.('details.segs'); if (!det) return;
  const n = Number(det.dataset.n);
  if (det.open) { S.open.add(n); S.closed.delete(n); } else { S.open.delete(n); S.closed.add(n); }
}, true);
$('b-actions').addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-d]'); if (!b) return;
  if (b.dataset.d === 'output') return editOutput();
  await batchAction(S.detail.id, b.dataset.d);
  if (S.view === 'batch') loadDetail();
}));
$('b-rename').addEventListener('click', run(async () => {
  const r = await editDialog({ title: 'Rename batch', help: 'The folder on disk is renamed too.', name: S.detail.name, nameLabel: 'Name', ok: 'Rename' });
  if (!r || !r.name.trim() || r.name.trim() === S.detail.name) return;
  await api(`/api/batches/${S.detail.id}`, { method: 'PATCH', json: { name: r.name.trim() } });
  toast('Renamed.', true); loadDetail();
}));
$('b-scripts').addEventListener('click', run(async (e) => {
  const d = S.detail;
  const sb = e.target.closest('[data-s]');
  if (sb) {
    const n = Number(sb.closest('.scard').dataset.n);
    const s = d.scripts.find((x) => x.n === n);
    if (sb.dataset.s === 'edit') {
      const r = await editDialog({
        title: `Edit script ${n}`, help: 'Only the parts whose text changed are spoken again; the rest keep their audio.',
        name: s.title, text: s.text,
        extra: `<div class="pair"><div class="field"><label class="label">Voice</label><div class="select-wrap"><select class="select" name="voice">${voiceOptions(s.voice)}</select>${icon('chevron')}</div></div>
          <div class="field" style="flex:0 0 160px"><label class="label">Language</label><div class="select-wrap"><select class="select" name="language">${languageOptions(s.language, d.settings?.model)}</select>${icon('chevron')}</div></div></div>
          <p class="help">Changing the voice or language speaks the whole script again.</p>`,
      });
      if (!r) return;
      const body = {};
      if (r.text !== s.text) body.text = r.text;
      if (r.name !== s.title) body.title = r.name;
      if (r.voice !== s.voice) body.voice = r.voice;
      if (r.language !== s.language) body.language = r.language;
      if (!Object.keys(body).length) return;
      S.detail = await api(`/api/batches/${d.id}/scripts/${n}`, { method: 'PATCH', json: body });
      toast('Saved. Changed parts are queued.', true);
    } else if (sb.dataset.s === 'output') {
      return editOutput(n);
    } else if (sb.dataset.s === 'refinish') {
      S.detail = await api(`/api/batches/${d.id}/scripts/${n}/refinish`, { method: 'POST' });
      toast('Rebuilding the files…', true);
    } else if (sb.dataset.s === 'delete') {
      if (!await confirmDialog(`Delete script ${n}?`, 'Its finished files go to the Recycle Bin.')) return;
      S.detail = await api(`/api/batches/${d.id}/scripts/${n}`, { method: 'DELETE' });
    }
    $('b-scripts')._html = ''; renderDetail(); return;
  }
  const gb = e.target.closest('[data-seg]'); if (!gb) return;
  const id = gb.closest('.seg-row').dataset.item;
  const it = d.items.find((x) => x.id === id);
  if (gb.dataset.seg === 'regen') S.detail = await api(`/api/batches/${d.id}/segments/${id}/regenerate`, { method: 'POST', json: { new_seed: true } });
  else if (gb.dataset.seg === 'retry') S.detail = await api(`/api/batches/${d.id}/segments/${id}/retry`, { method: 'POST' });
  else if (gb.dataset.seg === 'edit') {
    const r = await editDialog({ title: `Edit part ${it.k}`, help: 'Fix a word, spell a name the way it sounds, or add punctuation for a pause. This part is spoken again.', text: it.text, rows: 6, ok: 'Save and speak again' });
    if (!r || r.text.trim() === it.text) return;
    S.detail = await api(`/api/batches/${d.id}/segments/${id}`, { method: 'PATCH', json: { text: r.text } });
  }
  $('b-scripts')._html = ''; renderDetail();
}));

// ---------- VOICES ----------
async function loadVoicesList() {
  try { S.voices = await api('/api/voices'); } catch { /* keep the old list */ }
}
async function loadVoices() {
  await loadVoicesList();
  if (!S.settings) S.settings = await api('/api/settings');
  const lang = $('voice-lang').value || S.state?.default_language || 'en';
  $('voice-lang').innerHTML = languageOptions(lang);
  fillFindLang($('find-lang').value || lang);
  separateHelp();
  renderVoiceCards();
}
// A round badge with the voice's initials, in a colour that stays the same for each name.
function avatar(name) {
  const words = String(name || '?').trim().split(/\s+/);
  const initials = (words[0][0] + (words.length > 1 ? words[words.length - 1][0] : '')).toUpperCase();
  let h = 0; for (const c of String(name)) h = (h * 31 + c.codePointAt(0)) % 360;
  return `<span class="avatar" style="--h:${h}" aria-hidden="true">${esc(initials)}</span>`;
}
const emptyCard = (pic, title, text, action = '', style = '') => `<div class="card empty big"${style ? ` style="${style}"` : ''}>
  <span class="pic">${icon(pic)}</span><b>${title}</b><p>${text}</p>${action}</div>`;
function renderVoiceCards() {
  const def = S.settings?.default_voice;
  const html = S.voices.length ? S.voices.map((v) => `
    <section class="card vcard${v.id === def ? ' default' : ''}" data-id="${esc(v.id)}">
      <div class="top">${avatar(v.name)}<div class="who"><span class="name">${esc(v.name)}</span><span class="lang">${esc(langName(v.language))}</span></div>${v.id === def ? '<span class="chip accent">Default</span>' : ''}${v.source === 'found' ? '<span class="chip">Found</span>' : ''}${v.source === 'kokoro' ? '<span class="chip">Kokoro</span>' : ''}</div>
      <div class="meta"><span>${v.seconds} s clip</span>${v.denoised ? '<span>noise reduced</span>' : ''}<span>${fmtWhen(v.created)}</span></div>
      ${v.notes ? `<div class="notes">${esc(v.notes)}</div>` : ''}
      ${player(`/api/voices/${encodeURIComponent(v.id)}/clip?v=${encodeURIComponent(v.seconds + '-' + v.denoised)}`)}
      ${v.advice?.length && v.source !== 'kokoro' ? `<ul class="tips">${v.advice.map((a) => `<li>${esc(a)}</li>`).join('')}</ul>` : ''}
      <div class="preview-slot"></div>
      <div class="acts">
        <button class="btn sm accent" data-v="preview">${icon('speaker')} Hear it speak</button>
        <button class="btn sm" data-v="edit">${icon('pencil')} Edit</button>
        <span class="grow"></span>
        ${v.id === def ? `<span class="icon-btn on" title="The default voice" aria-label="The default voice">${icon('star')}</span>` : `<button class="icon-btn" data-v="default" title="Make default" aria-label="Make default">${icon('star')}</button>`}
        <button class="icon-btn" data-v="delete" title="Delete voice" aria-label="Delete voice">${icon('trash')}</button>
      </div>
    </section>`).join('') : emptyCard('users', 'No voices yet', 'Add a 6–15 second clip of a voice above, or find a brand-new voice that belongs to nobody.', '', 'grid-column:1/-1');
  setHtml($('voice-cards'), html);
}

// Adding a voice from a file
S.voiceFile = null;
function setVoiceFile(f) {
  S.voiceFile = f;
  $('voice-drop-text').innerHTML = f ? `<b>${esc(f.name)}</b><br><small>${fmtSize(f.size)} · click to choose another</small>` : 'Drop an audio file here, or click to choose';
  const p = $('voice-file-preview');
  if (f) { p.innerHTML = player(URL.createObjectURL(f)); p.hidden = false; } else { p.innerHTML = ''; p.hidden = true; }
  if (f && !$('voice-name').value) $('voice-name').value = f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').slice(0, 60);
  checkVoiceForm();
}
function checkVoiceForm() {
  const missing = [!S.voiceFile && 'choose a clip', !$('voice-name').value.trim() && 'give it a name', !$('voice-consent').checked && 'tick the permission box'].filter(Boolean);
  $('voice-add').disabled = missing.length > 0;
  const hint = $('voice-add-hint');
  hint.textContent = missing.length ? `To add it: ${missing.join(', ').replace(/, ([^,]*)$/, ' and $1')}.` : '';
  hint.hidden = !missing.length;
}
$('voice-file').addEventListener('change', (e) => setVoiceFile(e.target.files[0] || null));
['voice-name', 'voice-consent'].forEach((id) => $(id).addEventListener('input', checkVoiceForm));
checkVoiceForm();
$('voice-consent').addEventListener('change', checkVoiceForm);
const drop = $('voice-drop');
['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove('over')));
drop.addEventListener('drop', (e) => { e.preventDefault(); if (e.dataTransfer.files[0]) setVoiceFile(e.dataTransfer.files[0]); });
$('voice-add').addEventListener('click', run(async () => {
  const form = new FormData();
  form.append('file', S.voiceFile); form.append('name', $('voice-name').value.trim());
  form.append('language', $('voice-lang').value); form.append('notes', $('voice-notes').value);
  form.append('denoise', $('voice-denoise').checked ? '1' : '0');
  form.append('separate', $('voice-separate').checked ? '1' : '0');
  $('voice-add').disabled = true;
  $('voice-add').textContent = $('voice-separate').checked ? 'Taking the voice out of the music… (a minute or two for long files)' : 'Preparing the clip…';
  try {
    const v = await api('/api/voices', { method: 'POST', form });
    toast(`Added “${v.name}” (${v.seconds} s clip).${v.advice?.length ? ' ' + v.advice[0] : ''}`, !v.advice?.length);
    setVoiceFile(null); $('voice-file').value = ''; $('voice-name').value = ''; $('voice-notes').value = ''; $('voice-consent').checked = false;
    S.settings = await api('/api/settings');
    await loadVoices();
  } finally { $('voice-add').textContent = 'Add voice'; checkVoiceForm(); }
}));

$('voice-cards').addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-v]'); if (!b) return;
  const card = b.closest('.vcard'), id = card.dataset.id;
  const v = S.voices.find((x) => x.id === id);
  if (b.dataset.v === 'preview') {
    b.disabled = true; b.innerHTML = `${icon('speaker')} Speaking…`;
    try {
      const r = await api(`/api/voices/${encodeURIComponent(id)}/preview`, { method: 'POST', json: {}, raw: true });
      const url = URL.createObjectURL(await r.blob());
      card.querySelector('.preview-slot').innerHTML = `<div class="micro">Sample · ${esc(langName(v.language))}</div>${player(url, { autoplay: true })}`;
    } finally { b.disabled = false; b.innerHTML = `${icon('speaker')} Hear it speak`; }
  } else if (b.dataset.v === 'default') {
    S.settings = await api('/api/settings', { method: 'PUT', json: { default_voice: id } });
    $('voice-cards')._html = ''; renderVoiceCards(); toast(`“${v.name}” is now the default voice.`, true);
  } else if (b.dataset.v === 'delete') {
    if (!await confirmDialog(`Delete “${v.name}”?`, 'Its folder (clip and original file) goes to the Recycle Bin. Finished audio made with it is kept.')) return;
    await api(`/api/voices/${encodeURIComponent(id)}`, { method: 'DELETE' });
    S.settings = await api('/api/settings'); await loadVoices();
  } else if (b.dataset.v === 'edit') {
    // S2 Pro, OmniVoice and MOSS-TTS Nano copy a voice from its clip and the words it says
    const cloners = [...new Set((S.state?.models || []).filter((m) => m.words && m.installed)
      .map((m) => (m.runtime === 's2' ? 'S2 Pro' : m.label.split(' · ')[0])))].join(', ').replace(/, ([^,]*)$/, ' and $1');
    const s2Ready = !!cloners;
    const r = await editDialog({
      title: `Edit “${v.name}”`, name: v.name, nameLabel: 'Name', text: null, ok: 'Save',
      extra: `<div class="pair"><div class="field"><label class="label">Language</label><div class="select-wrap"><select class="select" name="language">${languageOptions(v.language)}</select>${icon('chevron')}</div></div></div>
        <div class="field"><label class="label">Notes</label><input class="input" name="notes" value="${esc(v.notes || '')}"></div>
        ${s2Ready ? `<div class="field"><label class="label">What the clip says <span class="opt">— for ${cloners}</span></label>
          <textarea class="paste" name="transcript" rows="3" style="min-height:70px" placeholder="Heard by Whisper the first time ${cloners} uses this voice">${esc(v.transcript || '')}</textarea>
          <p class="help">${cloners} copies a voice from the clip and these words. Fix any word Whisper got wrong; leave it empty to have it heard again.</p></div>` : ''}
        <hr style="border:0;border-top:1px solid var(--line);width:100%">
        <p class="help">Prepare the clip again from the original file (${v.trimmed_from ?? v.seconds} s):</p>
        <label class="check"><input type="checkbox" name="denoise" ${v.denoised ? 'checked' : ''}> Reduce background noise</label>
        <div class="pair"><div class="field"><label class="label">Use from (seconds)</label><input class="input mono" name="start" type="number" min="0" step="0.1" value="${v.range?.[0] ?? ''}" placeholder="start"></div>
          <div class="field"><label class="label">to (seconds)</label><input class="input mono" name="end" type="number" min="0" step="0.1" value="${v.range?.[1] ?? ''}" placeholder="end"></div></div>
        <p class="help">Pick the cleanest 6–15 seconds of one person talking. Longer clips are cut at a pause after 20 seconds.</p>`,
    });
    if (!r) return;
    await api(`/api/voices/${encodeURIComponent(id)}`, { method: 'PATCH', json: { name: r.name, language: r.language, notes: r.notes, ...(s2Ready ? { transcript: r.transcript ?? '' } : {}) } });
    const range = [r.start === '' ? null : Number(r.start), r.end === '' ? null : Number(r.end)];
    if (r.denoise !== !!v.denoised || String(range) !== String(v.range || [null, null])) {
      await api(`/api/voices/${encodeURIComponent(id)}/prepare`, { method: 'POST', json: { denoise: r.denoise, start: range[0], end: range[1] } });
    }
    await loadVoices(); toast('Saved.', true);
  }
}));

// Find a voice: random new voices to keep
const speaksIt = (m, lang) => m.kind === 'voice' && m.installed && (m.languages || []).includes(lang);
function fillFindLang(selected) {
  // Only languages a downloaded voice model speaks; one without a ready sample sentence asks for one.
  const st = S.state, all = st?.languages || {};
  const codes = Object.keys(all).filter((k) => (st?.models || []).some((m) => speaksIt(m, k)));
  const pick = codes.includes(selected) ? selected : (codes[0] || 'en');
  $('find-lang').innerHTML = codes.map((k) => `<option value="${k}"${k === pick ? ' selected' : ''}>${esc(all[k])}</option>`).join('');
  findLangChanged();
}
function findLangChanged() {
  const lang = $('find-lang').value;
  const own = !(S.state?.sample_languages || []).includes(lang);
  $('find-text-field').hidden = !own;
  $('find-text').placeholder = `A sentence in ${langName(lang)} for the new voices to say`;
}
$('find-lang').addEventListener('change', findLangChanged);
$('find-go').addEventListener('click', run(async () => {
  const n = Number($('find-count').value), lang = $('find-lang').value;
  const text = $('find-text-field').hidden ? '' : $('find-text').value.trim();
  if (!$('find-text-field').hidden && !text) { $('find-text').focus(); throw new Error(`Type a sentence in ${langName(lang)} for the new voices to say.`); }
  const def = (S.state?.models || []).find((m) => m.key === S.state?.default_model);
  const each = def && speaksIt(def, lang) ? 8 : 15;  // S2 Pro (other languages) takes longer
  $('find-go').disabled = true; $('find-go').innerHTML = `${icon('sparkle')} Finding ${n} voices… (about ${n * each} s)`;
  try {
    const found = await api('/api/voices/find', { method: 'POST', json: { language: lang, count: n, ...(text ? { text } : {}) } });
    $('found-list').innerHTML = found.map((f, i) => `
      <div class="found-item" data-token="${f.token}" data-lang="${f.language}">
        <div class="row between"><span class="micro">Voice ${i + 1} · ${esc(langName(f.language))}</span></div>
        ${player(`/api/found/${f.token}`)}
        <div class="row" style="gap:8px"><input class="input" placeholder="Name it to keep it" maxlength="60" style="height:34px"><button class="btn sm accent" data-keep>Keep</button></div>
      </div>`).join('');
  } finally { $('find-go').disabled = false; $('find-go').innerHTML = `${icon('sparkle')} Find voices`; }
}));
$('found-list').addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-keep]'); if (!b) return;
  const item = b.closest('.found-item'), name = item.querySelector('input').value.trim();
  if (!name) { item.querySelector('input').focus(); throw new Error('Give the voice a name first.'); }
  const v = await api('/api/voices/keep', { method: 'POST', json: { token: item.dataset.token, name, language: item.dataset.lang } });
  item.innerHTML = `<span class="chip ok">${icon('check')} Kept as “${esc(v.name)}”</span>`;
  S.settings = await api('/api/settings'); await loadVoices();
}));

// ---------- MODELS ----------
async function loadModels() {
  let models;
  try { models = await api('/api/models'); } catch (e) { toast(e.message); return; }
  const group = (kind, title, help, extra = '') => `<div class="group-title">${title}</div><p class="help" style="margin:-6px 0 12px">${help}</p>${extra}`
    + models.filter((m) => m.kind === kind).map(modelCard).join('');
  const [tools, wg] = await Promise.all([api('/api/tools'), api('/api/whisper-gpu').catch(() => null)]);
  setHtml($('models-list'), group('voice', 'Voice models', 'Speak your scripts. Qwen3-TTS, OmniVoice and the audio.cpp models (Chatterbox, VoxCPM2, CosyVoice 3, Kokoro, MOSS-TTS Nano) run on every engine chosen on the Setup page; S2 Pro on the NVIDIA · CUDA or AMD / Intel · Vulkan engine.')
    + group('subtitles', 'Subtitles and transcripts', 'Time the SRT subtitles of every finished script, and power the Transcribe page and the transcription API. They run on your graphics card with a CUDA or Vulkan engine, otherwise on the processor.', whisperWhere(wg, models.some((m) => m.kind === 'subtitles' && m.installed)))
    + group('separation', 'Voice separator', 'Takes a voice out of music or background sound when you add a voice from a video or a song.')
    + `<div class="group-title">Tools</div><p class="help" style="margin:-6px 0 12px">Programs the app uses for some file types.</p>`
    + tools.map(toolCard).join(''));
  const busy = (j) => j && ['downloading', 'checking', 'installing'].includes(j.status);
  if (models.some((m) => busy(m.job)) || tools.some((t) => busy(t.job)) || busy(wg?.job)) setTimeout(() => S.view === 'models' && loadModels(), 1000);
}
// Where Whisper runs, under the subtitles models: on the graphics card of the voice engine in use (its build comes
// by itself once there's a Whisper model), or on the processor.
function whisperWhere(wg, haveModel) {
  const line = (html) => `<div class="whisper-where">${html}</div>`;
  if (!wg) return line(`${icon('cpu')}<span>Whisper runs on the <b>processor</b>. With a graphics card engine on <a href="#setup">Setup</a> (CUDA or Vulkan) it runs on the card, many times faster.</span>`);
  const j = wg.job;
  if (j && ['downloading', 'checking', 'installing'].includes(j.status)) {
    const pct = j.total ? Math.min(100, 100 * j.done / j.total) : 0;
    const label = j.status === 'downloading' ? `${fmtSize(j.done)} of ${fmtSize(j.total)}` : j.status === 'checking' ? 'Checking…' : 'Installing…';
    return line(`${icon('download')}<span style="flex:1">Getting Whisper ready for your graphics card (${esc(wg.label)}) · ${label}<div class="progress live" style="margin-top:6px"><div style="width:${pct}%"></div></div></span><button class="text-btn red" data-wg="cancel">Pause</button>`);
  }
  if (wg.ready) return line(`${icon('check')}<span>Whisper runs on your <b>graphics card</b> (${esc(wg.label)}), whichever model you pick. Large-v3 turbo is the most accurate there, and quick.</span>`);
  if (j && ['failed', 'cancelled'].includes(j.status)) {
    return line(`${icon('alert')}<span style="flex:1">${j.status === 'failed' ? `Whisper's graphics card part didn't download: ${esc(j.error || '')}` : 'Paused.'} Until then it runs on the processor.</span><button class="btn sm" data-wg="retry">${icon('refresh')} ${j.status === 'failed' ? 'Try again' : 'Resume'}</button>`);
  }
  return line(`${icon('cpu')}<span>${haveModel ? 'Whisper runs on the processor for now.' : 'Download a Whisper model:'} It will run on your <b>graphics card</b> (${esc(wg.label)}), with a one-time ${fmtSize(wg.size - (wg.partial || 0))} download that starts by itself.</span>`);
}
document.addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-wg]'); if (!b) return;
  await api(`/api/whisper-gpu/${b.dataset.wg}`, { method: 'POST' });
  setTimeout(() => (S.view === 'setup' ? loadSetup() : loadModels()), 300);
}));
function dlBox(job, total, partial, kind, key) {
  if (job && ['downloading', 'checking', 'installing'].includes(job.status)) {
    const pct = job.total ? Math.min(100, 100 * job.done / job.total) : 0;
    const label = job.status === 'checking' ? 'Checking the download…' : job.status === 'installing' ? 'Installing…' : `${fmtSize(job.done)} of ${fmtSize(job.total)}`;
    return `<div class="dl"><div class="progress live"><div style="width:${pct}%"></div></div><div class="row between"><span class="micro">${label}</span><button class="text-btn red" data-${kind}="cancel" data-key="${key}">Pause</button></div></div>`;
  }
  return '';
}
function toolCard(t) {
  const busy = t.job && ['downloading', 'checking', 'installing'].includes(t.job.status);
  let acts;
  if (busy) acts = dlBox(t.job, t.size, t.partial, 't', t.key);
  else if (t.installed) acts = `<span class="chip ok">${icon('check')} Downloaded</span><button class="btn sm" data-t="remove" data-key="${t.key}">Remove</button>`;
  else if (t.on_pc) acts = `<span class="chip ok">${icon('check')} Already on this PC</span>`;
  else acts = `<button class="btn sm accent" data-t="download" data-key="${t.key}">${icon('download')} Download ${fmtSize(t.size - t.partial)}</button>`;
  return `<div class="card mcard"><div class="main"><div class="name">${esc(t.label)} <span class="license ok">${esc(t.license)}</span></div>
      <div class="about">${esc(t.about)}</div>${t.job?.status === 'failed' ? `<div class="err-note">${esc(t.job.error)}</div>` : ''}</div>
    <div class="acts">${acts}</div></div>`;
}
document.addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-t]'); if (!b) return;
  if (b.dataset.t === 'remove' && !await confirmDialog('Remove ffmpeg?', 'Video files can no longer be read until you download it again.', 'Remove')) return;
  await api(`/api/tools/${b.dataset.key}/${b.dataset.t}`, { method: 'POST' });
  setTimeout(loadModels, 300);
}));

// Voice models to pick from: all of them (S2 Pro and OmniVoice show their own limits on Models and when they can't run).
const speakable = (m) => m.kind === 'voice';
function modelCard(m) {
  const busy = m.job && ['downloading', 'checking', 'installing'].includes(m.job.status);
  let acts;
  if (busy) acts = dlBox(m.job, m.to_download, m.partial, 'm', m.key);
  else if (m.installed && m.kind === 'subtitles') acts = (m.in_use ? `<span class="chip ok">${icon('check')} In use</span>`
    : `<span class="chip">Downloaded</span><button class="btn sm accent" data-m="use" data-key="${m.key}">Use this one</button>`)
    + `<button class="btn sm" data-m="remove" data-key="${m.key}">Remove</button>`;
  else if (m.installed && m.runtime_job && ['downloading', 'checking', 'installing'].includes(m.runtime_job.status)) acts = dlBox(m.runtime_job, 0, 0, 'm', m.key);
  else if (m.installed) acts = `<span class="chip ok">${icon('check')} Downloaded</span><button class="btn sm" data-m="remove" data-key="${m.key}">Remove</button>`;
  else if (!m.engine_ok) acts = `<span class="help" style="max-width:240px;text-align:right">${m.runtime === 's2' ? 'Needs the NVIDIA · CUDA or AMD / Intel · Vulkan engine (<a href="#setup">Setup</a>)' : `${esc(m.engine_note)} (<a href="#setup">Setup</a>)`}</span>`;
  else if (m.partial) acts = `<button class="btn sm accent" data-m="download" data-key="${m.key}">${icon('download')} Resume (${fmtSize(m.partial)} done)</button><button class="text-btn red" data-m="discard" data-key="${m.key}">Discard</button>`;
  else acts = `<button class="btn sm accent" data-m="download" data-key="${m.key}">${icon('download')} Download ${fmtSize(m.to_download)}</button>`;
  return `<div class="card mcard"><div class="main">
      <div class="name">${esc(m.label)} ${licenseBadge(m)}${m.default ? '<span class="chip accent">Default</span>' : ''}${m.recommended && !m.installed ? '<span class="chip dark">Recommended</span>' : ''}</div>
      <div class="about">${esc(m.about)}</div>
      <div class="meta"><span>${fmtSize(m.size)}</span>${m.shared?.length ? `<span>shares ${plural(m.shared.length, 'file')} with other models (downloaded once)</span>` : ''}<a href="${esc(m.page)}" target="_blank" rel="noopener">Model page ↗</a>${m.fit && !['fits', 'cpu', 'unsupported'].includes(m.fit) ? `<span style="color:var(--warn)">${m.fit === 'tight' ? 'tight fit for your GPU' : 'too big for your GPU'}</span>` : ''}${m.runtime === 's2' && S.state?.engine?.engine === 'vulkan' ? '<span style="color:var(--warn)">slower on Vulkan (about 1.5× slower than real time)</span>' : ''}${m.runtime === 'omni' && S.state?.engine?.engine === 'cpu' ? '<span style="color:var(--warn)">on the processor: 2–3× slower than real time</span>' : ''}${m.key === 'chatterbox' && S.state?.engine?.engine === 'cpu' ? '<span style="color:var(--warn)">on the processor: about 10× slower than real time</span>' : ''}</div>
      ${m.installed && !m.runtime_ready && m.engine_ok && !(m.runtime_job && ['downloading', 'checking', 'installing'].includes(m.runtime_job.status)) ? `<div class="err-note">${m.runtime_job?.status === 'failed' ? `Its ${m.runtime_part || 'engine'} part didn't download: ${esc(m.runtime_job.error || '')}` : m.runtime_part === 'pronunciation' ? 'Its pronunciation part (eSpeak NG) is missing.' : 'Its engine part for this graphics card is missing.'} <button class="btn xs" data-m="download" data-key="${m.key}">${icon('download')} Get it</button></div>` : ''}
      ${m.installed && !m.engine_ok ? (m.runtime === 's2' ? '<div class="err-note">Needs the NVIDIA · CUDA or AMD / Intel · Vulkan engine: switch to one on Setup.</div>' : `<div class="err-note">${esc(m.engine_note)}: switch to another engine on Setup.</div>`) : ''}
      ${m.job?.status === 'failed' ? `<div class="err-note">${esc(m.job.error)}</div>` : ''}
    </div><div class="acts">${acts}</div></div>`;
}
document.addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-m]'); if (!b) return;
  const key = b.dataset.key, act = b.dataset.m;
  if (act === 'download') await api(`/api/models/${key}/download`, { method: 'POST' });
  else if (act === 'cancel') await api(`/api/models/${key}/cancel`, { method: 'POST' });
  else if (act === 'discard') { if (!await confirmDialog('Discard the paused download?', 'The part already downloaded is deleted.', 'Discard')) return; await api(`/api/models/${key}/partial`, { method: 'DELETE' }); }
  else if (act === 'use') { S.settings = await api('/api/settings', { method: 'PUT', json: { subtitles_model: key } }); toast('Subtitles and transcripts now use this model.', true); }
  else if (act === 'remove') { if (!await confirmDialog('Remove this model?', 'Its files are deleted from this PC. You can download it again any time.', 'Remove')) return; await api(`/api/models/${key}`, { method: 'DELETE' }); }
  setTimeout(() => (S.view === 'setup' ? loadSetup() : loadModels()), 300);
}));

// ---------- SETUP ----------
async function loadSetup(refresh = false) {
  let s;
  try { s = await api(`/api/setup${refresh ? '?refresh=1' : ''}`); } catch (e) { toast(e.message); return; }
  S.setupBench = s.benchmark;
  const hw = s.hardware, g = s.gpu;
  const locked = document.body.classList.contains('locked');
  $('setup-lede').textContent = locked ? 'Welcome! Two downloads and you\'re ready: the engine that runs the voices, and a voice model. The ones that suit this PC are marked Recommended.'
    : 'What this PC has, and the engine and models that suit it.';
  const stepHead = (n, done, title, text) => `<div class="step${done ? ' done' : ''}"><span class="n">${done ? '✓' : n}</span><div><h2>${title}</h2><p>${text}</p></div></div>`;
  const engines = s.engines.map((e) => {
    const busy = e.job && ['downloading', 'checking', 'installing'].includes(e.job.status);
    let acts;
    if (busy) acts = dlBox(e.job, e.size, e.partial, 'e', e.key);
    else if (e.active) acts = `<span class="chip ok">${icon('check')} In use</span>`;
    else if (e.installed) acts = `<button class="btn sm accent" data-e="use" data-key="${e.key}">Use this one</button><button class="btn sm" data-e="remove" data-key="${e.key}">Remove</button>`;
    else if (e.partial) acts = `<button class="btn sm accent" data-e="download" data-key="${e.key}">Resume (${fmtSize(e.partial)} done)</button><button class="text-btn red" data-e="discard" data-key="${e.key}">Discard</button>`;
    else acts = `<button class="btn sm ${e.recommended ? 'accent' : ''}" data-e="download" data-key="${e.key}">${icon('download')} Download ${fmtSize(e.size)}</button>`;
    return `<div class="card mcard"><div class="main"><div class="name">${esc(e.label)}${e.recommended ? '<span class="chip dark">Recommended</span>' : ''}</div>
      <div class="about">${esc(e.about)}</div>${e.job?.status === 'failed' ? `<div class="err-note">${esc(e.job.error)}</div>` : ''}</div><div class="acts">${acts}</div></div>`;
  }).join('');
  const voiceModels = s.models.filter((m) => m.kind === 'voice').map(modelCard).join('');
  const subModels = s.models.filter((m) => m.kind === 'subtitles').map(modelCard).join('');
  const b = s.benchmark;
  const html = `
    <div class="card hw">
      <div><div class="k">Graphics card</div><div class="v">${esc(g ? g.name : 'None found')}</div><small>${g ? `${g.vram_gb} GB${g.driver ? ` · driver ${esc(g.driver)}` : ''}` : 'Speech runs on the CPU'}</small></div>
      <div><div class="k">Memory</div><div class="v">${hw.ram_gb} GB RAM</div></div>
      <div><div class="k">Processor</div><div class="v">${esc(hw.cpu)}</div><small>${hw.cores} threads</small></div>
      <div><div class="k">Free disk (models)</div><div class="v">${s.disk_free != null ? fmtSize(s.disk_free) : '—'}</div></div>
    </div>
    ${s.warnings.map((w) => `<div class="warn-box ${w.level}">${icon('alert')}<span>${esc(w.message)}</span></div>`).join('')}
    ${stepHead(1, s.steps.engine, 'Engine', `llama.cpp ${esc(s.engine_release)}, the official build. Pick the one for your graphics card.`)}
    ${engines}
    ${stepHead(2, s.steps.model, 'Voice model', 'Speaks your scripts. Both versions are free for commercial use.')}
    ${voiceModels}
    ${stepHead(3, s.steps.subtitles, 'Subtitles <span class="opt" style="font-weight:400;font-size:14px;color:var(--muted)">— recommended</span>', s.whisper_gpu ? 'Times the SRT subtitles for your videos.'
      : 'Times the SRT subtitles for your videos. Small is plenty for subtitles; the bigger ones are more accurate for transcribing other audio.')}
    ${whisperWhere(s.whisper_gpu, s.models.some((m) => m.kind === 'subtitles' && m.installed))}
    ${subModels}
    ${stepHead(4, s.steps.voice, 'A voice', s.steps.voice ? 'You have voices in your library.' : 'Add a 6–15 second clip of a voice, or find a new one.')}
    ${s.ready ? `<a class="btn ${s.steps.voice ? '' : 'accent'}" href="#voices">${icon('users')} Open Voices</a>` : '<p class="help">Available once the engine and a voice model are downloaded.</p>'}
    ${stepHead(5, s.steps.benchmark, 'Speed test', 'Speaks a short paragraph to measure how fast this PC is.')}
    <div class="card bench">${b ? `<div><div class="big">${b.x_realtime}×</div><small>faster than real time</small></div>
      <div class="kv"><span class="k">Paragraph</span><span>${b.audio_s} s of speech in ${b.took_s} s</span><span class="k">Engine</span><span>${esc(b.engine)} · ${esc(b.model)}</span>
      <span class="k">10-min script</span><span>about ${fmtDur(600 / b.x_realtime + 30)}</span></div>` : '<p class="help" style="flex:1">Not tested yet.</p>'}
      <button class="btn ${b ? '' : 'accent'}" id="bench-go" ${s.ready ? '' : 'disabled'}>${icon('play')} ${b ? 'Test again' : 'Run speed test'}</button></div>`;
  setHtml($('setup-body'), html);
  const busy = s.engines.some((e) => e.job && ['downloading', 'checking', 'installing'].includes(e.job.status))
    || s.models.some((m) => m.job && ['downloading', 'checking', 'installing'].includes(m.job.status))
    || ['downloading', 'checking', 'installing'].includes(s.whisper_gpu?.job?.status);
  if (busy) setTimeout(() => S.view === 'setup' && loadSetup(), 1000);
}
$('setup-refresh').addEventListener('click', () => loadSetup(true));
document.addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-e]'); if (!b) return;
  const act = b.dataset.e;
  if (act === 'remove' && !await confirmDialog('Remove this engine?', 'Its files are deleted. You can download it again any time.', 'Remove')) return;
  if (act === 'discard' && !await confirmDialog('Discard the paused download?', 'The part already downloaded is deleted.', 'Discard')) return;
  await api(`/api/setup/engines/${b.dataset.key}/${act}`, { method: 'POST' });
  setTimeout(() => { loadSetup(); pollState(); }, 300);
}));
$('setup-body').addEventListener('click', run(async (e) => {
  if (!e.target.closest('#bench-go')) return;
  const btn = e.target.closest('#bench-go');
  btn.disabled = true; btn.textContent = 'Testing… (about 20 seconds)';
  try { await api('/api/setup/benchmark', { method: 'POST' }); } finally { $('setup-body')._html = ''; loadSetup(); }
}));

// ---------- CONNECT ----------
async function loadConnect() {
  S.settings = await api('/api/settings');
  const s = S.settings, base = S.state.api_base, key = s.api_key, port = s.port;
  const voice = S.voices[0]?.name || 'Narrator';
  const code = (text) => `<div class="code"><button class="icon-btn copy" data-copy="${esc(text)}" aria-label="Copy">${icon('copy')}</button>${esc(text)}</div>`;
  const tabs = {
    claude: `claude mcp add --scope user --transport http fatima-voice-studio http://127.0.0.1:${port}/mcp --header "Authorization: Bearer ${key}"`,
    codex: `# ~/.codex/config.toml\n[mcp_servers.fatima-voice-studio]\nurl = "http://127.0.0.1:${port}/mcp"\nhttp_headers = { "Authorization" = "Bearer ${key}" }`,
    antigravity: `// ~/.gemini/config/mcp_config.json\n{ "mcpServers": { "fatima-voice-studio": { "serverUrl": "http://127.0.0.1:${port}/mcp",\n    "headers": { "Authorization": "Bearer ${key}" } } } }`,
    hermes: `# ~/.hermes/config.yaml\nmcp_servers:\n  fatima-voice-studio:\n    url: "http://127.0.0.1:${port}/mcp"\n    headers:\n      Authorization: "Bearer ${key}"\n    timeout: 1800`,
    stdio: `command: ${s.python_exe}\nargs: ["${s.mcp_script.replace(/\\/g, '\\\\')}"]`,
  };
  const tab = S.connectTab || 'claude';
  const html = `<div class="settings-grid">
    <section class="card panel"><h2>OpenAI-compatible API</h2>
      <p class="help">Any app that can use OpenAI's text-to-speech can use this PC instead: point it at the address below with the key. <span class="mono">voice</span> is a name from your voice library.</p>
      <div class="kv"><span class="k">Base URL</span><span class="mono">${esc(base)}</span><span class="k">API key</span><span class="row" style="gap:6px"><span class="mono" id="key-text">${esc(key.slice(0, 12))}…</span><button class="icon-btn" data-copy="${esc(key)}" aria-label="Copy key">${icon('copy')}</button></span></div>
      ${code(`curl ${base}/audio/speech \\\n  -H "Authorization: Bearer ${key}" -H "Content-Type: application/json" \\\n  -d '{"input": "Hello from my own PC.", "voice": "${voice}", "response_format": "mp3"}' \\\n  -o hello.mp3`)}
      ${code(`from openai import OpenAI\nclient = OpenAI(base_url="${base}", api_key="${key}")\nclient.audio.speech.create(model="qwen3-tts", voice="${voice}", input="Hello!").write_to_file("hello.mp3")`)}
      <table class="plain"><tr><th>Endpoint</th><th>What it does</th></tr>
        <tr><td class="mono">POST /v1/audio/speech</td><td>Text to speech (mp3, wav, flac, pcm). Extras: <span class="mono">language</span>, <span class="mono">seed</span>. Any length; long text is split and joined.</td></tr>
        <tr><td class="mono">POST /v1/audio/transcriptions</td><td>Speech to text with Whisper (json, text, srt, vtt, verbose_json).</td></tr>
        <tr><td class="mono">GET /v1/audio/voices</td><td>Your voice library.</td></tr>
        <tr><td class="mono">GET /v1/models</td><td>Installed models.</td></tr></table>
      <p class="help">Interactive docs: <a href="/docs" target="_blank">/docs</a>. Requests go ahead of batches. The API only listens on this PC (127.0.0.1).</p>
    </section>
    <section class="card panel"><h2>AI agents (MCP)</h2>
      <p class="help">Let Claude Code, Codex, Antigravity, Hermes or any MCP agent make voiceovers: list voices, start batches, wait, fix parts, export. The studio must be running.</p>
      <div class="tabs">${Object.keys(tabs).map((t) => `<button type="button" data-tab="${t}" aria-pressed="${t === tab}">${{ claude: 'Claude Code', codex: 'Codex', antigravity: 'Antigravity', hermes: 'Hermes', stdio: 'Other (stdio)' }[t]}</button>`).join('')}</div>
      ${code(tabs[tab])}
      <h2 style="margin-top:8px">Guard rails</h2>
      <p class="help">Agents can't download models or delete anything. They only write to the Exports folder (<span class="mono">${esc(s.exports_dir)}</span>), and only read voice clips and script files from these folders (plus Batches and Exports):</p>
      <textarea class="paste mono" id="agent-dirs" rows="4" style="font-size:12px">${esc(s.agent_read_dirs.join('\n'))}</textarea>
      <label class="check"><input type="checkbox" id="agent-nc" ${s.agents_noncommercial ? 'checked' : ''}> Let agents use non-commercial models (none installed by default)</label>
      <button class="btn sm" id="agent-save">Save guard rails</button>
    </section></div>`;
  setHtml($('connect-body'), html);
}
document.addEventListener('click', run(async (e) => {
  const c = e.target.closest('[data-copy]');
  if (c) { await copyText(c.dataset.copy); toast('Copied.', true); return; }
  const t = e.target.closest('[data-tab]');
  if (t) { S.connectTab = t.dataset.tab; $('connect-body')._html = ''; loadConnect(); return; }
  if (e.target.closest('#agent-save')) {
    const dirs = $('agent-dirs').value.split('\n').map((x) => x.trim()).filter(Boolean);
    S.settings = await api('/api/settings', { method: 'PUT', json: { agent_read_dirs: dirs, agents_noncommercial: $('agent-nc').checked } });
    toast('Saved.', true);
  }
}));

// ---------- SETTINGS ----------
async function loadSettings() {
  const [settings] = await Promise.all([api('/api/settings'), loadVoicesList()]);
  S.settings = settings;
  const s = S.settings, st = S.state;
  const pathRow = (key, label, help) => `<div class="field"><label class="label">${label}</label><div class="path-row"><input class="input" data-set="${key}" value="${esc(s[key])}" title="${esc(s[key])}"><button class="btn sm" data-browse="${key}">Browse</button><button class="btn sm" data-open-folder="${key.replace('_dir', '')}" title="Open in File Explorer" aria-label="Open in File Explorer">${icon('folder')}</button></div>${help ? `<p class="help">${help}</p>` : ''}</div>`;
  const html = `<div class="settings-cols">
    <div class="settings-stack">
    <section class="card panel"><h2>Defaults for new scripts</h2>
      <div class="field"><label class="label">Voice</label><div class="select-wrap"><select class="select" data-set="default_voice">${voiceOptions(s.default_voice, { blank: 'None' })}</select>${icon('chevron')}</div></div>
      <div class="pair"><div class="field"><label class="label">Language</label><div class="select-wrap"><select class="select" data-set="default_language">${languageOptions(s.default_language, s.default_model)}</select>${icon('chevron')}</div></div>
        <div class="field"><label class="label">Voice model</label><div class="select-wrap"><select class="select" data-set="default_model">${st.models.filter(speakable).map((m) => `<option value="${m.key}"${m.key === s.default_model ? ' selected' : ''}>${esc(m.label)}${m.installed ? '' : ' (not downloaded)'}</option>`).join('')}</select>${icon('chevron')}</div></div></div>
    </section>
    <section class="card panel"><h2>Speech</h2>
      <div class="pair"><div class="field"><label class="label">Speed</label><div class="select-wrap"><select class="select" data-set="speed">${[0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15, 1.2].map((v) => `<option value="${v}"${Math.abs(v - (s.speed || 1)) < 0.001 ? ' selected' : ''}>${v}×${v === 1 ? ' natural' : ''}</option>`).join('')}</select>${icon('chevron')}</div></div>
        <div class="field" style="justify-content:flex-end"><label class="switch" style="height:42px"><input type="checkbox" data-set="spell_numbers" ${s.spell_numbers ? 'checked' : ''}> Say numbers as words</label></div></div>
      <div class="pair"><div class="field"><label class="label">Pause between paragraphs (s)</label><input class="input mono" type="number" step="0.1" min="0" max="10" data-set="pause_paragraph" value="${s.pause_paragraph}"></div>
        <div class="field"><label class="label">Pause inside a paragraph (s)</label><input class="input mono" type="number" step="0.05" min="0" max="5" data-set="pause_segment" value="${s.pause_segment}"></div></div>
      <div class="field"><label class="label">Longest part (characters)</label><input class="input mono" type="number" step="50" min="150" max="1200" data-set="max_chars" value="${s.max_chars}"><p class="help">Text is spoken in parts of up to this length (about ${Math.round(s.max_chars / 14)} s). Shorter parts are quicker to redo; longer ones flow more.</p></div>
    </section>
    </div>
    <div class="settings-stack">
    <section class="card panel"><h2>Files</h2>
      <div class="field"><span class="label">Files for each finished script</span><div class="checks">
        <label><input type="checkbox" data-fmt="wav" ${s.formats.includes('wav') ? 'checked' : ''}> WAV</label>
        <label><input type="checkbox" data-fmt="mp3" ${s.formats.includes('mp3') ? 'checked' : ''}> MP3</label>
        <label><input type="checkbox" data-set="subtitles" ${s.subtitles ? 'checked' : ''}> Subtitles (SRT)</label></div></div>
      <div class="field"><label class="label">Whisper model (subtitles and transcripts)</label><div class="select-wrap"><select class="select" data-set="subtitles_model"><option value=""${s.subtitles_model ? '' : ' selected'}>Best one downloaded</option>${st.models.filter((m) => m.kind === 'subtitles').map((m) => `<option value="${m.key}"${m.key === s.subtitles_model ? ' selected' : ''}${m.installed ? '' : ' disabled'}>${esc(m.label)}${m.installed ? '' : ' (not downloaded)'}</option>`).join('')}</select>${icon('chevron')}</div></div>
      <div class="pair"><div class="field"><label class="label">Loudness (LUFS)</label><input class="input mono" type="number" step="0.5" min="-30" max="-9" data-set="loudness" value="${s.loudness}"><p class="help">−16 suits voiceovers; YouTube plays at about −14.</p></div>
        <div class="field"><label class="label">MP3 quality (kbps)</label><div class="select-wrap"><select class="select" data-set="mp3_bitrate">${[96, 128, 160, 192, 256].map((k) => `<option${k === s.mp3_bitrate ? ' selected' : ''}>${k}</option>`).join('')}</select>${icon('chevron')}</div></div></div>
    </section>
    <section class="card panel"><h2>Folders</h2>
      ${pathRow('batches_dir', 'Batches', 'Every batch is a folder in here.')}
      ${pathRow('exports_dir', 'Exports', 'Where AI agents save exports.')}
      <div class="row wrap"><button class="btn sm" data-open-folder="voices">${icon('folder')} Voices</button><button class="btn sm" data-open-folder="models">${icon('folder')} Models</button><button class="btn sm" data-open-folder="logs">${icon('folder')} Logs</button></div>
    </section>
    </div>
    <div class="settings-stack">
    <section class="card panel"><h2>App</h2>
      <div class="field"><label class="label">Appearance</label><div class="seg" role="group" aria-label="Appearance">${[['', 'Same as Windows'], ['light', 'Light'], ['dark', 'Dark']].map(([k, label]) => `<button type="button" data-theme-pick="${k}" aria-pressed="${themePick() === k}">${label}</button>`).join('')}</div></div>
      <label class="switch"><input type="checkbox" data-set="start_with_windows" ${s.start_with_windows ? 'checked' : ''}> Start with Windows (in the tray)</label>
      <label class="switch"><input type="checkbox" data-set="notify" ${s.notify ? 'checked' : ''}> Windows notification when a batch finishes</label>
      <div class="pair"><div class="field"><label class="label">Port</label><input class="input mono" type="number" data-set="port" value="${s.port}"><p class="help">Applies after a restart.</p></div>
        <div class="field"><label class="label">API key</label><input class="input mono" data-set="api_key" value="${esc(s.api_key)}"></div></div>
      <div class="field"><label class="label">Hugging Face token <span class="opt">— optional</span></label><input class="input mono" type="password" data-set="hf_token" placeholder="${s.hf_token_set ? 'Set (type to replace, clear to remove)' : 'Not needed for the models here'}"></div>
    </section>
    </div></div>`;
  setHtml($('settings-body'), html);
}
// About → Updates: what's new in plain words, what each button does, and nothing from the download page.
function updatesPanel(s, upd) {
  const st = upd?.status;
  const checked = upd?.checked ? `Checked ${new Date(upd.checked * 1000).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}` : 'Not checked yet';
  let body = '';
  if (st === 'available' || st === 'downloading' || st === 'applying') {
    const several = (upd.whats_new || []).length > 1;  // skipped versions: label each one
    const news = (upd.whats_new || []).map((v) => `<div class="upd-ver">${several ? `<span class="micro">Version ${esc(v.version)}</span>` : ''}<ul>${v.items.map((i) => `<li>${esc(i)}</li>`).join('')}</ul></div>`).join('');
    const opt = (kind, name, item, what) => item ? `<div class="upd-opt"><div class="row between"><b>${name}</b><span class="micro">${fmtSize(item.size)}</span></div><p class="help">${what}</p></div>` : '';
    body = `<div class="upd-new"><div class="upd-head"><span class="upd-tag">New</span><b>Version ${esc(upd.latest)} is ready</b></div>
        ${news ? `<div class="upd-news">${news}</div>` : ''}
        ${upd.url ? `<a class="help-link" href="${esc(upd.url)}" target="_blank">Release page on GitHub</a>` : ''}</div>`;
    if (!s.installed) { /* source copies: the note under the buttons says how */ }
    else if (st === 'downloading') {
      const p = upd.progress || {};
      const pct = p.total ? Math.round(100 * p.done / p.total) : 0;
      body += `<div class="upd-progress"><div style="width:${pct}%"></div></div><p class="help">Downloading… ${pct}%. The app restarts by itself when it's done.</p>`;
    } else if (st === 'applying') body += '<p class="help">Installing… the app restarts by itself.</p>';
    else {
      body += `<div class="upd-opts">
          ${upd.quick_ok ? opt('quick', 'Quick update', upd.app, 'Replaces the app\'s own files. Takes a few seconds.') : ''}
          ${opt('full', 'Full update', upd.full, `Downloads the new installer and runs it. Takes about a minute.${upd.quick_ok ? '' : ' This version also updates the parts the app runs on, so it needs the full update.'}`)}
        </div>
        <p class="help">Your voices, models, settings and audio are kept. The app closes and starts again by itself.</p>
        <div class="row wrap">${upd.quick_ok ? '<button class="btn accent sm" data-update="quick">Quick update</button>' : ''}<button class="btn sm ${upd.quick_ok ? '' : 'accent'}" data-update="full">Full update</button></div>`;
    }
  } else if (st === 'manual' && upd.url) {
    body = `<p class="help">Version ${esc(upd.latest)} is out: <a href="${esc(upd.url)}" target="_blank">download it from GitHub</a>.</p>`;
  } else if (st === 'up_to_date') {
    body = '<p class="upd-ok">You have the latest version.</p>';
  } else if (st === 'checking') {
    body = '<p class="help">Checking…</p>';
  }
  return `<section class="card panel" id="about-updates"><h2>Updates</h2>
      ${body}
      ${upd?.error ? `<p class="err-note">${esc(upd.error)}</p>` : ''}
      <div class="row wrap"><button class="btn sm" data-update="check">${icon('refresh')} Check now</button>
        <label class="switch"><input type="checkbox" data-set="check_updates" ${s.check_updates ? 'checked' : ''}> Check automatically</label></div>
      <p class="help">${checked}.${s.installed ? '' : ' Running from source: updates come from git, not from here.'}</p>
    </section>`;
}
$('settings-body').addEventListener('change', run(async (e) => {
  const el = e.target;
  let body = null;
  if (el.dataset.set) body = { [el.dataset.set]: el.type === 'checkbox' ? el.checked : (el.type === 'number' ? Number(el.value) : el.value) };
  if (el.dataset.fmt) body = { formats: [...document.querySelectorAll('[data-fmt]')].filter((x) => x.checked).map((x) => x.dataset.fmt) };
  if (!body) return;
  const r = await api('/api/settings', { method: 'PUT', json: body });
  S.settings = r;
  const ls = document.querySelector('[data-set="default_language"]');
  if (el.dataset.set === 'default_model' && ls) {  // only what the new default model speaks
    ls.innerHTML = languageOptions(r.default_language, r.default_model);
    if (ls.value !== r.default_language) S.settings = await api('/api/settings', { method: 'PUT', json: { default_language: ls.value } });
  }
  toast(r.restart_needed ? 'Saved. Restart the app to use the new port.' : 'Saved.', true);
}));
$('settings-body').addEventListener('click', run(async (e) => {
  const tp = e.target.closest('[data-theme-pick]');
  if (tp) { setTheme(tp.dataset.themePick); document.querySelectorAll('[data-theme-pick]').forEach((b) => b.setAttribute('aria-pressed', b === tp)); return; }
  const br = e.target.closest('[data-browse]');
  if (br) {
    const key = br.dataset.browse;
    const r = await api('/api/browse-folder', { method: 'POST', json: { start: S.settings[key] } });
    if (r.path) { S.settings = await api('/api/settings', { method: 'PUT', json: { [key]: r.path } }); $('settings-body')._html = ''; loadSettings(); toast('Saved.', true); }
    return;
  }
}));

// ---------- channel presets (Create) ----------
S.presets = [];
async function loadPresets() {
  try { S.presets = await api('/api/presets'); } catch { return; }
  const keep = $('preset').value;
  $('preset').innerHTML = '<option value="">No preset</option>' + S.presets.map((p) => `<option value="${esc(p.id)}"${p.id === keep ? ' selected' : ''}>${esc(p.name)}</option>`).join('');
  $('preset-delete').hidden = !$('preset').value;
}
function applyPreset(p) {
  const s = p.settings;
  if (s.voice) $('voice').value = s.voice;
  if (s.model) $('model').value = s.model;  // first: the language list follows the model
  if (s.language) { $('language').innerHTML = languageOptions(s.language, createModel()); $('language').value = s.language; $('language').dataset.touched = '1'; }
  if (s.speed != null) { setSelect($('speed'), s.speed); $('speed').dataset.touched = '1'; }
  if (s.loudness != null) { setSelect($('loudness'), s.loudness); $('loudness').dataset.touched = '1'; }
  if (s.formats) { $('fmt-wav').checked = s.formats.includes('wav'); $('fmt-mp3').checked = s.formats.includes('mp3'); $('fmt-wav').dataset.touched = '1'; }
  if (s.subtitles != null) { $('opt-srt').checked = s.subtitles; $('opt-srt').dataset.touched = '1'; }
  if (s.pause_paragraph != null) $('pause-paragraph').value = s.pause_paragraph;
  if (s.spell_numbers != null) { $('opt-numbers').checked = s.spell_numbers; $('opt-numbers').dataset.touched = '1'; }
  fillCreateSelects(); renderScripts(); updateSummary();
}
$('preset').addEventListener('change', () => {
  const p = S.presets.find((x) => x.id === $('preset').value);
  $('preset-delete').hidden = !p;
  if (p) { applyPreset(p); toast(`Preset “${p.name}” applied.`, true); }
});
$('preset-save').addEventListener('click', run(async () => {
  const cur = S.presets.find((x) => x.id === $('preset').value);
  const r = await editDialog({ title: cur ? `Update “${cur.name}”` : 'Save as a preset', nameLabel: 'Preset name',
    name: cur?.name || '', help: 'Saves the voice, language, model, speed, loudness, pauses, files and the numbers option. Same name = update it.', ok: 'Save' });
  if (!r || !r.name.trim()) return;
  const { voice, language, model, speed, loudness, formats, subtitles, pause_paragraph, spell_numbers } = createSettings();
  const p = await api('/api/presets', { method: 'POST', json: { name: r.name.trim(), settings: { voice, language, model, speed, loudness, formats, subtitles, pause_paragraph, spell_numbers } } });
  await loadPresets(); $('preset').value = p.id; $('preset-delete').hidden = false;
  toast(`Saved preset “${p.name}”.`, true);
}));
$('preset-delete').addEventListener('click', run(async () => {
  const p = S.presets.find((x) => x.id === $('preset').value); if (!p) return;
  if (!await confirmDialog(`Delete preset “${p.name}”?`, 'Only the preset is deleted; voices and batches are untouched.')) return;
  await api(`/api/presets/${p.id}`, { method: 'DELETE' });
  $('preset').value = ''; await loadPresets();
}));

// "See what the voice will read"
$('read-preview').addEventListener('click', run(async () => {
  const text = S.cmode === 'single' ? $('single-text').value : (S.scripts.find((s) => s.text.trim())?.text || '');
  if (!text.trim()) throw new Error('Type some text first.');
  const r = await api('/api/speakable', { method: 'POST', json: { text, language: $('language').value, spell_numbers: $('opt-numbers').checked } });
  await editDialog({ title: 'What the voice will read', text: r.text, rows: 12, ok: 'Close',
    help: (r.numbers_supported ? '' : 'Numbers stay as digits in this language (the voice reads them itself). ')
      + 'Your script and subtitles keep the original spelling. Fix a word on the Pronunciation page.' });
}));

// ---------- batch output (speed, loudness, files) ----------
async function editOutput(scriptN) {
  const one = scriptN != null ? S.detail.scripts.find((x) => x.n === scriptN) : null;
  const s = one ? one.out : S.detail.settings;
  const speeds = [0.85, 0.9, 0.95, 1, 1.05, 1.1, 1.15, 1.2];
  const r = await editDialog({
    title: 'Output', help: 'Finished scripts are rebuilt with these settings in a few seconds each; nothing is spoken again.',
    extra: `<div class="pair"><div class="field"><label class="label">Speed</label><div class="select-wrap"><select class="select" name="speed">${speeds.map((v) => `<option value="${v}"${Math.abs(v - (s.speed || 1)) < 0.001 ? ' selected' : ''}>${v}×</option>`).join('')}</select>${icon('chevron')}</div></div>
      <div class="field"><label class="label">Loudness (LUFS)</label><input class="input mono" type="number" step="0.5" min="-30" max="-9" name="loudness" value="${s.loudness ?? -16}"></div></div>
      <div class="checks"><label><input type="checkbox" name="wav" ${(s.formats || []).includes('wav') ? 'checked' : ''}> WAV</label>
        <label><input type="checkbox" name="mp3" ${(s.formats || []).includes('mp3') ? 'checked' : ''}> MP3</label>
        <label><input type="checkbox" name="subtitles" ${s.subtitles !== false ? 'checked' : ''}> Subtitles (SRT)</label></div>`,
    ok: 'Rebuild files',
  });
  if (!r) return;
  const formats = [r.wav && 'wav', r.mp3 && 'mp3'].filter(Boolean);
  S.detail = await api(`/api/batches/${S.detail.id}/settings${one ? `?script=${one.n}` : ''}`, { method: 'PATCH',
    json: { speed: Number(r.speed), loudness: Number(r.loudness), formats, subtitles: r.subtitles } });
  $('b-scripts')._html = ''; renderDetail(); toast('Rebuilding the files…', true);
}

// ---------- voice separator availability (Voices) ----------
function separateHelp() {
  const ready = S.state?.models.find((m) => m.key === 'uvr-vocals')?.installed;
  $('voice-separate').disabled = !ready;
  if (!ready) $('voice-separate').checked = false;
  $('voice-separate-help').innerHTML = ready
    ? 'For clips from videos, songs or anything with music under the voice. A long file is cut to its best minute first.'
    : 'Needs the voice separator (67 MB): <a href="#models">Models → Voice separator</a>.';
}

// ---------- PRONUNCIATION ----------
async function loadWords() {
  S.words = await api('/api/dictionary');
  const lang = S.state?.default_language || 'en';
  if (!$('w-lang').options.length) {
    $('w-lang').innerHTML = `<option value="">Every language</option>${languageOptions(lang)}`;
    $('w-test-lang').innerHTML = languageOptions(lang);
  }
  renderWords();
}
function renderWords() {
  const q = $('w-search').value.trim().toLowerCase();
  const rows = S.words.filter((w) => !q || w.from.toLowerCase().includes(q) || w.to.toLowerCase().includes(q));
  $('w-count').textContent = `(${S.words.length})`;
  $('w-table').innerHTML = `<tr><th>Written</th><th>Said as</th><th>Language</th><th>Capitals</th><th></th></tr>` + (rows.length ? rows.map((w) => `
    <tr data-id="${w.id}"><td class="mono">${esc(w.from)}</td><td>${esc(w.to)}</td><td>${w.language ? esc(langName(w.language)) : 'Every language'}</td>
      <td>${w.case ? 'exactly' : 'any'}</td>
      <td style="text-align:right;white-space:nowrap"><button class="btn xs" data-w="hear">${icon('speaker')} Hear</button>
        <button class="btn xs" data-w="edit">${icon('pencil')} Edit</button><button class="icon-btn" data-w="delete" aria-label="Delete">${icon('trash')}</button></td></tr>`).join('')
    : '<tr><td colspan="5" class="help" style="padding:16px 10px">No words yet.</td></tr>');
}
$('w-search').addEventListener('input', renderWords);

// Import / export the dictionary (CSV for Excel or Google Sheets, JSON, or TXT lines "written = said")
$('w-export').addEventListener('click', run(async () => {
  const r = await editDialog({
    title: 'Export pronunciations', ok: 'Download',
    help: 'CSV opens in Excel or Google Sheets (accents included); JSON is for other tools or a backup. Import it again on any PC.',
    extra: `<div class="pair"><div class="field"><label class="label">Format</label><div class="select-wrap"><select class="select" name="format">
        <option value="csv">CSV (Excel, Google Sheets)</option><option value="json">JSON</option></select>${icon('chevron')}</div></div>
      <div class="field"><label class="label">Words</label><div class="select-wrap"><select class="select" name="language">
        <option value="">All languages</option>${languageOptions('')}</select>${icon('chevron')}</div></div></div>
      <p class="help">${plural(S.words.length, 'word')} in the dictionary. “All languages” words are included in every language's export.</p>`,
  });
  if (!r) return;
  const a = document.createElement('a');
  a.href = `/api/dictionary/export?format=${r.format}${r.language ? `&language=${r.language}` : ''}`;
  a.download = '';
  document.body.append(a); a.click(); a.remove();
}));
$('w-import').addEventListener('click', run(async () => {
  let file = null;
  const r = await editDialog({
    title: 'Import pronunciations', ok: 'Import',
    help: 'A CSV (written, said, language, exact_capitals — English or Spanish headers, comma or semicolon), a JSON file, or a TXT list with one “written = said as” per line.',
    extra: `<label class="drop" id="wi-drop"><input type="file" id="wi-file" accept=".csv,.json,.txt,text/csv,application/json,text/plain" hidden>
        ${icon('upload')}<span id="wi-text">Choose or drop the file</span></label>
      <div class="field"><label class="label">Language for rows that don't say</label><div class="select-wrap"><select class="select" name="language">
        <option value="">Every language</option>${languageOptions('')}</select>${icon('chevron')}</div></div>
      <label class="check"><input type="checkbox" name="update" checked> Update words that are already in the dictionary</label>`,
    onOpen: (dlg) => {
      const inp = dlg.querySelector('#wi-file'), drop = dlg.querySelector('#wi-drop');
      const pick = (f) => { file = f; dlg.querySelector('#wi-text').innerHTML = f ? `<b>${esc(f.name)}</b> · ${fmtSize(f.size)}` : 'Choose or drop the file'; };
      inp.addEventListener('change', () => pick(inp.files[0] || null));
      ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
      ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove('over')));
      drop.addEventListener('drop', (e) => { e.preventDefault(); pick(e.dataTransfer.files[0] || null); });
    },
  });
  if (!r) return;
  if (!file) throw new Error('Choose a file to import.');
  const form = new FormData();
  form.append('file', file); form.append('language', r.language); form.append('update', r.update ? '1' : '0');
  const res = await api('/api/dictionary/import', { method: 'POST', form });
  await loadWords(); updateWordTest();
  const summary = `Imported: ${res.added} added, ${res.updated} updated, ${res.skipped} already there`
    + (res.problem_count ? `, ${plural(res.problem_count, 'line')} skipped.` : '.');
  if (res.problem_count) {
    await editDialog({ title: 'Import finished, with some problems', text: [summary, '', ...res.problems].join('\n'), rows: 10, ok: 'OK',
      help: 'The good rows were imported. Fix these lines in the file and import it again (words already imported are just skipped).' });
  } else toast(summary, true);
}));
$('w-add').addEventListener('click', run(async () => {
  await api('/api/dictionary', { method: 'POST', json: { written: $('w-from').value, said: $('w-to').value, language: $('w-lang').value, case: $('w-case').checked } });
  toast(`Added “${$('w-from').value.trim()}”.`, true);
  $('w-from').value = ''; $('w-to').value = ''; $('w-case').checked = false;
  await loadWords(); updateWordTest();
}));
async function hearText(text, lang, btn) {
  const voice = S.settings?.default_voice || S.voices[0]?.id;
  if (!voice) throw new Error('Add a voice first (Voices page).');
  const old = btn.innerHTML; btn.disabled = true; btn.innerHTML = `${icon('speaker')} Speaking…`;
  try {
    const r = await api(`/api/voices/${encodeURIComponent(voice)}/preview`, { method: 'POST', json: { text, language: lang }, raw: true });
    new Audio(URL.createObjectURL(await r.blob())).play();
  } finally { btn.disabled = false; btn.innerHTML = old; }
}
$('w-hear').addEventListener('click', run(async (e) => {
  const said = $('w-to').value.trim() || $('w-from').value.trim();
  if (!said) throw new Error('Type the word first.');
  await hearText(said, $('w-lang').value || S.state.default_language, e.currentTarget);
}));
$('w-table').addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-w]'); if (!b) return;
  const w = S.words.find((x) => x.id === b.closest('tr').dataset.id);
  if (b.dataset.w === 'hear') return hearText(w.to, w.language || S.state.default_language, b);
  if (b.dataset.w === 'delete') { await api(`/api/dictionary/${w.id}`, { method: 'DELETE' }); return loadWords(); }
  const r = await editDialog({ title: `Edit “${w.from}”`, name: w.from, nameLabel: 'Written', ok: 'Save',
    extra: `<div class="field"><label class="label">Said as</label><input class="input" name="said" value="${esc(w.to)}"></div>
      <div class="pair"><div class="field"><label class="label">Language</label><div class="select-wrap"><select class="select" name="language"><option value="">Every language</option>${languageOptions(w.language)}</select>${icon('chevron')}</div></div>
      <div class="field" style="justify-content:flex-end"><label class="check" style="height:42px"><input type="checkbox" name="case" ${w.case ? 'checked' : ''}> Only with these capitals</label></div></div>` });
  if (!r) return;
  await api(`/api/dictionary/${w.id}`, { method: 'PATCH', json: { written: r.name, said: r.said, language: r.language, case: r.case } });
  loadWords();
}));
let wordTimer;
function updateWordTest() {
  clearTimeout(wordTimer);
  wordTimer = setTimeout(run(async () => {
    const text = $('w-test').value;
    if (!text.trim()) { $('w-test-out').textContent = 'What the voice reads appears here.'; return; }
    const r = await api('/api/speakable', { method: 'POST', json: { text, language: $('w-test-lang').value, spell_numbers: $('w-test-num').checked } });
    $('w-test-out').textContent = r.text + (r.numbers_supported ? '' : '  (numbers stay as digits in this language)');
  }), 250);
}
['w-test', 'w-test-lang', 'w-test-num'].forEach((id) => $(id).addEventListener(id === 'w-test' ? 'input' : 'change', updateWordTest));

// ---------- TRANSCRIBE ----------
S.tFile = null;
async function loadTranscribe() {
  const st = S.state;
  if (!$('t-lang').options.length) $('t-lang').innerHTML = `<option value="">Detect automatically</option>${languageOptions('')}`;
  const keepModel = $('t-model').value;
  const subs = st.models.filter((m) => m.kind === 'subtitles');
  $('t-model').innerHTML = `<option value="">The one in use</option>` + subs.map((m) => `<option value="${m.key}"${m.key === keepModel ? ' selected' : ''}${m.installed ? '' : ' disabled'}>${esc(m.label)}${m.installed ? '' : ' (not downloaded)'}</option>`).join('');
  const tools = await api('/api/tools');
  const ff = tools.find((t) => t.key === 'ffmpeg');
  $('t-help').innerHTML = !st.subtitles_ready ? 'Download a Whisper model first: <a href="#models">Models</a>.'
    : ff?.ready ? 'Small is quick; Medium and Large are more accurate for other people\'s audio. You can leave this page; it carries on.'
    : 'Audio files work now. For video files, get ffmpeg on the <a href="#models">Models page</a> (Tools).';
  $('t-go').disabled = !(S.tFile && st.subtitles_ready);
  renderTranscripts();
}
async function renderTranscripts() {
  let list;
  try { list = await api('/api/transcripts'); } catch { return; }
  const html = list.length ? list.map((t) => {
    const busy = ['queued', 'converting', 'running'].includes(t.status);
    const state = t.status === 'converting' ? 'Reading the file…' : t.status === 'running' ? `Transcribing… ${t.progress}%` : t.status === 'queued' ? 'Waiting' : '';
    return `<div class="card bcard" data-id="${t.id}"><div class="main">
        <div class="row" style="gap:10px;min-width:0">${busy ? (t.status === 'queued' ? chip('queued') : '<span class="chip accent live">Transcribing</span>') : chip(t.status)}<span class="name">${esc(t.name)}</span></div>
        <div class="meta"><span>${fmtWhen(t.created)}</span>${t.seconds ? `<span>${fmtClock(t.seconds)} long</span>` : ''}
          ${t.words ? `<span>${t.words.toLocaleString()} words</span>` : ''}${t.detected_language ? `<span>${esc(langName(t.detected_language))}</span>` : ''}
          ${t.translate ? '<span>translated to English</span>' : ''}${t.took ? `<span>took ${fmtDur(t.took)}</span>` : ''}<span>${esc((S.state.models.find((m) => m.key === t.model) || {}).label || t.model || '')}</span></div>
        ${busy ? `<div class="progress live" style="margin-top:6px"><div style="width:${Math.max(4, t.progress)}%"></div></div><span class="micro">${state}</span>` : ''}
        ${t.error ? `<div class="err-note">${esc(t.error)}</div>` : ''}
      </div><div class="acts">
        ${t.status === 'done' ? `<button class="btn sm" data-tr="view">${icon('text')} Read</button>${Object.keys(t.files).filter((k) => k !== 'json').map((k) => `<a class="btn sm" href="/api/transcripts/${t.id}/${k}?download=1">${icon('download')} ${k.toUpperCase()}</a>`).join('')}` : ''}
        <button class="icon-btn" data-tr="delete" aria-label="Delete">${icon('trash')}</button></div></div>`;
  }).join('') : emptyCard('text', 'No transcripts yet', 'Drop a video or audio file above to get its text and subtitles.');
  setHtml($('t-list'), html);
  if (list.some((t) => ['queued', 'converting', 'running'].includes(t.status)) && S.view === 'transcribe') setTimeout(renderTranscripts, 1000);
}
function setTFile(f) {
  S.tFile = f;
  $('t-drop-text').innerHTML = f ? `<b>${esc(f.name)}</b><br><small>${fmtSize(f.size)} · click to choose another</small>` : 'Drop a video or audio file here, or click to choose';
  $('t-go').disabled = !(f && S.state?.subtitles_ready);
}
$('t-file').addEventListener('change', (e) => setTFile(e.target.files[0] || null));
const tdrop = $('t-drop');
['dragenter', 'dragover'].forEach((ev) => tdrop.addEventListener(ev, (e) => { e.preventDefault(); tdrop.classList.add('over'); }));
['dragleave', 'drop'].forEach((ev) => tdrop.addEventListener(ev, () => tdrop.classList.remove('over')));
tdrop.addEventListener('drop', (e) => { e.preventDefault(); if (e.dataTransfer.files[0]) setTFile(e.dataTransfer.files[0]); });
$('t-go').addEventListener('click', run(async () => {
  const form = new FormData();
  form.append('file', S.tFile); form.append('language', $('t-lang').value); form.append('model', $('t-model').value);
  form.append('translate', $('t-translate').checked ? '1' : '0');
  $('t-go').disabled = true; $('t-go').textContent = 'Uploading…';
  try { await api('/api/transcripts', { method: 'POST', form }); setTFile(null); $('t-file').value = ''; }
  finally { $('t-go').textContent = 'Transcribe'; }
  $('t-list')._html = ''; renderTranscripts();
}));
$('t-list').addEventListener('click', run(async (e) => {
  const b = e.target.closest('[data-tr]'); if (!b) return;
  const id = b.closest('.bcard').dataset.id;
  if (b.dataset.tr === 'delete') {
    if (!await confirmDialog('Delete this transcript?', 'Its text and subtitle files go to the Recycle Bin.')) return;
    await api(`/api/transcripts/${id}`, { method: 'DELETE' }); $('t-list')._html = ''; return renderTranscripts();
  }
  const text = await (await fetch(`/api/transcripts/${id}/txt`)).text();
  await editDialog({ title: 'Transcript', text, rows: 18, ok: 'Close', help: 'Select and copy what you need, or download the TXT / SRT / VTT.' });
}));

// ---------- ABOUT ----------
const PK_FLAG = '<svg class="flag" viewBox="0 0 30 20" role="img" aria-label="Pakistan"><rect width="30" height="20" fill="#01411c"/><rect width="7.5" height="20" fill="#fff"/><circle cx="18.6" cy="10.7" r="5.6" fill="#fff"/><circle cx="20.1" cy="9.4" r="5" fill="#01411c"/><polygon fill="#fff" points="23.62,5.12 23.17,6.70 24.50,7.67 22.85,7.73 22.34,9.30 21.77,7.75 20.13,7.75 21.42,6.73 20.92,5.16 22.28,6.08"/></svg>';  // drawn, because Windows shows flag emoji as letters
async function loadAbout() {
  const [a, setup, settings, updFull] = await Promise.all([api('/api/about'), api('/api/setup').catch(() => null),
    api('/api/settings'), api('/api/update').catch(() => null)]);
  S.settings = settings;
  const st = S.state, upd = st.update || {};
  const gpu = setup?.hardware?.gpus?.filter((g) => !g.integrated).map((g) => `${g.name}${g.vram_gb ? ` (${g.vram_gb} GB)` : ''}`).join(', ');
  const hw = setup?.hardware;
  const models = st.models.filter((m) => m.installed);
  const details = [
    ['App', `Fatima Voice Studio ${a.version} (${a.installed ? 'installed' : 'from source'})`],
    ['Windows', a.windows],
    ['Processor', hw ? `${hw.cpu}, ${hw.cores} cores, ${Math.round(hw.ram_gb)} GB RAM` : '—'],
    ['Graphics', gpu || 'none found'],
    ['Engine', `${st.engine.engine.toUpperCase()} · llama.cpp ${a.engine_release}`],
    ['Models', models.map((m) => m.label).join(', ') || 'none yet'],
    ['Python', a.python],
  ];
  S.aboutText = details.map(([k, v]) => `${k}: ${v}`).join('\n');
  const status = upd.status === 'available' ? `<button type="button" class="chip accent" data-about="updates">Version ${esc(upd.latest)} available</button>`
    : upd.status === 'up_to_date' ? '<span class="chip ok">Up to date</span>' : '';
  const html = `
    <section class="card about-hero">
      <span class="mark">${icon('mark')}</span>
      <div class="who">
        <h2>Fatima Voice Studio</h2>
        <div class="ver"><span>Version ${esc(a.version)}</span>${status}</div>
        <p class="tag">Voiceovers in your own voices, made on your own PC. No subscription, nothing uploaded.</p>
        <div class="made-in"><span>Proudly made in Pakistan</span> ${PK_FLAG} <span style="white-space:nowrap">with <span aria-label="love">❤️</span> by Hassan Latif</span></div>
      </div>
      <div class="links">
        <a class="btn sm" href="${esc(a.repo)}" target="_blank" rel="noopener">${icon('code')} GitHub</a>
        <a class="btn sm" href="#help">${icon('question')} Help</a>
      </div>
    </section>
    <div class="about-grid">
      ${updatesPanel({ ...settings, version: a.version, installed: a.installed }, updFull)}
      <section class="card panel"><h2>Models and licences</h2>
        <p class="help">Everything here can be used in monetized videos and client work, unless it's marked otherwise.</p>
        <div class="lic-list">${models.length ? models.map((m) => `<div class="lic-row"><span><b>${esc(m.label)}</b>${m.runtime === 's2' ? ' <span class="help">· Built with Fish Audio</span>' : ''}</span>
          <span class="license ${m.noncommercial ? 'nc' : 'ok'}">${m.noncommercial ? '' : icon('check')} ${esc(m.license)}</span></div>`).join('')
          : '<p class="help">No models downloaded yet. See <a href="#models">Models</a>.</p>'}</div>
        <div class="lic-row"><span><b>Fatima Voice Studio</b></span><span class="license ok">${icon('check')} MIT — free and open source</span></div>
      </section>
      <section class="card panel"><h2>This PC</h2>
        <p class="help">Something not working? Copy these details into your report on GitHub, so it can be fixed sooner.</p>
        <div class="kv">${details.map(([k, v]) => `<span class="k">${k}</span><span>${esc(v)}</span>`).join('')}</div>
        <div class="row wrap">
          <button class="btn sm accent" data-about="copy">${icon('copy')} Copy details</button>
          <a class="btn sm" href="${esc(a.repo)}/issues" target="_blank" rel="noopener">${icon('alert')} Report a problem</a>
          <button class="btn sm" data-open-folder="logs">${icon('folder')} Logs</button>
        </div>
        <details class="more"><summary>Folders</summary><div class="more-body"><div class="kv">
          ${Object.entries(a.folders).map(([k, v]) => `<span class="k">${esc(k)}</span><span class="mono" style="font-size:12px">${esc(v)}</span>`).join('')}</div></div></details>
      </section>
    </div>
    ${a.notices ? `<details class="card about-notices"><summary>Built with: third-party software and licences</summary>
      <div class="doc">${mdRender(a.notices.replace(/^# .*\n/, ''), 'README')}</div></details>` : ''}`;
  setHtml($('about-body'), html);
}
$('about-body').addEventListener('click', run(async (e) => {
  if (e.target.closest('[data-about="updates"]')) { $('about-updates')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
  if (e.target.closest('[data-about="copy"]')) { await copyText(S.aboutText); toast('Copied. Paste it into your problem report.', true); return; }
  const up = e.target.closest('[data-update]');
  if (up) {
    if (up.dataset.update === 'check') await api('/api/update/check', { method: 'POST' });
    else {
      if (!await confirmDialog('Install the update now?', 'The app closes, updates and starts again by itself. Your voices, models, settings and audio are kept.', 'Update')) return;
      await api(`/api/update/${up.dataset.update}`, { method: 'POST' });
      toast('Updating… the app restarts by itself.', true);
    }
    $('about-body')._html = ''; loadAbout();
  }
}));
$('about-body').addEventListener('change', run(async (e) => {
  if (e.target.dataset.set !== 'check_updates') return;
  S.settings = await api('/api/settings', { method: 'PUT', json: { check_updates: e.target.checked } });
  toast('Saved.', true);
}));

// ---------- HELP ----------
// The guides are the Markdown files in studio/help (also read on GitHub). #help/<guide>/<section> opens one.
const HELP_FOR = { create: 'making-voiceovers', batches: 'batches', batch: 'batches', voices: 'voices', transcribe: 'transcribe',
  models: 'setup-and-models', setup: 'setup-and-models', connect: 'connect', settings: 'settings', words: 'pronunciation',
  about: 'troubleshooting' };
S.help = { docs: {}, toc: null };

// GitHub's heading ids: lower case, punctuation dropped, spaces to hyphens ("3. Setup: two downloads" -> "3-setup-two-downloads").
const slugify = (t) => t.toLowerCase().replace(/<[^>]+>/g, '').replace(/[^\p{L}\p{N}\s_-]/gu, '').trim().replace(/\s/g, '-');

function helpHref(href, page) {
  if (/^[a-z]+:/i.test(href)) return { href, external: true };
  const [file, anchor] = href.split('#');
  if (!file) return { href: `#help/${page}/${anchor}` };
  if (!file.endsWith('.md')) return { href: `/help-files/${file}`, external: true };
  const name = file.replace(/\.md$/, '');
  return { href: `#help${name === 'README' ? '' : `/${name}`}${anchor ? `${name === 'README' ? '/README' : ''}/${anchor}` : ''}` };
}

function mdInline(text, page) {
  const codes = [];
  let s = esc(text).replace(/`([^`]+)`/g, (_, c) => `\u0000${codes.push(c) - 1}\u0000`);
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_, alt, src) => `<img src="${/^[a-z]+:/i.test(src) ? src : `/help-files/${src}`}" alt="${alt}" loading="lazy">`);
  s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, href) => {
    const h = helpHref(href.replace(/&amp;/g, '&'), page);
    return `<a href="${esc(h.href)}"${h.external ? ' target="_blank" rel="noopener"' : ''}>${label}</a>`;
  });
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<em>$2</em>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[i]}</code>`);
}

// Just the Markdown the guides use: headings, paragraphs, lists (one level of nesting), tables, quotes, code, images.
function mdRender(md, page) {
  const lines = md.replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  let i = 0;
  const isBlockStart = (l) => /^(#{1,4}\s|```|>|\|)/.test(l) || /^\s*([-*]|\d+\.)\s/.test(l) || !l.trim();
  const list = (indent) => {
    const ordered = /^\s*\d+\./.test(lines[i]);
    const items = [];
    while (i < lines.length) {
      const m = lines[i].match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
      if (!m || m[1].length !== indent) {
        if (m && m[1].length > indent && items.length) { items[items.length - 1].sub += list(m[1].length); continue; }
        if (!m && lines[i].trim() && /^\s+/.test(lines[i]) && items.length) { items[items.length - 1].text += ' ' + lines[i].trim(); i++; continue; }
        break;
      }
      items.push({ text: m[3], sub: '' }); i++;
    }
    const tag = ordered ? 'ol' : 'ul';
    return `<${tag}>${items.map((it) => `<li>${mdInline(it.text, page)}${it.sub}</li>`).join('')}</${tag}>`;
  };
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m;
    if (l.startsWith('```')) {
      const code = [];
      for (i++; i < lines.length && !lines[i].startsWith('```'); i++) code.push(lines[i]);
      i++;
      out.push(`<div class="code"><button class="icon-btn copy" data-copy="${esc(code.join('\n'))}" aria-label="Copy">${icon('copy')}</button>${esc(code.join('\n'))}</div>`);
    } else if ((m = l.match(/^(#{1,4})\s+(.*)$/))) {
      const n = m[1].length, html = mdInline(m[2], page);
      out.push(`<h${n} id="h-${slugify(m[2])}">${html}</h${n}>`); i++;
    } else if (/^\s*!\[[^\]]*\]\([^)]+\)\s*$/.test(l)) {
      out.push(`<figure>${mdInline(l.trim(), page)}</figure>`); i++;
    } else if (l.startsWith('>')) {
      const q = [];
      for (; i < lines.length && lines[i].startsWith('>'); i++) q.push(lines[i].replace(/^>\s?/, ''));
      out.push(`<aside class="tip">${mdInline(q.join(' '), page)}</aside>`);
    } else if (l.startsWith('|')) {
      const rows = [];
      for (; i < lines.length && lines[i].startsWith('|'); i++) rows.push(lines[i].trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
      const [head, , ...body] = rows;
      out.push(`<div class="table-wrap"><table class="plain"><tr>${head.map((c) => `<th>${mdInline(c, page)}</th>`).join('')}</tr>${body.map((r) => `<tr>${r.map((c) => `<td>${mdInline(c, page)}</td>`).join('')}</tr>`).join('')}</table></div>`);
    } else if (/^\s*([-*]|\d+\.)\s/.test(l)) {
      out.push(list(l.match(/^\s*/)[0].length));
    } else {
      const p = [];
      for (; i < lines.length && lines[i].trim() && !(p.length && isBlockStart(lines[i])); i++) p.push(lines[i].trim());
      out.push(`<p>${mdInline(p.join(' '), page)}</p>`);
    }
  }
  return out.join('\n');
}

async function helpDoc(name) {
  if (!(name in S.help.docs)) {
    const r = await fetch(`/help-files/${name}.md`);
    if (!r.ok) throw new Error('That guide could not be found.');
    S.help.docs[name] = (await r.text()).replace(/\r\n?/g, '\n');  // a Windows checkout may have CRLF line ends
  }
  return S.help.docs[name];
}

// The contents come from README.md: each ## heading is a group, each link under it a guide.
async function helpToc() {
  if (S.help.toc) return S.help.toc;
  const groups = [];
  for (const line of (await helpDoc('README')).split('\n')) {
    const h = line.match(/^##\s+(.*)$/);
    if (h) { groups.push({ title: h[1], guides: [] }); continue; }
    const g = line.match(/^- \[([^\]]+)\]\(([\w-]+)\.md\)/);
    if (g && groups.length) groups[groups.length - 1].guides.push({ title: g[1], name: g[2] });
  }
  S.help.toc = groups;
  return groups;
}

function renderHelpToc(current) {
  const groups = S.help.toc || [];
  setHtml($('help-toc'), `<a href="#help" class="${current === 'README' ? 'on' : ''}">${icon('text')} All guides</a>`
    + groups.map((g) => `<div class="micro">${esc(g.title)}</div>${g.guides.map((d) => `<a href="#help/${d.name}" class="${d.name === current ? 'on' : ''}">${esc(d.title)}</a>`).join('')}`).join(''));
}

async function loadHelp() {
  const [, name = 'README', section] = location.hash.slice(1).split('/').map(decodeURIComponent);
  if ($('help-search').value.trim()) { $('help-search').value = ''; }
  try {
    await helpToc();
    renderHelpToc(name);
    const md = await helpDoc(name);
    $('help-doc').innerHTML = mdRender(md, name);
    $('help-doc')._html = null;
  } catch (e) {
    $('help-doc').innerHTML = `<p class="err-note">${esc(e.message)}</p><p><a href="#help">All guides</a></p>`;
    return;
  }
  // The top bar is sticky and its height changes with the window's width: scroll to just below it.
  const bar = document.querySelector('.appbar').offsetHeight;
  document.documentElement.style.setProperty('--appbar-h', `${bar}px`);
  const target = section && document.getElementById(`h-${section}`);
  requestAnimationFrame(() => window.scrollTo(0, target ? target.getBoundingClientRect().top + scrollY - bar - 16 : 0));
}

// Search: every guide, by section; the best matches with a line of context.
let helpTimer;
$('help-search').addEventListener('input', () => {
  clearTimeout(helpTimer);
  helpTimer = setTimeout(run(async () => {
    const q = $('help-search').value.trim().toLowerCase();
    if (!q) return loadHelp();
    const toc = await helpToc();
    const words = q.split(/\s+/).filter(Boolean);
    const hits = [];
    for (const g of toc) {
      for (const d of g.guides) {
        const md = await helpDoc(d.name);
        let head = d.title, anchor = '', body = [];
        const flush = () => {
          const text = body.join(' ').replace(/[`*#|>]/g, ' ').replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/\s+/g, ' ').trim();
          const hay = `${head} ${text}`.toLowerCase();
          if (words.every((w) => hay.includes(w))) {
            const score = words.reduce((n, w) => n + (head.toLowerCase().includes(w) ? 5 : 0) + hay.split(w).length - 1, 0);
            const at = Math.max(0, text.toLowerCase().indexOf(words[0]) - 60);
            hits.push({ guide: d.title, name: d.name, head, anchor, score, snip: (at ? '…' : '') + text.slice(at, at + 180) + (text.length > at + 180 ? '…' : '') });
          }
        };
        for (const line of md.split('\n')) {
          const h = line.match(/^#{1,4}\s+(.*)$/);
          if (h) { flush(); head = h[1]; anchor = line.startsWith('# ') ? '' : slugify(h[1]); body = []; } else body.push(line);
        }
        flush();
      }
    }
    hits.sort((a, b) => b.score - a.score);
    const mark = (t) => esc(t).replace(new RegExp(`(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})`, 'gi'), '<mark>$1</mark>');
    $('help-doc').innerHTML = `<h1>Search: “${esc(q)}”</h1>` + (hits.length
      ? hits.slice(0, 25).map((h) => `<a class="hit" href="#help/${h.name}${h.anchor ? `/${h.anchor}` : ''}"><span class="micro">${esc(h.guide)}</span><b>${mark(h.head)}</b><span>${mark(h.snip)}</span></a>`).join('')
      : '<p>Nothing found. Try fewer or other words, or browse the guides on the left.</p>');
  }), 200);
});
$('help-search').addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('help-search').value = ''; loadHelp(); } });

// A "Help" link on every page, to its guide.
for (const [view, guide] of Object.entries(HELP_FOR)) {
  $(`view-${view}`).querySelector('.title-row')?.insertAdjacentHTML('beforeend', `<a class="page-help" href="#help/${guide}">${icon('question')} Help</a>`);
}

// ---------- start ----------
paintIcons();
loadDraft();
setSmode('list');
(async () => {
  await pollState();
  try { S.settings = await api('/api/settings'); } catch { /* not ready */ }
  try { const s = await api('/api/setup'); S.setupBench = s.benchmark; } catch { /* not ready */ }
  route();
  setInterval(async () => {
    await pollState();
    if (document.hidden) return;
    if (S.view === 'batch' && S.arg) {
      try { S.detail = await api(`/api/batches/${encodeURIComponent(S.arg)}`); renderDetail(); } catch { /* deleted */ }
    } else if (S.view === 'batches') loadBatches();
    else if (S.view === 'create') renderQueue();
  }, 1500);
})();
