import { writeFile } from 'node:fs/promises';
import { test, type Locator, type Page, type TestInfo } from '@playwright/test';
import { REHEARSE, clickLog, installCursor, pendingClicks } from './cursor';

/**
 * Smooth-scroll `target` into view before acting on it. Playwright's own
 * auto-scroll is instant, which reads as a jump cut in the recording (the viewer
 * loses their place on the page). scrollIntoView picks whichever ancestor
 * actually scrolls (often an app shell's <main>, not the window).
 */
export async function glideTo(page: Page, target: Locator, settleMs = 1100): Promise<void> {
  await target.evaluate((el, smooth) => el.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto', block: 'center' }), !REHEARSE);
  if (!REHEARSE) await page.waitForTimeout(settleMs);
}

/** A readable pause after a key moment; zero in rehearsal. */
export function hold(page: Page, ms = 1200): Promise<void> {
  return REHEARSE ? Promise.resolve() : page.waitForTimeout(ms);
}

/** Colour of the sync flash; import.mjs looks for the first frame filled with it. */
export const SYNC_COLOR = '#ff00ff';

/**
 * Caption timeline for one recording. Create it as the FIRST line of the test
 * body. Writes `timeline.json` (one entry per step: label + startMs/endMs) and
 * `clicks.json` (every `tap`: ms, box, gone) next to the video — the editor
 * builds the whole cut from those two files.
 *
 * Times are wall-clock from t0, but Playwright's video starts earlier (at page
 * creation) and its screencast only emits frames on repaint, so "t0 = video 0"
 * is off by fixture setup time. Before the first step a one-off full-screen
 * flash is painted and its time saved as `syncMs`; import.mjs finds the flash in
 * the footage and shifts every time by the difference.
 *
 * Also installs the visible cursor and hides framework dev badges (Next.js
 * dev-tools, Vite overlay) that would otherwise sit in every frame.
 */
export function createTimeline(testInfo: TestInfo, page: Page, accent?: string) {
  const t0 = Date.now();
  clickLog.length = 0;
  pendingClicks.length = 0;
  void installCursor(page.context(), accent);
  void page.context().addInitScript(() => {
    document.addEventListener('DOMContentLoaded', () => {
      const style = document.createElement('style');
      style.textContent = 'nextjs-portal, vite-error-overlay { display: none !important; }';
      document.head.append(style);
    });
  });
  const steps: { label: string; startMs: number; endMs: number }[] = [];
  let syncMs: number | undefined;
  return {
    async step<T>(label: string, fn: () => Promise<T>): Promise<T> {
      if (!steps.length && syncMs === undefined && !REHEARSE) syncMs = await flash(page, t0);
      const startMs = Date.now() - t0;
      try {
        return await test.step(label, fn);
      } finally {
        steps.push({ label, startMs, endMs: Date.now() - t0 });
      }
    },
    async save() {
      await Promise.all(pendingClicks);
      const clicks = clickLog.map(({ t, ...rest }) => ({ ms: t - t0, ...rest }));
      const body = JSON.stringify(steps, null, 2);
      await writeFile(testInfo.outputPath('timeline.json'), body);
      await writeFile(testInfo.outputPath('clicks.json'), JSON.stringify(clicks));
      if (syncMs !== undefined) await writeFile(testInfo.outputPath('sync.json'), JSON.stringify({ syncMs }));
      await testInfo.attach('timeline.json', { body, contentType: 'application/json' });
    },
  };
}

/** Paint the sync colour over the whole page for ~300 ms; returns when it went up (ms from t0). */
async function flash(page: Page, t0: number): Promise<number> {
  await page.evaluate((color) => {
    const d = document.createElement('div');
    d.id = 'tvideo-sync';
    d.style.cssText = `position:fixed;inset:0;z-index:2147483647;background:${color}`;
    (document.body ?? document.documentElement).append(d);
  }, SYNC_COLOR);
  // Two frames: the evaluate resolves before the compositor paints.
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  const at = Date.now() - t0;
  await page.waitForTimeout(300);
  await page.evaluate(() => document.getElementById('tvideo-sync')?.remove());
  // Let the removal paint, so the first step never starts on a magenta frame.
  await page.waitForTimeout(150);
  return at;
}

/**
 * A date `offsetDays` from today (in `timeZone`), skipped forward to a weekday.
 * Apps with booking windows ("tomorrow … +7 days") enforce them against the real
 * clock — a hardcoded demo date goes un-pickable within days.
 */
export function relativeDay(offsetDays: number, timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone) {
  const local = (d: Date) => new Date(d.toLocaleString('en-US', { timeZone }));
  const today = local(new Date());
  const d = new Date(today);
  d.setDate(d.getDate() + offsetDays);
  while (d.getDay() === 0 || d.getDay() === 6) d.setDate(d.getDate() + 1);
  const p = (n: number) => String(n).padStart(2, '0');
  return {
    iso: `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`,
    dmy: `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()}`,
    day: d.getDate(),
    monthsAhead: (d.getFullYear() - today.getFullYear()) * 12 + d.getMonth() - today.getMonth(),
  };
}
