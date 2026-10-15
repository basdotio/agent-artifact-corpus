/**
 * Tab (target) helpers for a browser you do NOT own.
 *
 * Rules encoded here:
 * - Only real web pages are candidates; internal pages (chrome://, edge://,
 *   devtools://, extensions, omnibox popups) are skipped.
 * - New tabs are opened in the background so the user's focus is not stolen.
 * - You only close tabs you created. Never the user's tabs, never the browser.
 * - Identify tabs by `targetId`. CDP order is NOT the visual tab-strip order.
 */

import type { Protocol } from "devtools-protocol";
import type { CdpClient } from "./cdp-client.ts";

export type TargetInfo = Protocol.Target.TargetInfo;

const INTERNAL_URL = /^(chrome|edge|brave|vivaldi|opera|devtools|chrome-extension|chrome-untrusted|about):/i;

/** True for tabs a script should consider working in. */
export function isUserPage(t: TargetInfo): boolean {
  return t.type === "page" && !INTERNAL_URL.test(t.url);
}

/** All open user-facing page tabs. */
export async function listPages(cdp: CdpClient): Promise<TargetInfo[]> {
  const { targetInfos } = await cdp.send("Target.getTargets");
  return targetInfos.filter(isUserPage);
}

/** Find a tab whose URL matches (string = substring, RegExp = test). */
export async function findPage(cdp: CdpClient, match: string | RegExp): Promise<TargetInfo | undefined> {
  const pages = await listPages(cdp);
  return pages.find((t) => (typeof match === "string" ? t.url.includes(match) : match.test(t.url)));
}

/** Attach to a target and return the flatten `sessionId` to route commands to it. */
export async function attach(cdp: CdpClient, targetId: string): Promise<string> {
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  return sessionId;
}

/** Detach without closing the tab. */
export async function detach(cdp: CdpClient, sessionId: string): Promise<void> {
  await cdp.send("Target.detachFromTarget", { sessionId });
}

/**
 * Open a NEW tab in the background (does not steal focus) and attach to it.
 * The returned `close` only closes this tab.
 */
export async function openBackgroundTab(
  cdp: CdpClient,
  url = "about:blank",
): Promise<{ targetId: string; sessionId: string; close: () => Promise<void> }> {
  const { targetId } = await cdp.send("Target.createTarget", { url, background: true });
  const sessionId = await attach(cdp, targetId);
  return {
    targetId,
    sessionId,
    close: async () => {
      await cdp.send("Target.closeTarget", { targetId });
    },
  };
}

/**
 * Evaluate an expression in a page session and return its value.
 * `awaitPromise` lets you evaluate async code; `returnByValue` serializes the result.
 */
export async function evaluate<T = unknown>(cdp: CdpClient, sessionId: string, expression: string): Promise<T> {
  const { result, exceptionDetails } = await cdp.send(
    "Runtime.evaluate",
    { expression, awaitPromise: true, returnByValue: true },
    { sessionId },
  );
  if (exceptionDetails) {
    throw new Error(`Evaluation failed: ${exceptionDetails.exception?.description ?? exceptionDetails.text}`);
  }
  return result.value as T;
}

/** Navigate a session and wait for its load event. */
export async function navigate(cdp: CdpClient, sessionId: string, url: string, timeoutMs = 30_000): Promise<void> {
  await cdp.send("Page.enable", undefined, { sessionId });
  const loaded = cdp.waitFor("Page.loadEventFired", { sessionId, timeoutMs });
  const { errorText } = await cdp.send("Page.navigate", { url }, { sessionId });
  if (errorText) throw new Error(`Navigation to ${url} failed: ${errorText}`);
  await loaded;
}
