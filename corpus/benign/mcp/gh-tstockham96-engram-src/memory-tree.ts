// ============================================================
// Memory Tree — Beautiful growing tree visualization
// ============================================================
//
// A truecolor Unicode block art tree that grows with your vault.
// Inspired by Gemini CLI's gradient block art.

// ── Color helpers (truecolor ANSI) ──

function rgb(r: number, g: number, b: number, text: string): string {
  return `\x1b[38;2;${r};${g};${b}m${text}\x1b[0m`;
}

function rgbBg(r: number, g: number, b: number, text: string): string {
  return `\x1b[48;2;${r};${g};${b}m${text}\x1b[0m`;
}

function lerp(a: number, b: number, t: number): number {
  return Math.round(a + (b - a) * t);
}

function lerpColor(c1: [number, number, number], c2: [number, number, number], t: number): [number, number, number] {
  return [lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t)];
}

// ── Palette ──

const PALETTE = {
  // Canopy gradient (top to bottom)
  leafLight:  [134, 239, 172] as [number, number, number],  // bright green
  leafMid:    [34, 197, 94] as [number, number, number],    // medium green
  leafDark:   [22, 101, 52] as [number, number, number],    // deep green
  leafGlow:   [74, 222, 128] as [number, number, number],   // glow highlights

  // Trunk
  barkLight:  [161, 98, 7] as [number, number, number],     // honey brown
  barkDark:   [92, 56, 15] as [number, number, number],     // dark brown
  barkMid:    [120, 75, 15] as [number, number, number],

  // Roots
  rootLight:  [87, 65, 30] as [number, number, number],
  rootDark:   [55, 40, 20] as [number, number, number],

  // Ground
  soil:       [62, 45, 25] as [number, number, number],
  grass:      [34, 120, 50] as [number, number, number],

  // Accents
  flower:     [251, 191, 36] as [number, number, number],   // golden
  fruit:      [239, 68, 68] as [number, number, number],    // red
  sparkle:    [250, 250, 210] as [number, number, number],  // pale yellow
  purple:     [168, 85, 247] as [number, number, number],   // purple accent
};

// ── Growth stages ──

interface TreeStats {
  memoryCount: number;
  entityCount: number;
  connectionCount: number;
  consolidationCount: number;
}

function getStage(stats: TreeStats): 'seed' | 'sprout' | 'sapling' | 'tree' | 'oak' | 'ancient' {
  const m = stats.memoryCount;
  if (m === 0) return 'seed';
  if (m < 10) return 'sprout';
  if (m < 50) return 'sapling';
  if (m < 200) return 'tree';
  if (m < 500) return 'oak';
  return 'ancient';
}

// ── Art definitions ──
// Each is an array of strings. We apply gradients per-row.
// Characters: █ ▓ ░ ▄ ▀ ╱ ╲ │ ─ ┌ ┐ └ ┘ ● ◆ ✦ ✧ ∙ · ˙

function renderSeed(): string[] {
  return [
    '',
    '                  ✦',
    '                 ∙│∙',
    '                  │',
    '               ───┴───',
    '',
  ];
}

function renderSprout(): string[] {
  return [
    '',
    '                  🌱',
    '                 ╱│╲',
    '                ╱ │ ╲',
    '                  │',
    '                  │',
    '              ────┴────',
    '',
  ];
}

function renderSapling(): string[] {
  return [
    '                ░░▒▒▓▓░░',
    '              ░▒▓████▓▒░',
    '            ░▒▓██████▓▒░░',
    '              ░▒▓████▓▒░',
    '                ░▒▓▒░',
    '                  ██',
    '                  ██',
    '                  ██',
    '                 ▄██▄',
    '            ─────────────',
  ];
}

function artTree(): string[] {
  return [
    '                  ░▒▓▒░',
    '              ░▒▓██████▓▒░',
    '           ░▒▓████████████▓▒░',
    '         ░▒▓████████████████▓░',
    '        ░▒▓██████████████████▓░',
    '         ░▒▓████████████████▓░',
    '           ░▒▓████████████▓▒░',
    '              ░▒▓██████▓▒░',
    '                  ████',
    '                  ████',
    '                  ████',
    '                  ████',
    '                 ▄████▄',
    '           ──────────────────',
  ];
}

function renderOak(): string[] {
  return [
    '                    ░▒▓▒░',
    '               ░▒▓████████▓▒░',
    '           ░▒▓████████████████▓▒░',
    '        ░▒▓████████████████████████▓░',
    '      ░▒▓████████████████████████████▓░',
    '     ░▒▓██████████████████████████████▓░',
    '      ░▒▓████████████████████████████▓░',
    '        ░▒▓████████████████████████▓░',
    '           ░▒▓████████████████▓▒░',
    '               ░▒▓████████▓▒░',
    '                   ██████',
    '                   ██████',
    '                   ██████',
    '                   ██████',
    '                   ██████',
    '                 ▄████████▄',
    '           ────────────────────────',
  ];
}

function renderAncient(): string[] {
  return [
    '                       ✦  ░▒▓▒░  ✦',
    '                  ░▒▓██████████████▓▒░',
    '             ░▒▓██████████████████████████▓▒░',
    '          ░▒▓████████████████████████████████▓░',
    '       ░▒▓████████████████████████████████████████▓░',
    '     ░▒▓████████████████████████████████████████████▓░',
    '    ░▒▓██████████████████████████████████████████████▓░',
    '     ░▒▓████████████████████████████████████████████▓░',
    '       ░▒▓████████████████████████████████████████▓░',
    '          ░▒▓████████████████████████████████▓░',
    '             ░▒▓██████████████████████████▓▒░',
    '                  ░▒▓██████████████▓▒░',
    '                     ████████████',
    '                     ████████████',
    '                     ████████████',
    '                     ████████████',
    '                     ████████████',
    '                     ████████████',
    '                  ▄██████████████████▄',
    '          ──────────────────────────────────',
  ];
}

// ── Colorize ──

function colorizeChar(ch: string, row: number, col: number, totalRows: number, stage: string): string {
  // Skip spaces
  if (ch === ' ' || ch === '') return ch;

  const rowT = row / Math.max(totalRows - 1, 1); // 0 = top, 1 = bottom

  // Sparkles / accents
  if (ch === '✦' || ch === '✧') return rgb(...PALETTE.sparkle, ch);
  if (ch === '∙' || ch === '·' || ch === '˙') return rgb(...PALETTE.flower, ch);
  if (ch === '🌱') return ch; // emoji, no coloring needed

  // Ground line
  if (ch === '─' || ch === '┴') {
    const c = lerpColor(PALETTE.grass, PALETTE.soil, 0.5);
    return rgb(...c, ch);
  }

  // Trunk characters
  if (ch === '│') {
    const c = lerpColor(PALETTE.barkLight, PALETTE.barkDark, rowT);
    return rgb(...c, ch);
  }

  // Trunk blocks (lower portion of tree)
  const isLowerHalf = rowT > 0.6;

  if (ch === '█' && isLowerHalf) {
    // Trunk
    const trunkT = (rowT - 0.6) / 0.4;
    const c = lerpColor(PALETTE.barkLight, PALETTE.barkDark, trunkT);
    return rgb(...c, ch);
  }

  if (ch === '▄' && isLowerHalf) {
    const c = lerpColor(PALETTE.barkMid, PALETTE.rootLight, 0.5);
    return rgb(...c, ch);
  }

  // Branch chars
  if (ch === '╱' || ch === '╲') {
    const c = lerpColor(PALETTE.barkLight, PALETTE.leafDark, 0.5);
    return rgb(...c, ch);
  }

  // Canopy — gradient from light at top to dark at bottom of canopy
  if (ch === '█' || ch === '▓' || ch === '▒' || ch === '░' || ch === '▀') {
    // Canopy vertical gradient
    const canopyT = Math.min(rowT / 0.6, 1); // normalize to canopy section

    let base: [number, number, number];
    if (canopyT < 0.3) {
      base = lerpColor(PALETTE.leafGlow, PALETTE.leafLight, canopyT / 0.3);
    } else if (canopyT < 0.7) {
      base = lerpColor(PALETTE.leafLight, PALETTE.leafMid, (canopyT - 0.3) / 0.4);
    } else {
      base = lerpColor(PALETTE.leafMid, PALETTE.leafDark, (canopyT - 0.7) / 0.3);
    }

    // Density variation by character
    const densityMod = ch === '░' ? 0.6 : ch === '▒' ? 0.8 : ch === '▓' ? 0.9 : 1.0;
    const c: [number, number, number] = [
      Math.round(base[0] * densityMod),
      Math.round(base[1] * densityMod),
      Math.round(base[2] * densityMod),
    ];

    // Occasional purple/gold highlights for ancient trees
    if (stage === 'ancient' && ch === '█') {
      const hash = (row * 31 + col * 17) % 47;
      if (hash === 0) return rgb(...PALETTE.purple, ch);
      if (hash === 1) return rgb(...PALETTE.flower, ch);
      if (hash === 2) return rgb(...PALETTE.fruit, ch);
    }

    return rgb(...c, ch);
  }

  return ch;
}

function colorizeLine(line: string, row: number, totalRows: number, stage: string): string {
  let result = '';
  for (let col = 0; col < line.length; col++) {
    // Handle multi-byte characters (emoji)
    const ch = line[col];
    if (ch && ch.charCodeAt(0) > 0xD7FF) {
      // Surrogate pair — grab both chars
      result += line[col] + (line[col + 1] ?? '');
      col++;
    } else {
      result += colorizeChar(ch, row, col, totalRows, stage);
    }
  }
  return result;
}

// ── Animation ──

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function clearLines(n: number): void {
  for (let i = 0; i < n; i++) {
    process.stderr.write('\x1b[1A\x1b[2K'); // Move up, clear line
  }
}

// ── Public API ──

/**
 * Render the memory tree for the current vault state.
 * Prints to stderr (so it works alongside MCP stdio).
 */
export function renderTree(stats: TreeStats, opts?: { animate?: boolean }): void {
  const stage = getStage(stats);
  const art = getArt(stage);
  const lines = art.map((line, i) => colorizeLine(line, i, art.length, stage));

  // Stats bar
  const stageLabel = getStageLabel(stage);
  const dim = (s: string) => `\x1b[2m${s}\x1b[0m`;
  const bold = (s: string) => `\x1b[1m${s}\x1b[0m`;

  const statsLine = dim(`  ${stageLabel}  ·  `) +
    bold(`${stats.memoryCount}`) + dim(' memories  ·  ') +
    bold(`${stats.entityCount}`) + dim(' entities  ·  ') +
    bold(`${stats.connectionCount}`) + dim(' connections');

  const consolidationLine = stats.consolidationCount > 0
    ? dim(`  ${stats.consolidationCount} consolidations`)
    : '';

  lines.push('');
  lines.push(statsLine);
  if (consolidationLine) lines.push(consolidationLine);
  lines.push('');

  for (const line of lines) {
    process.stderr.write(line + '\n');
  }
}

/**
 * Animate the tree growing from seed to current stage.
 * Shows each intermediate stage briefly.
 */
export async function animateGrowth(stats: TreeStats): Promise<void> {
  const targetStage = getStage(stats);
  const stages: Array<'seed' | 'sprout' | 'sapling' | 'tree' | 'oak' | 'ancient'> =
    ['seed', 'sprout', 'sapling', 'tree', 'oak', 'ancient'];

  const targetIdx = stages.indexOf(targetStage);
  let lastLineCount = 0;

  for (let i = 0; i <= targetIdx; i++) {
    const stage = stages[i];
    const art = getArt(stage);
    const lines = art.map((line, j) => colorizeLine(line, j, art.length, stage));

    // Clear previous frame
    if (lastLineCount > 0) {
      clearLines(lastLineCount);
    }

    for (const line of lines) {
      process.stderr.write(line + '\n');
    }

    lastLineCount = lines.length;

    if (i < targetIdx) {
      await sleep(400); // pause between stages
    }
  }

  // Final stats
  const stageLabel = getStageLabel(targetStage);
  const dim = (s: string) => `\x1b[2m${s}\x1b[0m`;
  const bold = (s: string) => `\x1b[1m${s}\x1b[0m`;

  const statsLine = dim(`  ${stageLabel}  ·  `) +
    bold(`${stats.memoryCount}`) + dim(' memories  ·  ') +
    bold(`${stats.entityCount}`) + dim(' entities  ·  ') +
    bold(`${stats.connectionCount}`) + dim(' connections');

  process.stderr.write('\n' + statsLine + '\n\n');
}

// ── Internal ──

function getArt(stage: string): string[] {
  switch (stage) {
    case 'seed': return renderSeed();
    case 'sprout': return renderSprout();
    case 'sapling': return renderSapling();
    case 'tree': return artTree();
    case 'oak': return renderOak();
    case 'ancient': return renderAncient();
    default: return renderSeed();
  }
}

function getStageLabel(stage: string): string {
  switch (stage) {
    case 'seed': return '🌰 Seed';
    case 'sprout': return '🌱 Sprout';
    case 'sapling': return '🌿 Sapling';
    case 'tree': return '🌳 Tree';
    case 'oak': return '🏔️  Oak';
    case 'ancient': return '✨ Ancient';
    default: return '🌰 Seed';
  }
}
