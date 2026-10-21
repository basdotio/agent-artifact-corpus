// gaga moodboard: the style directions side by side on one page.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { themeFromHtml, describeScore, buildMoodboardPage } from '../scripts/moodboard.mjs';

const root = new URL('../presets/', import.meta.url);
const presets = fs.readdirSync(root).filter((d) => fs.existsSync(new URL(`${d}/video.html`, root)));

test('every preset THEME yields a palette, type and its font links', () => {
  for (const slug of presets) {
    const { colors, fonts, fontLinks } = themeFromHtml(fs.readFileSync(new URL(`${slug}/video.html`, root), 'utf8'));
    assert.ok(colors.length >= 3, `${slug}: ${colors.length} colours`);
    assert.ok(colors.every((c) => /^#[0-9A-F]{3,6}$/.test(c.hex)), slug);
    assert.ok(fonts.length >= 1, `${slug}: fonts`);
    assert.ok(fonts.every((f) => f.stack.startsWith(`"${f.family}"`)), slug);
    assert.ok(fontLinks.length >= 1 && fontLinks.every((h) => h.startsWith('https://fonts.googleapis.com/css2?')), slug);
  }
});

test('only the THEME section is read', () => {
  const src = '// === THEME ===\nconst T = {\n  bg: \'#000\', // night\n  display: \'"Geist", sans-serif\',\n};\n// === EXAMPLE: x ===\nconst X = { red: \'#f00\', font: \'"Comic Neue"\' };\n';
  const { colors, fonts } = themeFromHtml(src);
  assert.deepEqual(colors, [{ name: 'bg', hex: '#000', note: 'night' }]);
  assert.deepEqual(fonts.map((f) => f.family), ['Geist']);
});

test('a draft score is summarised in one line', () => {
  assert.equal(describeScore(null), null);
  assert.equal(describeScore({ bpm: 100, key: 'D', mode: 'major', layers: [{ inst: 'pad' }, { inst: 'bass' }, { inst: 'pad' }], lead: { inst: 'glock' } }), '100 BPM · D major · pad, bass, glock');
});

const dirs = [
  { id: 'style-a', letter: 'A', name: '暖纸讲解', recommended: true, ratio: [1920, 1080], clip: 'style-a/build/moodboard/clip.mp4', hasSound: true, poster: 'a.jpg', frames: ['1.jpg', '2.jpg', '3.jpg'], palette: [{ hex: '#F3EFE6', name: 'paper' }], type: [{ family: 'Noto Sans SC', stack: '"Noto Sans SC", sans-serif', role: 'sans' }], motion: 'm', music: '100 BPM' },
  { id: 'style-b', letter: 'B', name: '<script>alert(1)</script>', ratio: [1080, 1920], poster: 'b.jpg', palette: [], type: [] },
];

test('the page has one card per direction, escapes text and works offline or served', () => {
  const html = buildMoodboardPage({ title: '为什么天空是蓝色的？', lang: 'zh', directions: dirs, fontLinks: ['https://fonts.googleapis.com/css2?family=A&display=block', 'https://fonts.googleapis.com/css2?family=A&display=block'] });
  assert.equal(html.match(/<article class="dir/g).length, 2);
  assert.equal(html.match(/class="tag">推荐</g).length, 1);
  assert.equal(html.match(/<link rel="stylesheet"/g).length, 1, 'font links deduplicated');
  assert.doesNotMatch(html, /<script>alert/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.match(html, /<video src="style-a\/build\/moodboard\/clip\.mp4" poster="a\.jpg" autoplay muted loop playsinline/);
  assert.match(html, /aspect-ratio:1080\/1920/);
  assert.match(html, /为什么天空是蓝色的？/);
  // the inline script parses
  const js = html.match(/<script>\n([\s\S]*?)<\/script>/)[1];
  assert.doesNotThrow(() => new Function(js));
  assert.match(js, /fetch\('pick'/);
  assert.match(js, /我选 /);
});

test('English labels by default', () => {
  const html = buildMoodboardPage({ directions: dirs });
  assert.match(html, /Pick a direction/);
  assert.match(html, /Recommended/);
});
