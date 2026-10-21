// Claudeweaver dev notes: shift+click any element to file a ticket on the board.
// Loaded in dev only. Everything renders inside one Shadow DOM root, and the
// only global is window.Claudeweaver.
(() => {
  if (window.Claudeweaver) return;
  // <script data-area="web" ...> sets the area of new notes; otherwise the board picks its first area.
  const AREA = document.currentScript?.dataset.area || undefined;
  const BOARD = (() => { try { return new URL(document.currentScript.src).origin; } catch { return "http://localhost:8090"; } })();
  const store = {
    get(k) { try { return localStorage.getItem("claudeweaver." + k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem("claudeweaver." + k, v); } catch {} },
  };

  // ---- pure helpers ----
  function selectorFor(el) {
    const unique = (s) => { try { return document.querySelectorAll(s).length === 1; } catch { return false; } };
    const attr = (n, v) => `[${n}="${String(v).replace(/["\\]/g, "\\$&")}"]`;
    const own = (e) => {
      const t = e.localName;
      if (e.id && !/\d{4,}|^[:_\d]|:/.test(e.id)) { const s = "#" + CSS.escape(e.id); if (unique(s)) return s; }
      for (const a of ["data-testid", "data-test", "aria-label"]) {
        const v = e.getAttribute(a); if (v) { const s = t + attr(a, v); if (unique(s)) return s; }
      }
      const role = e.getAttribute("role"); if (role) { const s = t + attr("role", role); if (unique(s)) return s; }
      return null;
    };
    const parts = [];
    for (let e = el; e && e.nodeType === 1 && e !== document.documentElement; e = e.parentElement) {
      const s = own(e);
      if (s) { parts.unshift(s); break; }
      let seg = e.localName;
      const p = e.parentElement;
      if (p) {
        const same = [...p.children].filter((c) => c.localName === e.localName);
        if (same.length > 1) seg += `:nth-of-type(${same.indexOf(e) + 1})`;
      }
      parts.unshift(seg);
      // Unanchored paths need some depth, or one new sibling elsewhere breaks them.
      if (parts.length >= 3 && unique(parts.join(" > "))) break;
    }
    return parts.join(" > ");
  }
  function parseNote(text, feature) {
    const lines = text.trim().split("\n");
    let title = lines[0].trim(), type = feature ? "feature" : "bug";
    const m = title.match(/^(feat|feature|bug)\s*:\s*/i);
    if (m) { type = /^b/i.test(m[1]) ? "bug" : "feature"; title = title.slice(m[0].length); }
    return { title, body: lines.slice(1).join("\n").trim(), type };
  }
  function place(r, w, h, vw, vh) {
    let left = r.right + 12, top = r.top;
    if (left + w > vw - 8) left = r.left - w - 12;
    if (left < 8) { left = r.left; top = r.bottom + 12; if (top + h > vh - 8) top = r.top - h - 12; }
    return { left: Math.max(8, Math.min(left, vw - w - 8)), top: Math.max(8, Math.min(top, vh - h - 8)) };
  }
  const elementText = (el) => (el.innerText || el.textContent || el.getAttribute("aria-label") || el.getAttribute("alt") || el.value || "").replace(/\s+/g, " ").trim().slice(0, 120);
  const openStatus = (s) => s !== "done" && s !== "wontfix";
  // Lucide icons (ISC), one per status, so status never rests on color alone.
  const ICONS = {
    inbox: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="1"/>',
    todo: '<circle cx="12" cy="12" r="10"/>',
    doing: '<path d="M10.1 2.182a10 10 0 0 1 3.8 0"/><path d="M13.9 21.818a10 10 0 0 1-3.8 0"/><path d="M17.609 3.721a10 10 0 0 1 2.69 2.7"/><path d="M2.182 13.9a10 10 0 0 1 0-3.8"/><path d="M20.279 17.609a10 10 0 0 1-2.7 2.69"/><path d="M21.818 10.1a10 10 0 0 1 0 3.8"/><path d="M3.721 6.391a10 10 0 0 1 2.7-2.69"/><path d="M6.391 20.279a10 10 0 0 1-2.69-2.7"/>',
    blocked: '<path d="M12 16h.01"/><path d="M12 8v4"/><path d="M15.312 2a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586l-4.688-4.688A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2z"/>',
    review: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    done: '<path d="M20 6 9 17l-5-5"/>',
    wontfix: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  };
  const icon = (s) => `<svg${s === "doing" ? ' class="spin"' : ""} viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[s] || ICONS.inbox}</svg>`;

  async function api(method, path, body, raw) {
    const r = await fetch(BOARD + path, {
      method, body: raw || (body ? JSON.stringify(body) : undefined),
      headers: raw ? { "Content-Type": raw.type || "image/png" } : body ? { "Content-Type": "application/json" } : {},
    });
    if (!r.ok) throw new Error((await r.text()).trim() || r.statusText);
    return r.json();
  }

  // ---- shadow root ----
  const host = document.createElement("claude-weaver");
  host.style.cssText = "all:initial;position:fixed;inset:0;pointer-events:none;z-index:2147483647;display:block;";
  const root = host.attachShadow({ mode: "open" });
  root.innerHTML = `<style>
:host { --on:#fff; --ink:#1A1C2B; --paper:#fff; --note:#DCE2FD; --raspberry:#3550F0; --cherry:#E8344E; --graphite:#5D6274; --line:#C9D1F5; --text:#1A1C2B; }
@media (prefers-color-scheme: dark) { :host { --paper:#1D1F2D; --note:#262D55; --raspberry:#6F82FF; --cherry:#FF5A70; --graphite:#A3A8BC; --line:#3A4272; --text:#E7E9F2; --on:#0F1019; } }
* { box-sizing: border-box; }
div, button, a, textarea, select, label { font: 500 13px/1.4 system-ui, -apple-system, sans-serif; color: var(--text); }
button { cursor: pointer; }
:focus-visible { outline: 2px solid var(--raspberry); outline-offset: 2px; }
[hidden] { display: none !important; }
.ui { pointer-events: auto; position: fixed; }
#hl { position: fixed; pointer-events: none; border: 2px solid var(--raspberry); border-radius: 4px; background: color-mix(in srgb, var(--raspberry) 8%, transparent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--raspberry) 18%, transparent); }
#hl.solid { border-style: solid; background: transparent; }
#note { width: 300px; background: var(--note); border-radius: 4px 14px 14px 14px; box-shadow: 0 10px 30px rgba(15,16,25,.22), 0 1px 0 var(--line) inset; padding: 12px 12px 10px; }
#note::before { content: ""; position: absolute; left: -5px; top: -5px; width: 12px; height: 12px; border-radius: 50%; background: var(--raspberry); box-shadow: 0 1px 2px rgba(0,0,0,.3); }
#note textarea { width: 100%; min-height: 76px; resize: vertical; border: 0; background: transparent; font-size: 15px; line-height: 1.45; outline: none; padding: 0; }
#note textarea::placeholder { color: var(--graphite); }
.row { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.seg button { border: 0; background: transparent; padding: 3px 10px; font-weight: 600; }
.seg button[aria-pressed=true] { background: var(--raspberry); color: var(--on); }
.hint { color: var(--graphite); font-size: 12px; margin-left: auto; }
.err { color: var(--cherry); font-size: 12px; margin-top: 6px; }
.pin { --c: #5D6274; display: inline-flex; align-items: center; gap: 3px; min-width: 22px; height: 22px; padding: 0 6px 0 5px; border-radius: 11px 11px 11px 3px; border: 2px solid #fff; background: var(--c); color: #fff; font-weight: 700; font-size: 11px; box-shadow: 0 2px 6px rgba(15,16,25,.3); transition: opacity .16s ease, transform .16s ease; }
.pin svg, .st svg, .btn svg { flex: none; }
.pin.gone { opacity: 0; transform: scale(.7); }
/* Muted status colors: white text on each passes 4.5:1, on light and dark pages alike. */
.s-todo { --c: #3550F0; } .s-doing { --c: #A35A00; } .s-blocked { --c: #B91C1C; } .s-review { --c: #7B3FC4; } .s-done { --c: #2E7D4F; } .s-wontfix { --c: #6B6F80; }
.st { display: inline-flex; align-items: center; gap: 4px; padding: 1px 7px 1px 5px; border-radius: 999px; font-size: 12px; font-weight: 600; color: var(--c, #5D6274); background: color-mix(in srgb, var(--c, #5D6274) 12%, transparent); }
@media (prefers-color-scheme: dark) { .st { color: color-mix(in srgb, var(--c, #5D6274) 45%, #fff); } }
.btn { display: inline-flex; align-items: center; gap: 5px; flex: none; }
/* The doing icon turns, so work in progress reads at a glance. */
.spin { animation: spin 1.2s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .pin { transition: none; } .spin, .thumb { animation: none; } }
#card { width: 300px; background: var(--paper); border-radius: 12px; border: 1px solid var(--line); box-shadow: 0 10px 30px rgba(15,16,25,.22); padding: 12px; }
#card h4 { margin: 0 0 4px; font: 700 14px/1.35 system-ui, sans-serif; color: var(--text); }
#card .meta { color: var(--graphite); font-size: 12px; }
#card .body { margin-top: 8px; max-height: 120px; overflow: auto; white-space: pre-wrap; }
#card select, #card textarea { width: 100%; border: 1px solid var(--line); border-radius: 8px; background: var(--paper); padding: 5px 8px; }
#card textarea { min-height: 52px; resize: vertical; margin-top: 8px; }
.btn { border: 1px solid var(--line); background: var(--paper); border-radius: 8px; padding: 4px 10px; font-weight: 600; text-decoration: none; }
.btn.primary { background: var(--raspberry); border-color: var(--raspberry); color: var(--on); }
/* A small tab on the right edge, halfway up, clear of composers and toolbars. */
#fab { right: 0; top: 50%; transform: translateY(-50%); width: 24px; height: 44px; border-radius: 10px 0 0 10px; opacity: .85; border: 0; background: var(--ink); color: #fff; font-weight: 700; font-size: 12px; box-shadow: 0 4px 14px rgba(15,16,25,.3); display: grid; place-items: center; padding: 0; }
#fab.has { background: var(--raspberry); }
#fab:hover, #fab:focus-visible { opacity: 1; width: 30px; }
#menu { right: 34px; top: 50%; transform: translateY(-50%); width: 250px; background: var(--paper); border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 10px 30px rgba(15,16,25,.22); padding: 6px; }
#menu button, #menu a, #menu label { display: flex; align-items: center; gap: 8px; width: 100%; padding: 7px 8px; border: 0; background: none; border-radius: 8px; text-decoration: none; text-align: left; }
#menu button:hover, #menu a:hover, #menu label:hover { background: color-mix(in srgb, var(--raspberry) 10%, transparent); }
#menu .tip { padding: 8px; color: var(--graphite); font-size: 12px; border-top: 1px solid var(--line); margin-top: 4px; }
#toast { right: 34px; top: calc(50% + 30px); background: var(--ink); color: #fff; border-radius: 10px; padding: 8px 12px; display: flex; gap: 10px; align-items: center; box-shadow: 0 6px 20px rgba(15,16,25,.3); }
/* Taps pass through the toast text to the page (picking mode); only its link is live. */
#toast { pointer-events: none; } #toast span { color: #fff; } #toast a { color: #AEBBFF; font-weight: 600; pointer-events: auto; }
kbd { font: 600 11px/1 ui-monospace, monospace; border: 1px solid var(--line); border-radius: 4px; padding: 1px 4px; }
#save { margin-left: auto; }
/* Chosen or pasted images, each with a remove button. */
.thumbs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.thumb { position: relative; width: 56px; height: 56px; animation: pop .14s ease-out; }
.thumb img { display: block; width: 100%; height: 100%; object-fit: cover; border-radius: 6px; border: 1px solid var(--line); }
.thumb button { position: absolute; top: -8px; right: -8px; width: 26px; height: 26px; border-radius: 50%; border: 2px solid var(--note); background: var(--ink); color: #fff; display: grid; place-items: center; padding: 0; }
@keyframes pop { from { opacity: 0; transform: scale(.85); } }
/* iOS Safari has no getDisplayMedia, so phones pick screenshots from Photos. */
#photos { display: none; position: relative; margin-top: 8px; }
#photos input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
@media (pointer: coarse) { #photos { display: inline-flex; } }
/* Touch: no Shift key, so the menu starts a pick and the note has a Save button. */
@media (pointer: coarse) { .row .hint { display: none; } #note textarea, #card textarea, #card select { font-size: 16px; } .pin { min-width: 28px; height: 28px; font-size: 12px; } }
@media (pointer: fine) { #save, #cancel { display: none; } }
/* Phones: note and card sit at the bottom, above the on-screen keyboard. */
@media (max-width: 520px) { #note, #card { left: 8px !important; right: 8px; top: auto !important; bottom: calc(8px + var(--kb, 0px)); width: auto; max-height: calc(100dvh - 16px - var(--kb, 0px)); overflow: auto; } #note::before { display: none; } #note { border-radius: 14px; } }
</style>
<div id="hl" hidden></div>
<div id="pins"></div>
<div id="note" class="ui" role="dialog" aria-label="New note" hidden>
  <textarea id="text" aria-label="Note" placeholder="What is wrong here? First line becomes the title. Paste or drop an image to attach it."></textarea>
  <div class="row">
    <span class="seg" role="group" aria-label="Kind"><button type="button" id="k-bug" aria-pressed="true">Bug</button><button type="button" id="k-feat" aria-pressed="false">Feature</button></span>
    <span class="hint"><kbd>Enter</kbd> save <kbd>Esc</kbd> cancel</span>
    <button type="button" class="btn" id="cancel">Cancel</button><button type="button" class="btn primary" id="save">Save</button>
  </div>
  <label class="btn" id="photos"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 5h6"/><path d="M19 2v6"/><path d="M21 11.5V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7.5"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/><circle cx="9" cy="9" r="2"/></svg>Choose from Photos<input type="file" id="file" accept="image/*" multiple></label>
  <div class="thumbs" id="note-imgs" hidden></div>
  <div class="err" id="note-err" hidden></div>
</div>
<div id="card" class="ui" role="dialog" aria-label="Note" hidden></div>
<div id="menu" class="ui" hidden>
  <button type="button" id="m-pick">Drop a note</button>
  <button type="button" id="m-pins"></button>
  <a id="m-board" target="_blank" rel="noopener">Open the board</a>
  <label id="m-shots-row"><input type="checkbox" id="m-shots"> Attach screenshots</label>
  <div class="tip"><kbd>Shift</kbd>+click anything to drop a note, or choose Drop a note and tap it. <kbd>Shift</kbd>+<kbd>D</kbd> hides all of this.</div>
</div>
<button id="fab" class="ui" type="button" aria-label="Dev notes"></button>
<div id="toast" class="ui" role="status" hidden></div>`;
  const $ = (id) => root.getElementById(id);
  // Keep our typing and clicks away from the host app's handlers.
  for (const t of ["keydown", "keyup", "keypress", "input", "click", "mousedown", "pointerdown", "mouseup", "pointerup", "dblclick", "paste", "dragover", "drop"]) root.addEventListener(t, (e) => e.stopPropagation());

  let enabled = store.get("off") !== "1";
  let pinsOn = store.get("pins") !== "0";
  let notes = [];
  let target = null, feature = false, stream = null, mx = 0, my = 0, picking = false;
  const inOverlay = (e) => e.composedPath().includes(host);

  // ---- highlight ----
  function highlight(el) {
    const hl = $("hl");
    if (!el || !enabled || !pinsOn) { hl.hidden = true; return; }
    const r = el.getBoundingClientRect();
    Object.assign(hl.style, { left: r.left - 3 + "px", top: r.top - 3 + "px", width: r.width + 6 + "px", height: r.height + 6 + "px" });
    hl.hidden = false;
  }
  const noteOpen = () => !$("note").hidden;

  // ---- sticky note ----
  function setKind(f) { feature = f; if (target && $("text").value) $("text").dispatchEvent(new Event("input")); $("k-bug").setAttribute("aria-pressed", !f); $("k-feat").setAttribute("aria-pressed", f); }
  $("k-bug").onclick = () => { setKind(false); $("text").focus(); };
  $("k-feat").onclick = () => { setKind(true); $("text").focus(); };
  function openNote(el) {
    target = el; hideCard(); highlight(el); $("menu").hidden = true;
    $("note-err").hidden = true;
    setKind(false);
    $("note").hidden = false;
    positionNote();
    $("text").focus();
  }
  function positionNote() {
    if (!target) return;
    const p = place(target.getBoundingClientRect(), 300, $("note").offsetHeight || 150, innerWidth, innerHeight);
    Object.assign($("note").style, { left: p.left + "px", top: p.top + "px" });
  }
  $("save").onclick = () => save();
  $("cancel").onclick = () => closeNote();
  // Keep the bottom sheet above the on-screen keyboard.
  const vv = window.visualViewport;
  if (vv) { const kb = () => host.style.setProperty("--kb", Math.max(0, innerHeight - vv.height - vv.offsetTop) + "px"); vv.addEventListener("resize", kb); vv.addEventListener("scroll", kb); }
  function closeNote() { $("note").hidden = true; $("text").value = ""; target = null; highlight(null); queue([]); store.set("draft", ""); }

  // The draft survives a reload (dev servers reload often). Images are not kept.
  $("text").addEventListener("input", () => {
    if (target) store.set("draft", JSON.stringify({ url: location.href, sel: selectorFor(target), text: $("text").value, feature }));
  });
  function restoreDraft() {
    let d; try { d = JSON.parse(store.get("draft") || "null"); } catch {}
    if (!d || d.url !== location.href || !d.text) return;
    openNote(findEl(d.sel) || document.body);
    setKind(!!d.feature);
    $("text").value = d.text;
  }

  // Pasted or dropped images: queued on a new note, uploaded right away on an open card.
  let queued = [], cardId = null;
  const imagesIn = (dt) => [...(dt?.files || [])].filter((f) => f.type.startsWith("image/"));
  // The board takes PNG, JPEG or WebP up to 5 MB. Anything else (a big photo,
  // HEIC) is redrawn as a JPEG, smaller each try, until it fits.
  const MAX = 5 << 20;
  async function fit(f) {
    if (f.size <= MAX && /^image\/(png|jpeg|webp)$/.test(f.type)) return f;
    const bmp = await createImageBitmap(f), c = document.createElement("canvas");
    for (let s = Math.min(1, 4096 / Math.max(bmp.width, bmp.height)); s > 0.05; s *= 0.7) {
      c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
      c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
      const b = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.85));
      if (b && b.size <= MAX) return b;
    }
    throw new Error("image too large");
  }
  async function addImages(f) {
    const out = [];
    for (const x of f) {
      try { out.push(await fit(x)); } catch { $("note-err").textContent = `Could not attach ${x.name || "an image"}.`; $("note-err").hidden = false; }
    }
    queue([...queued, ...out]);
  }
  function takeImages(el, onFiles) {
    const files = (dt) => !!dt && [...dt.types].includes("Files");
    el.addEventListener("paste", (e) => { const f = imagesIn(e.clipboardData); if (f.length) { e.preventDefault(); onFiles(f); } });
    el.addEventListener("dragover", (e) => { if (files(e.dataTransfer)) e.preventDefault(); });
    el.addEventListener("drop", (e) => { if (files(e.dataTransfer)) { e.preventDefault(); onFiles(imagesIn(e.dataTransfer)); } });
  }
  function queue(f) {
    queued = f;
    const box = $("note-imgs");
    box.innerHTML = "";
    f.forEach((file, i) => {
      const d = document.createElement("div"); d.className = "thumb";
      const img = document.createElement("img"); img.alt = `Image ${i + 1}`;
      img.src = URL.createObjectURL(file); img.onload = img.onerror = () => URL.revokeObjectURL(img.src);
      const x = document.createElement("button"); x.type = "button"; x.setAttribute("aria-label", `Remove image ${i + 1}`);
      x.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">${ICONS.wontfix}</svg>`;
      x.onclick = () => queue(queued.filter((_, j) => j !== i));
      d.append(img, x); box.append(d);
    });
    box.hidden = !f.length;
  }
  takeImages($("note"), async (f) => { await addImages(f); $("text").focus(); });
  $("file").onchange = async () => { const f = [...$("file").files]; $("file").value = ""; await addImages(f); };
  takeImages($("card"), async (f) => {
    const id = cardId;
    for (const x of f) await fit(x).then((b) => api("POST", `/api/tickets/${id}/screenshot`, null, b)).catch(() => {});
    if (f.length) toast(id, `Added ${f.length === 1 ? "an image" : f.length + " images"} to #${id}`);
  });
  $("text").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.preventDefault(); closeNote(); }
    else if (e.key === "Enter" && (!e.shiftKey || e.metaKey || e.ctrlKey)) { e.preventDefault(); save(); }
  });
  async function save() {
    const text = $("text").value;
    if ((!text.trim() && !queued.length) || !target) return;
    const n = parseNote(text, feature), el = target, rect = el.getBoundingClientRect(), files = queued;
    const ticket = {
      title: n.title || "Screenshot", body: n.body, type: n.type, status: "inbox", priority: "p2", area: AREA, source: "devnote",
      url: location.href, selector: selectorFor(el), element_text: elementText(el), viewport: innerWidth + "x" + innerHeight,
    };
    $("note").hidden = true;
    // Start the capture now, while the keypress still counts as a user
    // gesture, but never let a pending permission prompt hold up the ticket.
    const shot = store.get("shots") === "1" ? grab(rect).catch(() => null) : null;
    try {
      const t = await api("POST", "/api/tickets", ticket);
      closeNote();
      const png = await shot;
      toast(t.id);
      loadPins();
      for (const img of png ? [...files, png] : files) await api("POST", `/api/tickets/${t.id}/screenshot`, null, img).catch(() => {});
    } catch (err) {
      $("note").hidden = false; positionNote();
      $("note-err").textContent = `Not saved: ${BOARD} did not answer (${err.message}). Is the board running?`;
      $("note-err").hidden = false;
    }
  }

  // Screenshots: getDisplayMedia asks permission, so it only runs when the user
  // turns it on. The stream is kept for the session so they are asked once.
  const within = (p, ms) => Promise.race([p, new Promise((r) => setTimeout(r, ms))]);
  async function grab(rect) {
    if (!stream || !stream.active) {
      stream = await navigator.mediaDevices.getDisplayMedia({ video: { displaySurface: "browser" }, audio: false, preferCurrentTab: true, selfBrowserSurface: "include" });
      stream.getVideoTracks()[0].addEventListener("ended", () => { stream = null; });
    }
    const v = document.createElement("video");
    v.muted = true; v.srcObject = stream;
    const c = document.createElement("canvas");
    // Hide our pins, then wait for a frame painted after that (each step
    // gives up after a moment: a still page sends no new frames).
    host.style.visibility = "hidden";
    try {
      await within(v.play(), 1000);
      await within(new Promise((r) => v.requestVideoFrameCallback(() => v.requestVideoFrameCallback(r))), 600);
      if (!v.videoWidth) throw new Error("no video frame");
      const sx = v.videoWidth / innerWidth, sy = v.videoHeight / innerHeight, pad = 160;
      const x = Math.max(0, rect.left - pad), y = Math.max(0, rect.top - pad);
      const w = Math.min(innerWidth, rect.right + pad) - x, h = Math.min(innerHeight, rect.bottom + pad) - y;
      c.width = Math.max(1, Math.round(w * sx)); c.height = Math.max(1, Math.round(h * sy));
      c.getContext("2d").drawImage(v, x * sx, y * sy, w * sx, h * sy, 0, 0, c.width, c.height);
    } finally {
      host.style.visibility = "";
      v.pause(); v.srcObject = null;
    }
    return new Promise((r) => c.toBlob(r, "image/png"));
  }

  let toastTimer;
  function toast(id, text) {
    const t = $("toast");
    t.innerHTML = "";
    const s = document.createElement("span"); s.textContent = text || `Ticket #${id} created`;
    t.append(s);
    if (id) { const a = document.createElement("a"); a.href = `${BOARD}/#t=${id}`; a.target = "_blank"; a.rel = "noopener"; a.textContent = "Open on board"; t.append(a); }
    t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 5000);
  }

  // ---- pins ----
  async function loadPins() {
    if (!enabled) return;
    try {
      notes = (await api("GET", "/api/tickets?url=" + encodeURIComponent(location.href))).filter((t) => openStatus(t.status));
    } catch { notes = []; }
    renderPins();
  }
  function findEl(sel) { try { return sel ? document.querySelector(sel) : null; } catch { return null; } }
  function renderPins() {
    const box = $("pins");
    box.innerHTML = "";
    $("fab").textContent = notes.length || "+";
    $("fab").classList.toggle("has", notes.length > 0);
    $("fab").setAttribute("aria-label", `Dev notes: ${notes.length} open on this page`);
    if (!pinsOn || !enabled) return;
    for (const t of notes) {
      const b = document.createElement("button");
      b.className = `pin ui s-${t.status}`; b.type = "button"; b.innerHTML = icon(t.status); b.append(t.id); b.dataset.id = t.id;
      b.setAttribute("aria-label", `Note #${t.id}, ${t.status}: ${t.title}`); b.title = `${t.status}: ${t.title}`;
      b.onclick = () => showCard(t, b);
      box.append(b);
    }
    positionPins();
  }
  function positionPins() {
    for (const b of $("pins").children) {
      const t = notes.find((n) => String(n.id) === b.dataset.id);
      const el = t && findEl(t.selector), r = el && el.getBoundingClientRect();
      if (!r || (!r.width && !r.height) || r.bottom < 0 || r.top > innerHeight) { b.hidden = true; continue; }
      b.hidden = false;
      b.style.left = Math.min(innerWidth - 40, Math.max(2, r.right - 12)) + "px";
      b.style.top = Math.max(2, r.top - 12) + "px";
    }
    if (noteOpen()) { highlight(target); positionNote(); }
  }
  let raf = 0;
  const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; positionPins(); }); };
  addEventListener("scroll", schedule, { capture: true, passive: true });
  addEventListener("resize", schedule, { passive: true });
  setInterval(schedule, 1000); // the app may re-render under a pin
  setInterval(() => { if (!document.hidden) loadPins(); }, 15000);

  function hideCard() { $("card").hidden = true; }
  function showCard(t, pin) {
    const c = $("card"); cardId = t.id;
    c.innerHTML = "";
    const h = document.createElement("h4"); h.textContent = t.title;
    const meta = document.createElement("div"); meta.className = "meta row";
    const st = document.createElement("span"); st.className = `st s-${t.status}`; st.innerHTML = icon(t.status); st.append(t.status);
    meta.append(st, `#${t.id}, ${t.type}, ${t.priority}`); meta.style.marginTop = "0";
    const body = document.createElement("div"); body.className = "body"; body.textContent = t.body || ""; body.hidden = !t.body;
    const sel = document.createElement("select"); sel.setAttribute("aria-label", "Status");
    for (const s of ["inbox", "todo", "doing", "blocked", "review", "done", "wontfix"]) sel.append(new Option(s, s, false, s === t.status));
    const note = document.createElement("textarea"); note.placeholder = "Add a note"; note.setAttribute("aria-label", "Add a note");
    const err = document.createElement("div"); err.className = "err"; err.hidden = true;
    const row = document.createElement("div"); row.className = "row";
    const statusRow = document.createElement("div"); statusRow.className = "row"; statusRow.append(sel);
    const add = document.createElement("button"); add.className = "btn primary"; add.type = "button"; add.textContent = "Add note";
    const open = document.createElement("a"); open.className = "btn"; open.href = `${BOARD}/#t=${t.id}`; open.target = "_blank"; open.rel = "noopener"; open.textContent = "Open on board";
    row.append(add, open);
    if (t.status === "review") {
      const done = document.createElement("button"); done.className = "btn primary"; done.type = "button"; done.innerHTML = icon("done"); done.append("Done");
      done.onclick = async () => {
        done.disabled = true;
        try {
          await api("PATCH", `/api/tickets/${t.id}`, { status: "done" });
          hideCard();
          // Done pins are hidden: fade this one out, then refresh.
          const p = $("pins").querySelector(`[data-id="${t.id}"]`);
          if (p) p.classList.add("gone");
          setTimeout(loadPins, matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 160);
        } catch (e) { done.disabled = false; fail(e); }
      };
      statusRow.prepend(done);
    }
    c.append(h, meta, body, statusRow, note, row, err);
    const fail = (e) => { err.textContent = e.message; err.hidden = false; };
    sel.onchange = async () => {
      try { const u = await api("PATCH", `/api/tickets/${t.id}`, { status: sel.value }); if (!openStatus(u.status)) hideCard(); loadPins(); } catch (e) { fail(e); }
    };
    add.onclick = async () => {
      if (!note.value.trim()) return;
      try { await api("POST", `/api/tickets/${t.id}/notes`, { text: note.value, by: "human" }); note.value = ""; add.textContent = "Added"; setTimeout(() => { add.textContent = "Add note"; }, 1500); } catch (e) { fail(e); }
    };
    c.hidden = false;
    const p = place(pin.getBoundingClientRect(), 300, c.offsetHeight, innerWidth, innerHeight);
    Object.assign(c.style, { left: p.left + "px", top: p.top + "px" });
    (statusRow.querySelector("button") || sel).focus();
    const el = findEl(t.selector); if (el) { highlight(el); setTimeout(() => { if (!noteOpen()) highlight(null); }, 1500); }
  }

  // ---- floating button and menu ----
  function syncMenu() {
    $("m-pins").textContent = pinsOn ? "Hide pins" : "Show pins";
    $("m-board").href = BOARD + "/";
    $("m-shots").checked = store.get("shots") === "1";
    $("m-shots-row").hidden = !navigator.mediaDevices?.getDisplayMedia;
  }
  $("fab").onclick = () => { if (picking) return pick(false); $("menu").hidden = !$("menu").hidden; syncMenu(); };
  function pick(on) {
    picking = on; $("menu").hidden = true;
    if (on) { if (!pinsOn) { pinsOn = true; store.set("pins", "1"); renderPins(); } toast(null, "Tap anything to drop a note"); clearTimeout(toastTimer); }
    else { $("toast").hidden = true; if (!noteOpen()) highlight(null); }
  }
  $("m-pick").onclick = () => pick(true);
  $("m-pins").onclick = () => { pinsOn = !pinsOn; store.set("pins", pinsOn ? "1" : "0"); syncMenu(); renderPins(); };
  $("m-shots").onchange = () => {
    store.set("shots", $("m-shots").checked ? "1" : "0");
    if (!$("m-shots").checked && stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  };

  function setEnabled(on) {
    enabled = on; store.set("off", on ? "0" : "1");
    for (const id of ["fab", "pins"]) $(id).hidden = !on;
    if (!on) { closeNote(); hideCard(); $("menu").hidden = true; $("toast").hidden = true; }
    else loadPins();
  }

  // ---- page events ----
  const editable = (e) => { const t = e.composedPath()[0]; return t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)); };
  addEventListener("keydown", (e) => {
    if (e.key === "Shift" && enabled && !noteOpen()) { const el = document.elementFromPoint(mx, my); if (el && el !== host) highlight(el); }
    if ((e.key === "D" || e.key === "d") && e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey && !editable(e)) { e.preventDefault(); setEnabled(!enabled); }
    if (e.key === "Escape" && !$("card").hidden) hideCard();
    if (e.key === "Escape" && picking) pick(false);
  }, true);
  addEventListener("keyup", (e) => { if (e.key === "Shift" && !noteOpen()) highlight(null); }, true);
  addEventListener("mousemove", (e) => {
    mx = e.clientX; my = e.clientY;
    if (!enabled || noteOpen()) return;
    if (e.shiftKey && !inOverlay(e)) highlight(e.target); else if (!$("hl").hidden) highlight(null);
  }, { capture: true, passive: true });
  const block = (e) => {
    if (!enabled || !pinsOn || !(e.shiftKey || picking) || e.button !== 0 || inOverlay(e)) return;
    e.preventDefault(); e.stopImmediatePropagation();
    if (picking && e.type === "pointerdown") highlight(e.target);
    if (e.type === "click") { if (picking) pick(false); openNote(e.target); }
  };
  for (const t of ["pointerdown", "mousedown", "pointerup", "mouseup", "click", "dblclick"]) addEventListener(t, block, true);
  addEventListener("click", (e) => {
    if (inOverlay(e)) return;
    if (!$("card").hidden) hideCard();
    if (!$("menu").hidden) $("menu").hidden = true;
  }, true);

  // SPA navigation: reload pins after the route changes.
  let navTimer;
  const onNav = () => { clearTimeout(navTimer); navTimer = setTimeout(loadPins, 300); };
  for (const m of ["pushState", "replaceState"]) {
    const orig = history[m];
    history[m] = function (...args) { const r = orig.apply(this, args); onNav(); return r; };
  }
  addEventListener("popstate", onNav);
  addEventListener("hashchange", onNav);

  // A modal dialog makes everything outside it inert, and clicks on inert
  // nodes land on its backdrop and close it. So while one is open, live inside
  // it, as a manual popover so we stay in the top layer above it.
  host.popover = "manual";
  function rehome() {
    const parent = [...document.querySelectorAll("dialog:modal")].pop() || document.documentElement;
    if (host.parentNode === parent) return;
    parent.appendChild(host);
    host.showPopover();
    if (noteOpen()) $("text").focus();
  }
  function mount() {
    rehome();
    new MutationObserver(rehome).observe(document.documentElement, { childList: true, subtree: true, attributeFilter: ["open"] });
    syncMenu();
    setEnabled(enabled);
    if (enabled) restoreDraft();
  }
  if (document.body) mount(); else addEventListener("DOMContentLoaded", mount);

  window.Claudeweaver = { board: BOARD, toggle: () => setEnabled(!enabled), reload: loadPins };
})();
