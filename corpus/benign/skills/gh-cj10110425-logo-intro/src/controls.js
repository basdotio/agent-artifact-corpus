/*! logo-intro v0.1.0 · MIT License */
/** Playback bar for previewing an intro: play/pause, replay, a scrubber with beat ticks, speed and loop. */
import { DURATION, TIMELINE } from './logo-intro.js';

const CSS = `
.lic{--bg:rgba(255,255,255,.88);--line:#e2e5de;--text:#15181a;--muted:#666d68;--chip:#eff1eb;--chip-on:#fff;--track:#15181a;--btn:#15181a;--btn-ink:#fff;--focus:#a4cf2a;
  position:fixed;left:50%;bottom:calc(16px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);z-index:10;
  width:min(780px,calc(100% - 32px));box-sizing:border-box;display:flex;align-items:center;gap:12px;padding:10px 12px;
  background:var(--bg);-webkit-backdrop-filter:blur(14px) saturate(1.2);backdrop-filter:blur(14px) saturate(1.2);
  border:1px solid var(--line);border-radius:16px;box-shadow:0 12px 32px -20px rgba(0,0,0,.45);
  font:500 13px/1.3 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--text)}
.lic.lic-dark{--bg:rgba(39,39,42,.82);--line:#3f3f46;--text:#e4e4e7;--muted:#a1a1aa;--chip:#27272a;--chip-on:#3f3f46;--track:#fafafa;--btn:#fafafa;--btn-ink:#18181b;--focus:#a77dff}
.lic button{font:inherit;cursor:pointer}
.lic button:focus-visible,.lic input:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.lic-play{flex:none;width:36px;height:36px;border-radius:50%;border:0;background:var(--btn);color:var(--btn-ink);display:grid;place-items:center}
.lic-play svg{width:14px;height:14px}
.lic-ghost{flex:none;height:34px;padding:0 12px 0 10px;border-radius:10px;border:1px solid var(--line);background:transparent;color:inherit;display:inline-flex;align-items:center;gap:6px;font-weight:650}
.lic-ghost svg{width:15px;height:15px}
.lic-scrub{position:relative;flex:1;min-width:0;padding-bottom:15px}
.lic-range{--p:0%;-webkit-appearance:none;appearance:none;display:block;width:100%;height:22px;margin:0;background:transparent;cursor:pointer}
.lic-range::-webkit-slider-runnable-track{height:4px;border-radius:4px;background:linear-gradient(to right,var(--track) var(--p),var(--line) var(--p))}
.lic-range::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;margin-top:-5px;border-radius:50%;background:var(--chip-on);border:2px solid var(--track);box-sizing:border-box}
.lic-range::-moz-range-track{height:4px;border-radius:4px;background:var(--line)}
.lic-range::-moz-range-progress{height:4px;border-radius:4px;background:var(--track)}
.lic-range::-moz-range-thumb{width:14px;height:14px;border-radius:50%;background:var(--chip-on);border:2px solid var(--track);box-sizing:border-box}
.lic-ticks{position:absolute;left:7px;right:7px;bottom:0;height:13px;font-size:11px;line-height:13px;color:var(--muted);pointer-events:none}
.lic-ticks span{position:absolute;top:0;padding-left:4px;white-space:nowrap}
.lic-ticks span::before{content:"";position:absolute;left:0;top:1px;width:1px;height:10px;background:var(--line)}
.lic-clock{flex:none;min-width:52px;text-align:right;font-variant-numeric:tabular-nums}
.lic-seg{flex:none;display:inline-flex;padding:3px;gap:2px;background:var(--chip);border-radius:10px}
.lic-seg button,.lic-chip{height:28px;padding:0 9px;border:0;border-radius:8px;background:transparent;color:var(--muted);font-weight:650;font-variant-numeric:tabular-nums}
.lic-seg button[aria-pressed=true]{background:var(--chip-on);color:var(--text);box-shadow:0 1px 2px rgba(0,0,0,.12)}
.lic-chip{flex:none;height:34px;padding:0 12px;background:var(--chip);border-radius:10px}
.lic-chip[aria-pressed=true]{background:var(--track);color:var(--btn-ink)}
.lic [hidden]{display:none!important}
@media (max-width:620px){.lic{flex-wrap:wrap;gap:8px;row-gap:6px;padding:10px}.lic-scrub{order:5;flex-basis:100%}
  .lic-ghost .lic-label{display:none}.lic-ghost{padding:0 9px}.lic-clock{margin-right:auto;text-align:left}.lic-seg button{padding:0 7px}}`;

const PAUSE = '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2" y="1.5" width="3.4" height="11" rx="1" fill="currentColor"/><rect x="8.6" y="1.5" width="3.4" height="11" rx="1" fill="currentColor"/></svg>';
const PLAY = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 1.8v10.4a.8.8 0 0 0 1.2.7l8.3-5.2a.8.8 0 0 0 0-1.4L4.7 1.1a.8.8 0 0 0-1.2.7z" fill="currentColor"/></svg>';
const REPLAY = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.8 8a5.2 5.2 0 1 0 1.6-3.8" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><path d="M2.5 1.8v3.1h3.1" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>';

const isDark = hex => {
  const h = (hex || '#fff').replace('#', '');
  const n = parseInt(h.length === 3 ? h.replace(/./g, c => c + c) : h, 16);
  return (0.2126 * (n >> 16 & 255) + 0.7152 * (n >> 8 & 255) + 0.0722 * (n & 255)) / 255 < 0.5;
};

/** Mounts the bar and wires it to a player from mountLogoIntro. Returns a function that removes it. */
export function mountControls(player, { background = '#fff', parent = document.body } = {}) {
  if (!document.getElementById('lic-style')) {
    const s = document.createElement('style');
    s.id = 'lic-style';
    s.textContent = CSS;
    document.head.append(s);
  }
  const labels = { mark: 'Mark', wordmark: 'Word', lockIn: 'Lock', shimmer: 'Shine', hold: 'Hold' };
  const bar = document.createElement('div');
  bar.className = `lic${isDark(background) ? ' lic-dark' : ''}`;
  bar.setAttribute('role', 'toolbar');
  bar.setAttribute('aria-label', 'Playback');
  bar.innerHTML = `
    <button class="lic-play" type="button" aria-label="Pause">${PAUSE}</button>
    <button class="lic-ghost" type="button" aria-label="Replay">${REPLAY}<span class="lic-label">Replay</span></button>
    <div class="lic-scrub">
      <input class="lic-range" type="range" min="0" max="${DURATION * 1000}" step="1" value="0" aria-label="Timeline">
      <div class="lic-ticks" aria-hidden="true">${Object.entries(player.timeline || TIMELINE).sort((x, y) => x[1] - y[1]).map(([k, s]) => `<span style="left:${(s / DURATION * 100).toFixed(1)}%">${labels[k]}</span>`).join('')}</div>
    </div>
    <output class="lic-clock">0.00 s</output>
    <div class="lic-seg" role="group" aria-label="Speed">${[0.25, 0.5, 1].map(v => `<button type="button" data-speed="${v}" aria-pressed="${v === 1}">${v}×</button>`).join('')}</div>
    <button class="lic-chip" type="button" aria-pressed="false">Loop</button>`;
  parent.append(bar);
  const [playBtn, replayBtn] = bar.querySelectorAll('.lic-play, .lic-ghost');
  const range = bar.querySelector('.lic-range'), clock = bar.querySelector('.lic-clock'), loopBtn = bar.querySelector('.lic-chip');

  let raf = 0, shown = null;
  const sync = () => {
    const t = player.time;
    range.value = Math.round(t * 1000);
    range.style.setProperty('--p', `${(t / DURATION * 100).toFixed(2)}%`);
    clock.textContent = `${t.toFixed(2)} s`;
    if (shown !== player.playing) {
      shown = player.playing;
      playBtn.innerHTML = shown ? PAUSE : PLAY;
      playBtn.setAttribute('aria-label', shown ? 'Pause' : 'Play');
    }
    raf = requestAnimationFrame(sync);
  };
  raf = requestAnimationFrame(sync);

  const toggle = () => (player.playing ? player.pause() : player.play());
  playBtn.addEventListener('click', toggle);
  replayBtn.addEventListener('click', () => player.replay());
  range.addEventListener('input', () => player.seek(range.value / 1000));
  bar.querySelectorAll('[data-speed]').forEach(b => b.addEventListener('click', () => {
    player.setSpeed(+b.dataset.speed);
    bar.querySelectorAll('[data-speed]').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
  }));
  loopBtn.addEventListener('click', () => {
    player.loop = !player.loop;
    loopBtn.setAttribute('aria-pressed', String(player.loop));
  });
  const onKey = e => {
    const onControl = e.target.closest?.('button, input');
    if (e.key === ' ' && !onControl) { e.preventDefault(); toggle(); }
    else if ((e.key === 'r' || e.key === 'R') && !e.metaKey && !e.ctrlKey) player.replay();
    else if ((e.key === 'ArrowLeft' || e.key === 'ArrowRight') && e.target !== range) {
      e.preventDefault();
      player.seek(player.time + (e.key === 'ArrowRight' ? 1 : -1) / 25);
    }
  };
  document.addEventListener('keydown', onKey);
  return () => { cancelAnimationFrame(raf); document.removeEventListener('keydown', onKey); bar.remove(); };
}
