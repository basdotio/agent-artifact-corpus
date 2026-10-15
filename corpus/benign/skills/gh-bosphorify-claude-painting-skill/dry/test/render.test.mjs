import { test, after } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync, mkdtempSync, rmSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const dry = join(dirname(fileURLToPath(import.meta.url)), '..');
const tmp = mkdtempSync(join(tmpdir(), 'dry-render-'));
after(() => rmSync(tmp, { recursive: true, force: true }));

const render = out => execFileSync(process.execPath, [join(dry, 'render.mjs'), join(dry, 'template.html'), out, '--no-review'], { stdio: 'pipe' });
const pngSize = buf => ({ width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) });

// Fraction of pixels whose RGBA differs between two PNGs (decoded in the browser)
async function diffFraction(a, b) {
  const browser = await chromium.launch({ channel: 'chrome' }).catch(() => chromium.launch());
  const page = await browser.newPage();
  const frac = await page.evaluate(async urls => {
    const pixels = async src => {
      const img = new Image(); img.src = src; await img.decode();
      const g = new OffscreenCanvas(img.width, img.height).getContext('2d');
      g.drawImage(img, 0, 0);
      return g.getImageData(0, 0, img.width, img.height).data;
    };
    const [A, B] = await Promise.all(urls.map(pixels));
    let n = 0;
    for (let i = 0; i < A.length; i += 4) if (A[i] !== B[i] || A[i + 1] !== B[i + 1] || A[i + 2] !== B[i + 2] || A[i + 3] !== B[i + 3]) n++;
    return n / (A.length / 4);
  }, [a, b].map(buf => 'data:image/png;base64,' + buf.toString('base64')));
  await browser.close();
  return frac;
}

test('template.html renders to a fixed-size PNG, the same for the same seed', async t => {
  const a = join(tmp, 'a.png'), b = join(tmp, 'b.png');
  render(a);
  render(b);
  assert.ok(existsSync(a), 'render wrote no PNG');
  const A = readFileSync(a), B = readFileSync(b);
  assert.equal(A.subarray(1, 4).toString(), 'PNG');
  assert.deepEqual(pngSize(A), { width: 1200, height: 900 }); // template.html's W x H
  const frac = A.equals(B) ? 0 : await diffFraction(A, B);
  t.diagnostic(`pixels differing between two renders: ${(frac * 100).toFixed(4)}%`);
  assert.ok(frac < 0.005, `renders differ in ${(frac * 100).toFixed(3)}% of pixels (limit 0.5%)`); // WebGL float noise only
});
