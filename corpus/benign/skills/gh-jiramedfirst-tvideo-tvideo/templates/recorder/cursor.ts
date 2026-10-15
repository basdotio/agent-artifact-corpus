import type { BrowserContext, Locator, Page } from '@playwright/test';

/**
 * A visible mouse for tutorial recordings. Playwright's video has no cursor, so a
 * viewer can't see WHERE a click happened. This draws an arrow that follows the
 * real (Playwright-driven) mouse plus a ripple on each press, and `tap`/`typeInto`
 * glide to a control before using it so the eye can follow.
 *
 * Installed with addInitScript on the CONTEXT, so it is rebuilt on every
 * navigation and also appears in popups / new tabs; the last position lives in
 * sessionStorage so the arrow doesn't jump to a corner after a page change.
 * (A popup still records to its own video file — keep tutorial flows in one tab.)
 */
export async function installCursor(context: BrowserContext, accent = '#93d600'): Promise<void> {
  await context.addInitScript((color: string) => {
    const KEY = 'tvideo.cursor';
    const mount = () => {
      const arrow = document.createElement('div');
      arrow.setAttribute('aria-hidden', 'true');
      arrow.style.cssText =
        'position:fixed;left:0;top:0;width:28px;height:28px;z-index:2147483647;pointer-events:none;' +
        'transition:transform 40ms linear;filter:drop-shadow(0 2px 3px rgba(0,0,0,.45))';
      arrow.innerHTML =
        '<svg viewBox="0 0 24 24" width="28" height="28"><path d="M4 2l15 9.5-6.6 1.4 3.9 7.6-2.9 1.5-3.9-7.6L4 19z" ' +
        'fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
      document.body.append(arrow);
      const place = (x: number, y: number) => {
        arrow.style.transform = `translate(${x - 4}px, ${y - 2}px)`;
        sessionStorage.setItem(KEY, JSON.stringify([x, y]));
      };
      const saved = sessionStorage.getItem(KEY);
      const [sx, sy] = saved ? (JSON.parse(saved) as [number, number]) : [640, 400];
      place(sx, sy);
      window.addEventListener('mousemove', (e) => place(e.clientX, e.clientY), true);
      window.addEventListener(
        'mousedown',
        (e) => {
          const ring = document.createElement('div');
          ring.style.cssText =
            `position:fixed;left:${e.clientX - 18}px;top:${e.clientY - 18}px;width:36px;height:36px;border-radius:50%;` +
            `border:3px solid ${color};background:${color}40;z-index:2147483646;pointer-events:none;` +
            'transition:transform 450ms ease-out,opacity 450ms ease-out';
          document.body.append(ring);
          requestAnimationFrame(() => {
            ring.style.transform = 'scale(1.8)';
            ring.style.opacity = '0';
          });
          setTimeout(() => ring.remove(), 500);
        },
        true,
      );
    };
    if (document.body) mount();
    else document.addEventListener('DOMContentLoaded', mount);
  }, accent);
}

/** Rehearsal runs (TV_REHEARSE=1) skip the glides and pauses: they only prove every selector resolves. */
export const REHEARSE = process.env.TV_REHEARSE === '1';

/** A control's box in recording pixels, centre-based — the same shape as plan.json's `ring`. */
export type Box = { x: number; y: number; w: number; h: number };

/**
 * Glide the mouse to the centre of `target` and return where it sits on screen.
 * A target outside the viewport is smooth-scrolled into view first: Playwright's
 * own auto-scroll is instant and reads as a jump cut. Returns null in rehearsal.
 */
export async function pointAt(page: Page, target: Locator): Promise<Box | null> {
  if (REHEARSE) {
    await target.scrollIntoViewIfNeeded();
    return null;
  }
  let box = await target.boundingBox();
  const vp = page.viewportSize();
  const inView = box && vp && box.x >= 0 && box.y >= 0 && box.x + box.width <= vp.width && box.y + box.height <= vp.height;
  if (!inView) {
    // scrollIntoView picks whichever ancestor actually scrolls (often an app
    // shell's <main>, not the window); 900 ms lets the smooth scroll finish.
    await target.evaluate((el) => el.scrollIntoView({ behavior: 'smooth', block: 'center' }));
    await page.waitForTimeout(900);
    box = await target.boundingBox();
  }
  if (!box) throw new Error('pointAt: target has no bounding box (not visible?)');
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 25 });
  await page.waitForTimeout(250);
  // Re-measure for the log: a control in an opening drawer/modal may still have
  // been animating at the first read; this is where it sits when clicked.
  box = (await target.boundingBox()) ?? box;
  const r = Math.round;
  return { x: r(box.x + box.width / 2), y: r(box.y + box.height / 2), w: r(box.width), h: r(box.height) };
}

/**
 * Every `tap`: wall-clock time, the control's box (so the editor can ring it
 * without anyone measuring pixels) and `gone` — the control vanished after the
 * click (navigation, a closed menu), which tells the editor to show the frame
 * BEFORE the click (holdFirst). createTimeline resets these; save() awaits
 * `pendingClicks` so every `gone` is settled before clicks.json is written.
 */
export type Click = { t: number; box?: Box; gone?: boolean };
export const clickLog: Click[] = [];
export const pendingClicks: Promise<void>[] = [];
// When the next tap began, per click: a control that disappears only after that
// (a text field, once the NEXT tap navigates away) wasn't removed by its own click.
const nextTapAt = new WeakMap<Click, number>();

/** Glide to `target`, pause so the viewer sees where, then click it. */
export async function tap(page: Page, target: Locator): Promise<void> {
  const prev = clickLog.at(-1);
  if (prev && !nextTapAt.has(prev)) nextTapAt.set(prev, Date.now());
  const box = await pointAt(page, target);
  const click: Click = { t: Date.now(), ...(box && { box }) };
  clickLog.push(click);
  await target.click();
  // Not awaited: a control that stays (a text field) would otherwise stall every
  // tap for the whole timeout. 3 s covers a navigation or a menu closing.
  // ponytail: a navigation slower than 3 s, or one landing on an identical
  // control (a wizard's "Next"), reads as not gone — set holdFirst in plan.json.
  pendingClicks.push(
    target.waitFor({ state: 'hidden', timeout: 3000 }).then(
      () => { if (Date.now() <= (nextTapAt.get(click) ?? Infinity)) click.gone = true; },
      () => {},
    ),
  );
}

/** Glide to a field, click into it, and type at a readable pace. */
export async function typeInto(page: Page, target: Locator, text: string): Promise<void> {
  await tap(page, target);
  await target.pressSequentially(text, { delay: REHEARSE ? 0 : 90 });
}
