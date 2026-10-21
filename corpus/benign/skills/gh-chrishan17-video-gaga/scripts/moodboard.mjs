// video-gaga moodboard — one local HTML page that puts the style directions side
// by side so the user can pick one (SKILL.md, *What the user experiences*).
//
// Each direction is a style preview project (`gaga init .gaga-previews/style-a …` plus
// one scene with the user's own title). `gaga moodboard` renders, per direction:
// a looping motion sample, three frames, the palette and type read from its THEME,
// and the music direction. The pure parts live here; the CLI does the rendering.
//
// Optional <preview>/moodboard.json, written by the agent for this brief:
//   {
//     "name": "Warm paper explainer",            // what the user sees (default: folder name)
//     "pitch": "why it fits this brief, one line",
//     "recommended": true,                        // exactly one direction
//     "keywords": ["warm", "clear", "patient"],
//     "motion": "type lands on the spoken word; charts draw in reading order",
//     "music": "curious, bright · 100 BPM D major · pad, key stabs, glockenspiel",
//     "palette": ["#F3EFE6", { "hex": "#E4572E", "name": "the point" }],   // default: THEME colours
//     "type": [{ "family": "Noto Sans SC", "role": "display" }]           // default: THEME fonts
//   }

const HEADER = /^\/\/ === (.*?)\s*=*\s*$/;

// The THEME section(s) of a composition → colours and fonts, in source order.
export function themeFromHtml(src) {
  const lines = src.split('\n');
  const colors = [], fonts = [];
  let inTheme = false;
  for (const l of lines) {
    const h = l.match(HEADER);
    if (h) { inTheme = /^THEME\b/.test(h[1]); continue; }
    if (!inTheme) continue;
    // one colour per line (`bg: '#000', // note`) or several packed on one line (`night: '#16122B', shade: '#2C2554',`)
    const note = (l.match(/\/\/\s*(.*)$/)?.[1] || '').trim();
    const cs = [...l.replace(/\/\/.*$/, '').matchAll(/(?:^|[{,])\s*([\w$]+)\s*:\s*['"](#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?)['"]\s*(?=,|}|$)/g)];
    for (const c of cs) {
      if (!colors.some((x) => x.hex.toLowerCase() === c[2].toLowerCase())) colors.push({ name: c[1], hex: c[2].toUpperCase(), note: cs.length === 1 ? note : '' });
    }
    const f = l.match(/^\s*([\w$]+)\s*:\s*'("([^"]+)"[^']*)'\s*,?\s*(?:\/\/\s*(.*))?$/);
    if (f && !fonts.some((x) => x.family === f[3])) fonts.push({ name: f[1], family: f[3], stack: f[2], note: (f[4] || '').trim() });
  }
  const fontLinks = [...src.matchAll(/<link[^>]+href="(https:\/\/fonts\.googleapis\.com\/css2\?[^"]+)"/g)].map((m) => m[1].replace(/&amp;/g, '&'));
  return { colors, fonts, fontLinks };
}

// A generated score spec (info.score) → one line, for directions with a draft score.
export function describeScore(score) {
  if (!score) return null;
  const insts = [...new Set([...(score.layers || []).map((l) => l.inst), score.lead?.inst].filter(Boolean))];
  return [`${score.bpm} BPM`, [score.key, score.mode].filter(Boolean).join(' '), insts.join(', ')].filter(Boolean).join(' · ');
}

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const STRINGS = {
  zh: {
    heading: '选一个方向', sub: '每一列都是你的视频开场的真实样子：动态、配色、字体和配乐方向。点「选这个」，或直接在对话里告诉我。',
    recommended: '推荐', palette: '配色', type: '字体', motion: '动态', music: '配乐方向', frames: '关键帧',
    pick: '选这个', picked: '已选', note: '想混搭或调整？（可选）', notePh: '比如：A 的配色 + C 的动态',
    copied: '已复制，粘贴回对话即可：', sent: '已发送给 agent，可以关掉这个页面了。', sound: '听声音',
    reply: (l, n) => `我选 ${l}：${n}`, more: '补充：',
  },
  en: {
    heading: 'Pick a direction', sub: 'Each column is the real opening of your video: motion, palette, type and the music direction. Click “Pick this”, or just tell me in the chat.',
    recommended: 'Recommended', palette: 'Palette', type: 'Type', motion: 'Motion', music: 'Music direction', frames: 'Key frames',
    pick: 'Pick this', picked: 'Picked', note: 'Want to mix or adjust? (optional)', notePh: 'e.g. A’s colours with C’s motion',
    copied: 'Copied. Paste it back into the chat:', sent: 'Sent to the agent. You can close this page.', sound: 'Listen',
    reply: (l, n) => `I pick ${l}: ${n}`, more: 'Note: ',
  },
};

// directions: [{ id, letter, name, pitch, recommended, keywords, ratio: [w, h],
//   clip, poster, frames: [src], hasSound, palette: [{hex, name}], type: [{family, role}],
//   motion, music }]  (clip / poster / frames are URLs relative to the page)
export function buildMoodboardPage({ title = '', lang = 'en', directions, fontLinks = [] }) {
  const S = STRINGS[/^zh/.test(lang) ? 'zh' : 'en'];
  const specimen = title || 'Aa 永 0123';
  const card = (d) => {
    const [w, h] = d.ratio || [16, 9];
    const media = d.clip
      ? `<video src="${esc(d.clip)}"${d.poster ? ` poster="${esc(d.poster)}"` : ''} autoplay muted loop playsinline preload="auto"></video>`
      : d.poster ? `<img src="${esc(d.poster)}" alt="">` : '';
    return `
<article class="dir${d.recommended ? ' rec' : ''}" data-id="${esc(d.id)}" data-letter="${esc(d.letter)}" data-name="${esc(d.name)}">
  <header><span class="letter">${esc(d.letter)}</span><h2>${esc(d.name)}</h2>${d.recommended ? `<span class="tag">${S.recommended}</span>` : ''}</header>
  <div class="stage" style="aspect-ratio:${w}/${h}">${media}${d.clip && d.hasSound ? `<button class="snd" type="button" aria-pressed="false">♪ ${S.sound}</button>` : ''}</div>
  ${d.pitch ? `<p class="pitch">${esc(d.pitch)}</p>` : ''}
  ${d.keywords?.length ? `<p class="kw">${d.keywords.map((k) => `<span>${esc(k)}</span>`).join('')}</p>` : ''}
  ${d.frames?.length ? `<section><h3>${S.frames}</h3><div class="frames">${d.frames.map((f) => `<img src="${esc(f)}" alt="" style="aspect-ratio:${w}/${h}">`).join('')}</div></section>` : ''}
  ${d.palette?.length ? `<section><h3>${S.palette}</h3><div class="pal">${d.palette.map((c) => `<div class="sw"><i style="background:${esc(c.hex)}"></i><b>${esc(c.hex)}</b><small>${esc(c.name || '')}</small></div>`).join('')}</div></section>` : ''}
  ${d.type?.length ? `<section><h3>${S.type}</h3>${d.type.map((t) => `<div class="spec"><div class="sample" style="font-family:${esc(t.stack || `'${t.family}'`)}">${esc(t.sample || specimen)}</div><small>${esc(t.family)}${t.role ? ` · ${esc(t.role)}` : ''}</small></div>`).join('')}</section>` : ''}
  ${d.motion ? `<section><h3>${S.motion}</h3><p>${esc(d.motion)}</p></section>` : ''}
  ${d.music ? `<section><h3>${S.music}</h3><p>${esc(d.music)}</p></section>` : ''}
  <button class="pick" type="button">${S.pick} ${esc(d.letter)}</button>
</article>`;
  };
  return `<!doctype html>
<html lang="${/^zh/.test(lang) ? 'zh-CN' : 'en'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title || S.heading)}</title>
${[...new Set(fontLinks)].map((h) => `<link rel="stylesheet" href="${esc(h)}">`).join('\n')}
<style>
:root { --bg:#f4f3f0; --card:#fff; --ink:#18181a; --dim:#6d6c69; --line:#e2e0db; --accent:#2f5bea; }
@media (prefers-color-scheme: dark) { :root { --bg:#121214; --card:#1c1c1f; --ink:#ecebe8; --dim:#9a9994; --line:#2c2c30; --accent:#7f9cff; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui, -apple-system, "PingFang SC", "Noto Sans SC", sans-serif; }
main { max-width:1680px; margin:0 auto; padding:32px 16px 140px; }
.top h1 { margin:0 0 4px; font-size:26px; letter-spacing:-0.01em; }
.top p { margin:0 0 24px; color:var(--dim); max-width:70ch; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 340px), 1fr)); gap:20px; align-items:start; }
.dir { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; display:flex; flex-direction:column; gap:12px; transition:box-shadow .2s, border-color .2s; }
.dir.rec { border-color:color-mix(in srgb, var(--accent) 45%, var(--line)); }
.dir.chosen { border-color:var(--accent); box-shadow:0 0 0 3px color-mix(in srgb, var(--accent) 30%, transparent); }
.dir header { display:flex; align-items:center; gap:10px; }
.letter { width:30px; height:30px; flex:none; display:grid; place-items:center; border-radius:50%; background:var(--ink); color:var(--card); font-weight:700; }
.dir h2 { margin:0; font-size:18px; flex:1; }
.tag { font-size:12px; font-weight:600; color:var(--accent); border:1px solid currentColor; border-radius:99px; padding:1px 9px; }
.stage { position:relative; width:100%; max-height:62vh; margin:0 auto; background:#000; border-radius:8px; overflow:hidden; }
.stage video, .stage img { display:block; width:100%; height:100%; object-fit:contain; }
.snd { position:absolute; top:8px; right:8px; font:600 12px/1 system-ui, sans-serif; color:#fff; background:rgba(0,0,0,.6); border:0; padding:6px 10px; border-radius:99px; cursor:pointer; }
.snd[aria-pressed=true] { background:var(--accent); }
.pitch { margin:0; }
.kw { margin:0; display:flex; flex-wrap:wrap; gap:6px; }
.kw span { font-size:12px; color:var(--dim); border:1px solid var(--line); border-radius:99px; padding:1px 9px; }
section h3 { margin:0 0 6px; font-size:12px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--dim); }
section p { margin:0; }
.frames { display:grid; grid-template-columns:repeat(3, 1fr); gap:6px; }
.frames img { width:100%; object-fit:cover; border-radius:4px; background:#000; display:block; }
.pal { display:flex; flex-wrap:wrap; gap:8px; }
.sw { width:72px; display:flex; flex-direction:column; gap:2px; }
.sw i { height:40px; border-radius:6px; border:1px solid var(--line); }
.sw b { font:600 11px/1.2 ui-monospace, Menlo, monospace; }
.sw small, .spec small { color:var(--dim); font-size:11px; line-height:1.2; overflow-wrap:anywhere; }
.spec { margin-bottom:8px; }
.spec .sample { font-size:26px; line-height:1.25; overflow-wrap:anywhere; }
.pick { margin-top:auto; font:inherit; font-weight:600; padding:10px 14px; border-radius:10px; border:1px solid var(--ink); background:transparent; color:var(--ink); cursor:pointer; }
.pick:hover, .chosen .pick { background:var(--ink); color:var(--card); }
.bar { position:fixed; left:0; right:0; bottom:0; background:color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter:blur(8px); border-top:1px solid var(--line); padding:12px 16px; }
.bar div { max-width:1680px; margin:0 auto; display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
.bar label { color:var(--dim); font-size:13px; }
.bar input { flex:1; min-width:200px; font:inherit; padding:8px 10px; border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--ink); }
.bar output { width:100%; font-size:13px; }
.bar output code { background:var(--card); border:1px solid var(--line); border-radius:6px; padding:2px 6px; user-select:all; }
</style>
</head>
<body>
<main>
  <div class="top"><h1>${S.heading}</h1><p>${S.sub}</p></div>
  <div class="grid">${directions.map(card).join('\n')}</div>
</main>
<div class="bar"><div>
  <label for="note">${S.note}</label><input id="note" placeholder="${esc(S.notePh)}">
  <output id="out"></output>
</div></div>
<script>
const S = ${JSON.stringify({ copied: S.copied, sent: S.sent, picked: S.picked, pick: S.pick, more: S.more })};
const reply = ${S.reply.toString()};
const out = document.getElementById('out');
// one direction plays with sound at a time; the others stay muted
for (const btn of document.querySelectorAll('.snd')) {
  btn.addEventListener('click', () => {
    const on = btn.getAttribute('aria-pressed') !== 'true';
    for (const b of document.querySelectorAll('.snd')) { b.setAttribute('aria-pressed', 'false'); b.parentElement.querySelector('video').muted = true; }
    const v = btn.parentElement.querySelector('video');
    if (on) { btn.setAttribute('aria-pressed', 'true'); v.muted = false; v.currentTime = 0; v.play(); }
  });
}
for (const card of document.querySelectorAll('.dir')) {
  card.querySelector('.pick').addEventListener('click', async () => {
    document.querySelectorAll('.dir').forEach((c) => { c.classList.toggle('chosen', c === card); c.querySelector('.pick').textContent = (c === card ? S.picked : S.pick) + ' ' + c.dataset.letter; });
    const note = document.getElementById('note').value.trim();
    const text = reply(card.dataset.letter, card.dataset.name) + (note ? '\\n' + S.more + note : '');
    if (location.protocol.startsWith('http')) {
      try {
        const r = await fetch('pick', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ id: card.dataset.id, letter: card.dataset.letter, name: card.dataset.name, note }) });
        if (r.ok) { out.textContent = S.sent; return; }
      } catch {}
    }
    try { await navigator.clipboard.writeText(text); } catch {}
    out.innerHTML = '';
    out.append(S.copied + ' ');
    const code = document.createElement('code'); code.textContent = text; out.append(code);
  });
}
</script>
</body>
</html>
`;
}
