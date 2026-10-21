#!/usr/bin/env node
// scaffold-lesson.mjs - create a draft lesson shell in ./lessons/.
// Run from the teach skill directory:
//   node scripts/scaffold-lesson.mjs "Lesson title" [--slug lesson-slug]
import { existsSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { basename, join, resolve } from "node:path";

const args = process.argv.slice(2);

function usage(exitCode = 2) {
  const out = exitCode === 0 ? console.log : console.error;
  out("usage: node scripts/scaffold-lesson.mjs \"Lesson title\" [--slug lesson-slug]");
  process.exit(exitCode);
}

let explicitSlug = "";
const titleParts = [];
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === "-h" || arg === "--help") usage(0);
  if (arg === "--slug") {
    explicitSlug = args[++i] || "";
    continue;
  }
  if (arg.startsWith("--slug=")) {
    explicitSlug = arg.slice("--slug=".length);
    continue;
  }
  titleParts.push(arg);
}

const title = titleParts.join(" ").trim();
if (!title) usage();

const cwd = process.cwd();
const expectedFiles = ["SKILL.md", "assets/lesson-kit.css", "assets/lesson-kit.js"];
const missing = expectedFiles.filter(file => !existsSync(resolve(cwd, file)));
if (missing.length) {
  console.error("error: run this from the teach skill directory");
  console.error(`missing: ${missing.join(", ")}`);
  process.exit(1);
}

function slugify(value) {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

let slug = slugify(explicitSlug || title);
if (!slug || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)) {
  console.error(`error: could not derive a valid slug from "${explicitSlug || title}"`);
  console.error("slug must contain at least one ASCII letter or digit");
  process.exit(1);
}

function ordinalsFrom(dir) {
  const full = resolve(cwd, dir);
  if (!existsSync(full)) return [];
  return readdirSync(full, { withFileTypes: true })
    .filter(entry => entry.isFile())
    .map(entry => entry.name.match(/^(\d{4})-[a-z0-9][a-z0-9-]*\.html$/))
    .filter(Boolean)
    .map(match => Number(match[1]))
    .filter(Number.isFinite);
}

const lessonOrdinals = ordinalsFrom("lessons");
const seedOrdinals = lessonOrdinals.length ? lessonOrdinals : ordinalsFrom("examples");
const next = Math.max(0, ...seedOrdinals) + 1;
const ordinal = String(next).padStart(4, "0");
const shortOrdinal = String(next).padStart(2, "0");
const lessonsDir = resolve(cwd, "lessons");
const outFile = join(lessonsDir, `${ordinal}-${slug}.html`);

if (existsSync(outFile)) {
  console.error(`error: refusing to overwrite existing ${outFile}`);
  process.exit(1);
}

function escapeHtml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const safeTitle = escapeHtml(title);
const safeSlug = escapeHtml(slug);

const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${shortOrdinal} - ${safeTitle}</title>
<meta name="teach:lesson" content="${ordinal}">
<meta name="teach:contract" content="v1">
<meta name="description" content="${safeTitle}">
<style id="kit"></style>
<style id="page">
  /* Page-specific layout only. Prefer kit tokens and classes. */
</style>
</head>
<body>
<main class="lesson">

  <header class="lesson-head">
    <span class="ordinal">Lesson ${ordinal} - Topic</span>
    <h1>${safeTitle}</h1>
    <p class="mission">Tie this lesson to the learner's mission in one sentence.</p>
  </header>

  <p class="lede">Name the one tangible win the learner will have by the end.</p>

  <div class="section-label">Concept</div>
  <p>Explain the smallest useful idea first, in plain language, then pair it with one
    load-bearing visual treatment from the map.</p>

  <div class="callout callout--rule">
    <span class="callout__k">Rule</span>
    State the compact rule the learner should be able to reuse later.
  </div>

  <div class="section-label">Worked example</div>
  <div class="worked">
    <p>Use a real example. Ask the learner to predict each step before revealing it.</p>
    <div class="worked__step" data-id="${safeSlug}-step-1">
      <strong>1. First move.</strong>
      <button class="worked__reveal">reveal</button>
      <span class="worked__answer">Show the first move and why it works.</span>
    </div>
    <div class="worked__step" data-id="${safeSlug}-step-2">
      <strong>2. Transfer.</strong>
      <button class="worked__reveal">reveal</button>
      <span class="worked__answer">Ask for more from the learner as support fades.</span>
    </div>
  </div>

  <div class="section-label">Recall <span class="recall-score"></span></div>
  <div class="quiz" data-id="${safeSlug}-check">
    <p class="quiz__q">What should the learner be able to produce from memory?</p>
    <button class="quiz__option" data-correct="false">Plausible distractor</button>
    <button class="quiz__option" data-correct="true">Correct answer</button>
    <button class="quiz__option" data-correct="false">Plausible distractor</button>
    <p class="quiz__why" hidden>Explain why the correct answer is right, not just that it is right.</p>
  </div>

  <div class="callout callout--info">
    <span class="callout__k">Ask your teacher</span>
    Stuck, or want this applied to your own example? Ask a follow-up.
  </div>

  <footer class="cite">
    Primary source: <a href="">add a real primary source before publishing</a>.
    <br>Related: <a href="#">sibling lesson</a> or <a href="#">reference document</a>.
  </footer>

</main>
<script id="kit"></script>
</body>
</html>
`;

mkdirSync(lessonsDir, { recursive: true });
writeFileSync(outFile, html);

console.log(`created ${join("lessons", basename(outFile))}`);
console.log(`next: node scripts/inline-kit.mjs ${join("lessons", basename(outFile))}`);
