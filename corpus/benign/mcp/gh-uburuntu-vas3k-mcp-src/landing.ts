/**
 * Landing page for vas3k-mcp.rmbk.me — served at GET /.
 *
 * Self-contained <!doctype html> with inline CSS, no JS, no external assets
 * other than Ubuntu via Google Fonts (matches vas3k.club's --sans-font).
 * Visual tokens (colors, radii, shadows, fonts) lifted from
 * reference/frontend/static/css/theme.css and base.css to feel native.
 */

export const landingHtml: string = `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>MCP-сервер для Вастрик.Клуба</title>
<meta name="description" content="MCP-сервер для Клуба. Подключи Клуб к AI — поиск людей, цитаты из постов, ссылки прямо в чате." />
<meta property="og:title" content="MCP-сервер для Вастрик.Клуба" />
<meta property="og:description" content="Подключи Клуб к своему AI — чтобы умел искать людей, цитировать посты и подтягивать ссылки прямо в чате." />
<meta property="og:type" content="website" />
<meta property="og:image" content="https://vas3k-mcp.rmbk.me/img/cover.jpeg" />
<meta property="og:image:width" content="2886" />
<meta property="og:image:height" content="1344" />
<meta property="og:image:type" content="image/jpeg" />
<meta property="og:url" content="https://vas3k-mcp.rmbk.me/" />
<meta property="og:locale" content="ru_RU" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:image" content="https://vas3k-mcp.rmbk.me/img/cover.jpeg" />
<meta name="twitter:title" content="MCP-сервер для Вастрик.Клуба" />
<meta name="twitter:description" content="Подключи Клуб к своему AI — чтобы умел искать людей, цитировать посты и подтягивать ссылки прямо в чате." />
<meta name="theme-color" content="#FCFDFF" media="(prefers-color-scheme: light)" />
<meta name="theme-color" content="#282c35" media="(prefers-color-scheme: dark)" />
<link rel="icon" type="image/x-icon" href="/favicon.ico" sizes="32x32" />
<link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96" />
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
<link rel="manifest" href="/site.webmanifest" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&family=Ubuntu+Mono:wght@400;700&display=swap" />
<style>
:root {
  --sans-font: "Ubuntu", Helvetica, Verdana, sans-serif;
  --mono-font: "Ubuntu Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

  --block-border-radius: 15px;
  --button-border-radius: 15px;
  --accent: rgba(255, 196, 85, 0.91); /* --badge-color from vas3k theme */
  --accent-strong: #f7b733;
  --accent-soft: rgba(255, 196, 85, 0.18);

  /* light theme — copied from theme.css */
  --bg-color: #FCFDFF;
  --opposite-bg-color: #282c35;
  --text-color: #333;
  --brighter-text-color: #000;
  --opposite-text-color: #DDD;
  --block-bg-color: #FFF;
  --opposite-block-bg-color: #282c35;
  --block-shadow: 10px 15px 40px rgba(83, 91, 110, 0.11);
  --block-border: none;
  --link-color: #333;
  --link-hover-color: #000;
  --button-color: #FFF;
  --button-bg-color: #333;
  --button-border: solid 2px #333;
  --button-hover-color: #333;
  --button-hover-bg-color: #FFF;
  --button-hover-border: solid 2px #333;
  --muted: #6b7180;
  --hairline: rgba(0, 0, 0, 0.08);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-color: #282c35;
    --opposite-bg-color: #FCFDFF;
    --text-color: #DDD;
    --brighter-text-color: #FFF;
    --opposite-text-color: #333;
    --block-bg-color: #1B1B1C;
    --opposite-block-bg-color: #FFF;
    --block-shadow: 0 0 0 #000;
    --block-border: solid 1px #FCFDFF;
    --link-color: #DDD;
    --link-hover-color: #FFF;
    --button-color: #333;
    --button-bg-color: #FFF;
    --button-border: solid 2px #FFF;
    --button-hover-color: #FFF;
    --button-hover-bg-color: #333;
    --button-hover-border: solid 2px #FFF;
    --muted: #9aa0ad;
    --hairline: rgba(255, 255, 255, 0.12);
  }
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--sans-font);
  font-size: 17px;
  line-height: 1.5;
  color: var(--text-color);
  background-color: var(--bg-color);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

@media (max-width: 800px) { body { font-size: 15px; } }

a {
  color: var(--link-color);
  transition: color linear .1s;
  font-weight: 500;
}
a:hover { color: var(--link-hover-color); }

main {
  max-width: 920px;
  margin: 0 auto;
  padding: 40px 20px 20px;
}

@media (max-width: 570px) {
  main { padding: 20px 14px; }
}

/* hero */
.hero {
  padding: 48px 36px 44px;
  margin-bottom: 30px;
  background-color: var(--block-bg-color);
  border: var(--block-border);
  border-radius: var(--block-border-radius);
  box-shadow: var(--block-shadow);
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 32px;
}
.hero-text { position: relative; z-index: 1; min-width: 0; }
.hero-art {
  width: 280px;
  height: 280px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  perspective: 1000px;
}
.hero-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;

  /* Apple-icon-style squircle: 4-cubic Bezier supercircle, one cubic per
     quadrant so there are no curve joins (and therefore no tangent
     mismatches → no corner bulges). Control points sit at 17.86 instead
     of the 27.6 that would draw a true quarter circle, which flattens the
     sides into the squircle silhouette. SVG mask ensures the drop-shadow
     halo follows the squircle outline rather than a bounding rect. */
  --squircle: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100' preserveAspectRatio='none'><path fill='black' d='M0,50 C0,17.86 17.86,0 50,0 C82.14,0 100,17.86 100,50 C100,82.14 82.14,100 50,100 C17.86,100 0,82.14 0,50 Z'/></svg>");
  -webkit-mask-image: var(--squircle);
          mask-image: var(--squircle);
  -webkit-mask-size: 100% 100%;
          mask-size: 100% 100%;
  -webkit-mask-repeat: no-repeat;
          mask-repeat: no-repeat;

  /* Three CSS variables drive the transform: --tilt-x/y come from the
     mousemove handler at the bottom of the page (so the squircle leans
     toward the cursor, not a fixed angle); --hover-scale flips on
     :hover/:active. Composing them with var() means the hover scale
     respects the live tilt instead of replacing it. */
  --tilt-x: 0deg;
  --tilt-y: 0deg;
  --hover-scale: 1;
  transform: scale(var(--hover-scale))
             rotateX(var(--tilt-x))
             rotateY(var(--tilt-y));

  filter: drop-shadow(0 18px 32px rgba(255, 196, 85, 0.28));
  transition: transform 0.18s cubic-bezier(0.2, 0, 0, 1),
              filter 0.45s ease;
  cursor: pointer;
  user-select: none;
  -webkit-user-drag: none;
  will-change: transform;
}
/* Hover: scale up and warm the shadow. The actual tilt is set live by the
   mousemove handler, so the squircle leans toward wherever the cursor is. */
.hero-art:hover img {
  --hover-scale: 1.05;
  filter: drop-shadow(-12px 30px 42px rgba(255, 196, 85, 0.45));
}
/* Press: tactile recoil that still respects the current cursor tilt. */
.hero-art:active img {
  --hover-scale: 0.97;
  transition-duration: 0.12s;
}
/* Easter egg: 3 clicks → 2 smooth rotations. linear timing keeps the
   rotation rate constant (no perceptible "stop and continue" between
   keyframes); the scale pop happens during the lead-in/outro only.
   720° / 1.4s with the 15-85 keyframes is exactly 7.2°/% time = uniform. */
.hero-art img.spin {
  animation: heroSpin 1.4s linear;
}
@keyframes heroSpin {
  0%   { transform: scale(1)    rotate(0deg);    }
  15%  { transform: scale(1.08) rotate(108deg);  }
  85%  { transform: scale(1.08) rotate(612deg);  }
  100% { transform: scale(1)    rotate(720deg);  }
}
@media (prefers-reduced-motion: reduce) {
  .hero-art img,
  .hero-art:hover img,
  .hero-art:active img,
  .hero-art img.spin {
    transition: none;
    animation: none;
    transform: none;
  }
}
@media (max-width: 720px) {
  .hero { grid-template-columns: 1fr; gap: 18px; padding: 38px 28px 32px; }
  .hero-art { width: 200px; height: 200px; margin: 0 auto; order: -1; }
}

.hero-tag {
  display: inline-block;
  font-size: 13px;
  font-weight: 500;
  background: var(--accent);
  color: #333;
  padding: 5px 12px;
  border-radius: 999px;
  margin-bottom: 22px;
  position: relative;
  z-index: 1;
}

.hero h1 {
  position: relative;
  z-index: 1;
  margin: 0 0 18px;
  font-size: 52px;
  line-height: 1.05;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--brighter-text-color);
}

@media (max-width: 570px) { .hero h1 { font-size: 36px; } }

.hero p {
  position: relative;
  z-index: 1;
  margin: 0 0 26px;
  font-size: 21px;
  max-width: 620px;
  color: var(--text-color);
  opacity: 0.9;
}

@media (max-width: 570px) { .hero p { font-size: 17px; } }

.hero-cta {
  position: relative;
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none !important;
  padding: 14px 22px;
  border-radius: var(--button-border-radius);
  background-color: var(--button-bg-color);
  border: var(--button-border);
  color: var(--button-color);
  text-align: center;
  cursor: pointer;
  line-height: 1em;
  font-weight: 500;
  font-size: 16px;
  transition: 0.2s ease-out;
}
.button:hover {
  color: var(--button-hover-color);
  background-color: var(--button-hover-bg-color);
  border: var(--button-hover-border);
}
.button:focus-visible {
  outline: 2px solid var(--accent-strong);
  outline-offset: 2px;
}
.button-ghost {
  background: transparent;
  color: var(--text-color);
  border: solid 2px var(--hairline);
}
.button-ghost:hover {
  background: transparent;
  color: var(--brighter-text-color);
  border: solid 2px var(--text-color);
}

/* blocks */
.block {
  padding: 36px;
  margin-bottom: 30px;
  background-color: var(--block-bg-color);
  border: var(--block-border);
  border-radius: var(--block-border-radius);
  box-shadow: var(--block-shadow);
}
@media (max-width: 570px) { .block { padding: 22px; } }

.block h2 {
  margin: 0 0 16px;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--brighter-text-color);
  letter-spacing: -0.01em;
}

.block p { margin: 0 0 14px; }
.block p:last-child { margin-bottom: 0; }

.ai-ethics-title {
  margin: 26px 0 12px;
  font-size: 19px;
  font-weight: 700;
  color: var(--brighter-text-color);
  letter-spacing: -0.005em;
}

.lede {
  font-size: 18px;
  opacity: 0.92;
}

/* use-case examples — soft tinted blocks under "Что это и зачем" */
.examples {
  list-style: none;
  padding: 0;
  margin: 14px 0 0;
  display: grid;
  gap: 10px;
}
.examples li {
  padding: 12px 16px;
  border-radius: 10px;
  background: var(--accent-soft);
  font-size: 15px;
  line-height: 1.5;
}
.examples li strong { color: var(--brighter-text-color); }

/* tools grid */
.tools {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin-top: 22px;
}

.tool {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 12px;
  background: var(--accent-soft);
  border: 1px solid transparent;
  transition: transform .15s ease, border-color .15s ease;
}
.tool:hover {
  transform: translateY(-2px);
  border-color: var(--accent-strong);
}
.tool-emoji { font-size: 22px; line-height: 1; }
.tool-name { font-weight: 700; color: var(--brighter-text-color); }
.tool-desc { font-size: 14px; opacity: 0.78; line-height: 1.4; }

.tool-group-title {
  font-size: 1.05rem;
  margin: 28px 0 4px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.tool-group-title:first-of-type { margin-top: 8px; }
.tool-group-desc {
  font-size: 14px;
  opacity: 0.78;
  margin: 0;
  line-height: 1.5;
}
.tool-group-badge {
  display: inline-block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--brighter-text-color);
  letter-spacing: 0.02em;
}
.tool-group-badge-write {
  background: var(--accent);
  color: #1B1B1C;
}

/* per-client accordion */
.client {
  border-top: 1px solid var(--hairline);
  padding: 0;
}
.client:last-of-type { border-bottom: 1px solid var(--hairline); }
.client + .client { margin-top: 0; }
.client > summary {
  list-style: none;
  cursor: pointer;
  padding: 14px 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  user-select: none;
}
.client > summary::-webkit-details-marker { display: none; }
.client > summary::after {
  content: "+";
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 18px;
  font-weight: 600;
  width: 24px;
  text-align: center;
  opacity: 0.5;
  transition: transform .2s ease, opacity .2s ease;
}
.client[open] > summary::after { content: "−"; opacity: 1; }
.client > summary:hover { background: rgba(0,0,0,0.025); }
.client > summary:focus-visible {
  outline: 2px solid var(--accent-strong);
  outline-offset: -2px;
  border-radius: 8px;
}
@media (prefers-color-scheme: dark) {
  .client > summary:hover { background: rgba(255,255,255,0.04); }
}
.client-name {
  font-weight: 700;
  font-size: 16px;
  color: var(--brighter-text-color);
}
.client-where {
  font-size: 13px;
  opacity: 0.7;
  margin-left: auto;
  margin-right: 12px;
}
.client-where code.inline {
  font-size: 12px;
  background: rgba(0,0,0,0.06);
  padding: 1px 6px;
  border-radius: 4px;
}
@media (prefers-color-scheme: dark) {
  .client-where code.inline { background: rgba(255,255,255,0.08); }
}
.client-body {
  padding: 0 4px 16px;
  animation: clientReveal .25s ease-out;
}
.client-body p { margin: 4px 0 10px; }
.client-body em { font-style: normal; font-weight: 600; color: var(--brighter-text-color); }
@keyframes clientReveal {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: none; }
}
@media (max-width: 570px) {
  .client > summary { padding: 12px 2px; }
  .client-where { margin-left: 0; width: 100%; order: 3; }
}

/* "custom" client section — explanatory text alongside a sample screenshot */
.custom-grid {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  align-items: start;
  margin-top: 4px;
}
@media (max-width: 720px) {
  .custom-grid { grid-template-columns: 1fr; }
}
.custom-grid ul { margin: 8px 0 12px; padding-left: 1.2rem; }
.custom-grid li { margin: 4px 0; }
.custom-figure { margin: 0; text-align: center; }
.custom-figure img {
  max-width: 240px;
  width: 100%;
  height: auto;
  border-radius: 12px;
  border: 1px solid var(--hairline);
  display: block;
  margin: 0 auto;
}
.custom-figure figcaption {
  font-size: 12px;
  opacity: 0.65;
  margin-top: 8px;
}

/* Connection builder — checkbox toggle that swaps every /mcp ↔ /mcp-full
   inside the section via :checked + ~ sibling selectors. Pure CSS, no JS. */
.write-toggle-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}
.write-toggle {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  margin: 18px 0 22px;
  background: var(--accent-soft);
  border: 2px solid transparent;
  border-radius: 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s ease, border-color 0.2s ease;
}
.write-toggle:hover { border-color: rgba(247, 183, 51, 0.5); }
.write-toggle-input:focus-visible + .write-toggle {
  outline: 2px solid var(--accent-strong);
  outline-offset: 2px;
}
.write-toggle-input:checked + .write-toggle {
  background: rgba(255, 196, 85, 0.32);
  border-color: var(--accent-strong);
}
@media (prefers-color-scheme: dark) {
  .write-toggle-input:checked + .write-toggle { background: rgba(255, 196, 85, 0.18); }
}
.write-toggle-track {
  width: 42px; height: 24px;
  background: rgba(0, 0, 0, 0.18);
  border-radius: 999px;
  position: relative;
  flex-shrink: 0;
  transition: background 0.25s ease;
}
.write-toggle-knob {
  position: absolute;
  top: 2px; left: 2px;
  width: 20px; height: 20px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.write-toggle-input:checked + .write-toggle .write-toggle-track { background: #1B1B1C; }
.write-toggle-input:checked + .write-toggle .write-toggle-knob { transform: translateX(18px); }
.write-toggle-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.write-toggle-text strong {
  color: var(--brighter-text-color);
  font-size: 15px;
  font-weight: 600;
}
.write-toggle-sub {
  font-size: 13px;
  opacity: 0.72;
}
.write-toggle-badge {
  font-family: var(--mono-font);
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.06);
  color: var(--brighter-text-color);
  flex-shrink: 0;
  transition: background 0.2s ease, color 0.2s ease;
}
.write-toggle-input:checked + .write-toggle .write-toggle-badge {
  background: var(--accent-strong);
  color: #1B1B1C;
}
@media (prefers-color-scheme: dark) {
  .write-toggle-badge { background: rgba(255, 255, 255, 0.1); }
}
@media (max-width: 570px) {
  .write-toggle { flex-wrap: wrap; }
  .write-toggle-text { order: 3; flex-basis: 100%; }
}

/* URL hero — power-user shortcut. Big monospace URL that lives between the
   toggle and the per-client accordions; click anywhere on it to copy. The
   read/write swap reuses the same .read-snippet / .write-snippet classes the
   per-client snippets use, with extra rules below to scope the swap to
   .url-hero (which sits outside .builder). */
.url-hero { margin: 18px 0 26px; }
.url-hero pre { margin: 0; }
.url-hero pre > code {
  font-size: 22px;
  padding: 22px 26px;
  font-weight: 700;
  letter-spacing: -0.01em;
  /* Inherits the dark background + hover outline from the global
     pre.copyable:hover code rule below — so it already looks tappable. */
}
@media (max-width: 720px) {
  .url-hero pre > code { font-size: 18px; padding: 18px 20px; }
}
@media (max-width: 480px) {
  .url-hero pre > code { font-size: 14px; padding: 16px 16px; }
}

/* Default: read variants visible, write hidden. Swap on :checked. */
.connection-builder .write-url,
.connection-builder .write-snippet { display: none; }
.connection-builder .read-url { display: inline; }
.connection-builder .read-snippet { display: block; }
.connection-builder .write-toggle-input:checked ~ .write-toggle .read-url,
.connection-builder .write-toggle-input:checked ~ .url-hero .read-snippet,
.connection-builder .write-toggle-input:checked ~ .builder .read-url { display: none; }
.connection-builder .write-toggle-input:checked ~ .write-toggle .write-url,
.connection-builder .write-toggle-input:checked ~ .builder .write-url { display: inline; }
.connection-builder .write-toggle-input:checked ~ .url-hero .write-snippet,
.connection-builder .write-toggle-input:checked ~ .builder .write-snippet { display: block; }
.connection-builder .write-toggle-input:checked ~ .builder .read-snippet { display: none; }

/* Agent hint — lives OUTSIDE the "Как подключить" .block so the section
   boundary itself does the visual separation (no margin-top hacks). */
.agent-hint {
  margin: 0 0 30px;
  padding: 18px 22px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-strong);
  border-radius: var(--block-border-radius);
  font-size: 14px;
}
.agent-hint strong { color: var(--brighter-text-color); }
.agent-hint a { font-family: var(--mono-font); }

/* One-click copy — applied to <pre> snippets and the inline install
   command in the agent hint. Clicking anywhere on the element copies
   its text; "Скопировано" badge slides in for 1.5s. Click handler is
   at the bottom of <body>. */
.copyable {
  cursor: pointer;
  position: relative;
}
pre.copyable:hover code {
  outline: 2px solid var(--accent-strong);
  outline-offset: -2px;
  border-radius: 12px;
}
span.copyable {
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 5px;
  border-radius: 4px;
  border-bottom: 1px dotted currentColor;
  font-family: var(--mono-font);
  font-size: 0.92em;
  transition: background 0.15s ease, border-color 0.15s ease;
}
@media (prefers-color-scheme: dark) {
  span.copyable { background: rgba(255, 255, 255, 0.08); }
}
span.copyable:hover {
  background: rgba(255, 196, 85, 0.28);
  border-bottom-style: solid;
  border-bottom-color: var(--accent-strong);
}
.copyable::after {
  content: "Скопировано";
  position: absolute;
  top: -22px;
  right: 0;
  background: var(--accent-strong);
  color: #1B1B1C;
  font-family: var(--sans-font);
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 999px;
  opacity: 0;
  pointer-events: none;
  transform: translateY(2px);
  transition: opacity 0.18s ease, transform 0.18s ease;
  white-space: nowrap;
}
.copyable.copied::after {
  opacity: 1;
  transform: translateY(0);
}
pre.copyable::after {
  top: 8px;
  right: 10px;
}

/* code block — mirrors base.css "pre > code" */
pre {
  margin: 18px 0 8px;
  padding: 0;
}
pre > code {
  display: block;
  padding: 18px 22px;
  white-space: pre;
  overflow-x: auto;
  background-color: var(--opposite-block-bg-color);
  color: var(--opposite-text-color);
  border-radius: 12px;
  font-family: var(--mono-font);
  font-size: 14px;
  line-height: 1.55;
}
code.inline {
  font-family: var(--mono-font);
  font-size: 0.92em;
  padding: 2px 6px;
  border-radius: 5px;
  background: var(--accent-soft);
  color: var(--brighter-text-color);
}

/* security list */
.checklist {
  list-style: none;
  padding: 0;
  margin: 14px 0 0;
}
.checklist li {
  position: relative;
  padding: 8px 0 8px 32px;
  border-top: 1px solid var(--hairline);
}
.checklist li:first-child { border-top: 0; }
.checklist li::before {
  content: "✓";
  position: absolute;
  left: 6px;
  top: 8px;
  width: 20px;
  height: 20px;
  font-weight: 700;
  color: var(--accent-strong);
}

/* two-up row */
.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 30px;
}
@media (max-width: 720px) { .row { grid-template-columns: 1fr; } }
.row .block { margin-bottom: 0; height: 100%; }

/* footer */
footer {
  text-align: center;
  padding: 40px 20px 60px;
  font-size: 14px;
  opacity: 0.72;
  line-height: 1.7;
}
footer a { font-weight: 500; }
footer .sep { padding: 0 12px; opacity: 0.5; }
@media (max-width: 570px) {
  footer .sep { display: block; padding: 0; height: 4px; }
}
</style>
</head>
<body>
<main>

  <section class="hero">
    <div class="hero-text">
      <span class="hero-tag">✖️ Вастрик.Клуб MCP</span>
      <h1>MCP-сервер<br />для Клуба</h1>
      <p>Подключи Клуб к своему AI — чтобы умел искать людей, цитировать посты и подтягивать ссылки прямо в чате.</p>
      <div class="hero-cta">
        <a href="#подключить" class="button">Как подключить →</a>
        <a href="https://github.com/uburuntu/vas3k-mcp" class="button button-ghost" target="_blank" rel="noopener">GitHub</a>
      </div>
    </div>
    <div class="hero-art">
      <img src="/img/hero.webp" alt="" width="280" height="280" decoding="async" />
    </div>
  </section>

  <section class="block" id="зачем">
    <h2>Что это и зачем 🤔</h2>
    <p class="lede">
      <strong>MCP</strong> — способ дать AI-ассистентам ходить в живые API. Этот сервер подключает Клуб как обычное OAuth-приложение со страницы <a href="https://vas3k.club/apps/" target="_blank" rel="noopener">/apps/</a>.
    </p>
    <p>На практике:</p>
    <ul class="examples">
      <li><strong>Дайджест за неделю.</strong> «Что я пропустил в Клубе за неделю?» — AI тянет свежие посты из нужных лент, фильтрует по твоим тегам и собирает короткий пересказ.</li>
      <li><strong>Поиск своих.</strong> «Кто в Клубе пишет про Rust в проде?» — поиск по людям и тегам в один заход.</li>
      <li><strong>Длинный тред.</strong> «Перескажи спор в комментариях вот этого поста» — Markdown поста плюс ветка обсуждения.</li>
    </ul>
  </section>

  <section class="block connection-builder" id="подключить">
    <h2>Как подключить 🔌</h2>
    <p>Один URL, любой MCP-клиент. Включи переключатель ниже, если хочешь, чтобы AI мог ставить лайки, закладки и подписки от твоего имени — сниппеты ниже сразу обновятся.</p>

    <input type="checkbox" id="write-toggle" class="write-toggle-input" />
    <label for="write-toggle" class="write-toggle">
      <span class="write-toggle-track"><span class="write-toggle-knob"></span></span>
      <span class="write-toggle-text">
        <strong>Разрешать действия от твоего имени</strong>
        <span class="write-toggle-sub">лайки, закладки, подписки, друзья, теги</span>
      </span>
      <span class="write-toggle-badge"><span class="read-url">/mcp</span><span class="write-url">/mcp-full</span></span>
    </label>

    <div class="url-hero">
      <pre class="snippet read-snippet copyable" aria-label="MCP server URL — нажми, чтобы скопировать"><code>https://vas3k-mcp.rmbk.me/mcp</code></pre>
      <pre class="snippet write-snippet copyable" aria-label="MCP server URL — нажми, чтобы скопировать"><code>https://vas3k-mcp.rmbk.me/mcp-full</code></pre>
    </div>

    <div class="builder">
      <details class="client" open>
        <summary>
          <span class="client-name">ChatGPT (Web)</span>
          <span class="client-where">Settings → Apps → Advanced Settings → Developer mode → Create App</span>
        </summary>
        <div class="client-body">
          <p>Включи <em>Developer mode</em> в настройках, нажми <em>Create App</em>, заполни форму:</p>
          <ul>
            <li><em>Name</em> — любое (например, <code class="inline">vas3k</code>).</li>
            <li><em>MCP Server URL</em> — <code class="inline read-url">https://vas3k-mcp.rmbk.me/mcp</code><code class="inline write-url">https://vas3k-mcp.rmbk.me/mcp-full</code></li>
            <li><em>Authentication</em> — OAuth.</li>
          </ul>
          <p>Поставь галочку «I understand and want to continue» — это стандартное предупреждение OpenAI про сторонние MCP-серверы.</p>
        </div>
      </details>

      <details class="client">
        <summary>
          <span class="client-name">Claude Desktop</span>
          <span class="client-where">Settings → Connectors → Add Custom Connector</span>
        </summary>
        <div class="client-body">
          <p>В поле <em>URL</em> вставить:</p>
<pre class="snippet read-snippet copyable"><code>https://vas3k-mcp.rmbk.me/mcp</code></pre>
<pre class="snippet write-snippet copyable"><code>https://vas3k-mcp.rmbk.me/mcp-full</code></pre>
        </div>
      </details>

      <details class="client">
        <summary>
          <span class="client-name">Perplexity (Web)</span>
          <span class="client-where">Settings → Connectors → Add Connector</span>
        </summary>
        <div class="client-body">
          <p>В поле <em>Server URL</em> — адрес ниже, тип авторизации — OAuth:</p>
<pre class="snippet read-snippet copyable"><code>https://vas3k-mcp.rmbk.me/mcp</code></pre>
<pre class="snippet write-snippet copyable"><code>https://vas3k-mcp.rmbk.me/mcp-full</code></pre>
        </div>
      </details>

      <details class="client">
        <summary>
          <span class="client-name">Claude Code</span>
          <span class="client-where">Команда в терминале</span>
        </summary>
        <div class="client-body">
<pre class="snippet read-snippet copyable"><code>claude mcp add --transport http vas3k https://vas3k-mcp.rmbk.me/mcp</code></pre>
<pre class="snippet write-snippet copyable"><code>claude mcp add --transport http vas3k https://vas3k-mcp.rmbk.me/mcp-full</code></pre>
        </div>
      </details>

      <details class="client">
        <summary>
          <span class="client-name">Cursor</span>
          <span class="client-where"><code class="inline">~/.cursor/mcp.json</code></span>
        </summary>
        <div class="client-body">
<pre class="snippet read-snippet copyable"><code>{
  "mcpServers": {
    "vas3k": {
      "url": "https://vas3k-mcp.rmbk.me/mcp"
    }
  }
}</code></pre>
<pre class="snippet write-snippet copyable"><code>{
  "mcpServers": {
    "vas3k": {
      "url": "https://vas3k-mcp.rmbk.me/mcp-full"
    }
  }
}</code></pre>
        </div>
      </details>

      <details class="client">
        <summary>
          <span class="client-name">MCP Inspector</span>
          <span class="client-where">Отладочный клиент от Anthropic</span>
        </summary>
        <div class="client-body">
<pre class="copyable"><code>npx @modelcontextprotocol/inspector</code></pre>
          <p>В UI: <em>Transport</em> = Streamable HTTP, <em>URL</em> — <code class="inline read-url">https://vas3k-mcp.rmbk.me/mcp</code><code class="inline write-url">https://vas3k-mcp.rmbk.me/mcp-full</code></p>
        </div>
      </details>

      <details class="client">
        <summary>
          <span class="client-name">Любой другой клиент</span>
          <span class="client-where">Ручная настройка MCP</span>
        </summary>
        <div class="client-body">
          <div class="custom-grid">
            <div>
              <p>Большинство клиентов используют одни и те же поля. В форме «New connector» / «Add MCP server» нужно заполнить:</p>
              <ul>
                <li><em>Name</em> — любое имя (например, <code class="inline">vas3k</code>).</li>
                <li><em>MCP Server URL</em> — <code class="inline read-url">https://vas3k-mcp.rmbk.me/mcp</code><code class="inline write-url">https://vas3k-mcp.rmbk.me/mcp-full</code></li>
                <li><em>Authentication</em> — OAuth. Остальное клиент подтянет сам из <code class="inline">/.well-known/oauth-authorization-server</code>.</li>
              </ul>
              <p>Если клиент предупреждает про «небезопасные сторонние MCP» — это стандартное предупреждение, можно соглашаться.</p>
            </div>
            <figure class="custom-figure">
              <img src="/img/chatgpt-new-app.png" alt="Форма New App в ChatGPT" loading="lazy" />
              <figcaption>Например — форма из ChatGPT.</figcaption>
            </figure>
          </div>
        </div>
      </details>
    </div>

  </section>

  <p class="agent-hint">
    🤖 <strong>Если ты агент:</strong> открой <a href="/install.md">/install.md</a> — те же инструкции в Markdown. Или скажи своему агенту: «<span class="copyable">open https://vas3k-mcp.rmbk.me/install.md and install it for me</span>».
  </p>

  <section class="block" id="умеет">
    <h2>Что умеет 🛠</h2>

    <h3 class="tool-group-title">Только чтение <span class="tool-group-badge">/mcp</span></h3>
    <p class="tool-group-desc">Доступны на обоих URL. Ничего не меняют в Клубе.</p>
    <div class="tools">
      <div class="tool"><span class="tool-emoji" aria-hidden="true">👤</span><span class="tool-name">get_me</span><span class="tool-desc">Твой профиль</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🧑‍🚀</span><span class="tool-name">get_user</span><span class="tool-desc">Профиль участника по slug</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🏷</span><span class="tool-name">get_user_tags</span><span class="tool-desc">Теги в профиле</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🏆</span><span class="tool-name">get_user_badges</span><span class="tool-desc">Бейджи от других</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🎖</span><span class="tool-name">get_user_achievements</span><span class="tool-desc">Ачивки за активность</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">📲</span><span class="tool-name">find_user_by_telegram</span><span class="tool-desc">Найти по Telegram ID</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">📝</span><span class="tool-name">get_post</span><span class="tool-desc">Пост по типу и slug</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">📄</span><span class="tool-name">get_post_markdown</span><span class="tool-desc">Markdown поста</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">💬</span><span class="tool-name">list_post_comments</span><span class="tool-desc">Комментарии под постом</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">📰</span><span class="tool-name">get_feed</span><span class="tool-desc">Страница ленты с фильтрами</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🔍</span><span class="tool-name">search_users</span><span class="tool-desc">Поиск людей по префиксу</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🔖</span><span class="tool-name">search_tags</span><span class="tool-desc">Поиск тегов с фильтром группы</span></div>
    </div>

    <h3 class="tool-group-title">Действия от твоего имени <span class="tool-group-badge tool-group-badge-write">/mcp-full</span></h3>
    <p class="tool-group-desc">Только на <code class="inline">/mcp-full</code>. Лайки, закладки, подписки — AI ставит их от твоего имени, когда ты его об этом просишь.</p>
    <div class="tools">
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🔖</span><span class="tool-name">bookmark_post</span><span class="tool-desc">Добавить или убрать закладку</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">👍</span><span class="tool-name">upvote_post</span><span class="tool-desc">Лайкнуть пост</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">↩️</span><span class="tool-name">retract_post_vote</span><span class="tool-desc">Снять свой лайк с поста</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🔔</span><span class="tool-name">toggle_post_subscription</span><span class="tool-desc">Подписка на новые комментарии</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🎟</span><span class="tool-name">toggle_event_participation</span><span class="tool-desc">Отметиться на ивенте или сняться</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">💚</span><span class="tool-name">upvote_comment</span><span class="tool-desc">Лайкнуть комментарий</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">↩️</span><span class="tool-name">retract_comment_vote</span><span class="tool-desc">Снять лайк с комментария</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🫂</span><span class="tool-name">toggle_friend</span><span class="tool-desc">Отправить или отозвать запрос в друзья</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">📥</span><span class="tool-name">subscribe_room</span><span class="tool-desc">Подписаться на комнату</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🤐</span><span class="tool-name">mute_room</span><span class="tool-desc">Замьютить комнату</span></div>
      <div class="tool"><span class="tool-emoji" aria-hidden="true">🏷</span><span class="tool-name">toggle_profile_tag</span><span class="tool-desc">Переключить тег в профиле</span></div>
    </div>
  </section>

  <div class="row">
    <section class="block" id="безопасность">
      <h2>Приватность 🔒</h2>
      <ul class="checklist">
        <li>На <code class="inline">/mcp</code> — только чтение. На <code class="inline">/mcp-full</code> — то же самое плюс действия от твоего имени.</li>
        <li>OAuth ровно с теми же правами, что у любого приложения со страницы <a href="https://vas3k.club/apps/" target="_blank" rel="noopener">/apps/</a>.</li>
        <li>Доступ отзывается там же одной кнопкой.</li>
        <li>Токены шифруются ключом, который знает только этот сервер, перед записью в Cloudflare KV.</li>
        <li>Никакой телеметрии — данные едут только в твой AI-клиент.</li>
      </ul>

      <h3 class="ai-ethics-title">А что с обучением AI? 🧠</h3>
      <p>AI-приложение через MCP видит посты и комментарии других участников Клуба, в том числе из закрытых разделов. Если твой AI обучается на сообщениях пользователей, этот контент может попасть в обучение модели и теоретически попасть в чужие руки.</p>
      <p>Перед подключением открой настройки приватности своего AI-приложения и поищи раздел про обучение модели на твоих данных. В каждом приложении называется по-разному. Если такой опции вообще нет и ты не платишь за услуги — скорее всего, обучение включено по умолчанию.</p>
    </section>

    <section class="block" id="хостить">
      <h2>Свой инстанс 🏠</h2>
      <p>
        Код под MIT — можно поднять копию на своём Cloudflare-аккаунте. Шаги, секреты и KV-биндинги — в <a href="https://github.com/uburuntu/vas3k-mcp#self-host-on-cloudflare-workers" target="_blank" rel="noopener">README</a>.
      </p>
      <p>
        Исходники: <a href="https://github.com/uburuntu/vas3k-mcp" target="_blank" rel="noopener">github.com/uburuntu/vas3k-mcp</a>. Issues и PR — туда же.
      </p>
    </section>
  </div>

</main>

<footer>
  Неофициальный проект для <a href="https://vas3k.club" target="_blank" rel="noopener">vas3k.club</a>
  <span class="sep">∞</span>
  <a href="https://github.com/uburuntu/vas3k-mcp" target="_blank" rel="noopener">GitHub</a>
  <span class="sep">∞</span>
  <a href="https://vas3k.club/apps/" target="_blank" rel="noopener">/apps/</a>
</footer>

<script>
// Hero interactions. Two behaviours:
//   1. Cursor-following 3D tilt — derives ±8° rotateX/Y from the mouse
//      position relative to the element bounds and pushes them into CSS
//      vars (--tilt-x / --tilt-y). The transform itself is pure CSS.
//   2. Easter egg — 3 clicks within 700ms add the .spin class for the
//      duration of the @keyframes heroSpin animation.
(() => {
  const art = document.querySelector('.hero-art');
  if (!art) return;
  const img = art.querySelector('img');
  if (!img) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!reducedMotion) {
    art.addEventListener('mousemove', (e) => {
      if (img.classList.contains('spin')) return;
      const rect = art.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;   // 0..1
      const y = (e.clientY - rect.top) / rect.height;   // 0..1
      art.style.setProperty('--tilt-x', ((0.5 - y) * 16).toFixed(2) + 'deg');
      art.style.setProperty('--tilt-y', ((x - 0.5) * 16).toFixed(2) + 'deg');
    });
    art.addEventListener('mouseleave', () => {
      art.style.removeProperty('--tilt-x');
      art.style.removeProperty('--tilt-y');
    });
  }

  let clicks = 0;
  let timer = null;
  art.addEventListener('click', () => {
    if (img.classList.contains('spin')) return;
    clicks++;
    clearTimeout(timer);
    timer = setTimeout(() => { clicks = 0; }, 700);
    if (clicks >= 3) {
      clicks = 0;
      img.classList.add('spin');
      img.addEventListener(
        'animationend',
        () => img.classList.remove('spin'),
        { once: true },
      );
    }
  });
})();

// One-click copy for .copyable elements. <pre>: grab inner <code> text.
// Inline span: grab innerText. Briefly add .copied for the CSS badge.
(() => {
  document.querySelectorAll('.copyable').forEach((el) => {
    el.addEventListener('click', async () => {
      const target = el.tagName === 'PRE' ? el.querySelector('code') : el;
      const text = ((target || el).innerText || '').trim();
      try {
        await navigator.clipboard.writeText(text);
        el.classList.add('copied');
        setTimeout(() => el.classList.remove('copied'), 1500);
      } catch {
        // Clipboard blocked (insecure context). Select instead so the user
        // can ⌘C manually.
        const range = document.createRange();
        range.selectNodeContents(target || el);
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
      }
    });
  });
})();
</script>

</body>
</html>`;
