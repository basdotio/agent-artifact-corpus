// video-gaga scaffold — build a new composition from a style preset.
//
// A preset's video.html is a finished example video. `gaga init` keeps only what
// defines the *style* and leaves out what defines *that video*:
//   kept:    the <head> (fonts, import maps), the `// === THEME` section(s), the
//            `// === KIT …` sections (the style's reusable motion and drawing
//            helpers), and CV.create's look: size, background, fonts,
//            transition, caption style, overlay (grain, frame furniture)
//            minus any inline `// <example>` … `// </example>` block
//   dropped: every other section (`// === EXAMPLE …`: data, products, layouts
//            of the example), the example's scenes, its music score and its
//            narration.json
// The agent writes the scenes, the narration and the score for this brief.

const HEADER = /^\/\/ === (.*?)\s*=*\s*$/;
const KEEP = /^(THEME|KIT)\b/;

// → { html, kept: [section names], dropped: [section names] }
export function scaffoldFromPreset(src, { slug = 'preset' } = {}) {
  const lines = src.split('\n');
  const first = lines.findIndex((l) => HEADER.test(l));
  const video = lines.findIndex((l) => /^\/\/ === VIDEO\b/.test(l));
  const create = lines.findIndex((l, i) => i > video && /^CV\.create\(\{/.test(l));
  const scenes = lines.findIndex((l, i) => i > create && /^ {2}scenes: \[/.test(l));
  const scenesEnd = lines.findIndex((l, i) => i > scenes && /^ {2}\],?\s*(\/\/.*)?$/.test(l));
  if ([first, video, create, scenes, scenesEnd].some((i) => i < 0)) throw new Error(`preset "${slug}" does not follow the preset layout (// === THEME … // === VIDEO, CV.create({ … scenes: [ … ] }))`);

  const out = lines.slice(0, first);
  out.push(
    '// Scaffolded by `gaga init`: only this preset\'s STYLE was copied. THEME is the palette',
    '// and type. KIT is an optional toolbox of the style\'s signature moves: use, change or',
    '// delete any of it, and write the new helpers this video needs. The scenes, their',
    '// structure, the choreography and the score are designed fresh for this brief.',
    '',
  );
  const kept = [], dropped = [];
  let keep = false;
  for (let i = first; i < video; i++) {
    const h = lines[i].match(HEADER);
    if (h) { keep = KEEP.test(h[1]); (keep ? kept : dropped).push(h[1]); }
    if (keep) out.push(lines[i]);
  }
  // the VIDEO section up to CV.create: style-level helpers (e.g. a transition object)
  out.push(...lines.slice(video, create + 1));

  // CV.create config without the example's score
  const config = lines.slice(create + 1, scenes);
  for (let i = 0; i < config.length; i++) {
    if (!/^ {2}music:/.test(config[i])) continue;
    let j = i;
    if (!/\},?\s*(\/\/.*)?$/.test(config[i]) || /^ {2}music: \{\s*$/.test(config[i])) while (j < config.length && !/^ {2}\},?\s*$/.test(config[j])) j++;
    let k = i;
    while (k > 0 && /^ {2}\/\//.test(config[k - 1])) k--; // its comment lines
    config.splice(k, j - k + 1);
    break;
  }
  out.push(...config);
  out.push(
    '  // music: the score for THIS video, one piece written in score.mjs next to this file (docs/music-and-sound.md):',
    "  // music: { bpm, key, mode, script: 'score.mjs' },",
    '  scenes: [',
    '    // One scene per storyboard row: { id, energy, transition?, draw(ctx, s) { … } }.',
    `    // The preset's own example scenes (presets/${slug}/video.html) show its motion grammar; don't copy their content or structure.`,
    '  ],',
  );
  out.push(...lines.slice(scenesEnd + 1));
  // inline `// <example>` … `// </example>` blocks inside kept code (e.g. an overlay's
  // folio text) belong to the example too
  const html = out.join('\n').replace(/^[ \t]*\/\/ <example>[^\n]*\n[\s\S]*?^[ \t]*\/\/ <\/example>[^\n]*\n/gm, '');
  return { html, kept, dropped };
}

// Names declared in the dropped sections that the scaffold still uses (it
// would throw a ReferenceError). Rough, line-based; used by the tests.
export function danglingNames(src) {
  const decl = (l) => {
    const f = l.match(/^(?:async\s+)?function\s*\*?\s*([\w$]+)/);
    if (f) return [f[1]];
    const m = l.match(/^(?:const|let|var)\s+(.*)$/);
    return m ? [...m[1].matchAll(/(?:^|,\s*)([A-Za-z_$][\w$]*)\s*=(?!=)/g)].map((x) => x[1]) : [];
  };
  const lines = src.split('\n');
  const video = lines.findIndex((l) => /^\/\/ === VIDEO\b/.test(l));
  const dropped = new Set();
  let keep = true;
  lines.slice(0, video).forEach((l) => {
    const h = l.match(HEADER);
    if (h) keep = KEEP.test(h[1]);
    else if (!keep) decl(l).forEach((n) => dropped.add(n));
  });
  const html = scaffoldFromPreset(src).html;
  const declared = new Set(html.split('\n').flatMap(decl));
  const code = html.slice(html.search(/^<script(?:\s+type="module")?>$/m))
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/\/\/.*$/gm, ' ')
    .replace(/'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*"/g, "''");
  // parameters are local; `name:` is an object key, not a use
  for (const m of code.matchAll(/\(([^()]*)\)\s*=>|function\s*[\w$]*\s*\(([^)]*)\)/g)) for (const n of (m[1] ?? m[2]).match(/[A-Za-z_$][\w$]*/g) || []) declared.add(n);
  const used = new Set(code.replace(/[A-Za-z_$][\w$]*\s*:(?!:)/g, ' ').match(/(?<![.\w$])[A-Za-z_$][\w$]*/g));
  return [...dropped].filter((n) => !declared.has(n) && used.has(n));
}
