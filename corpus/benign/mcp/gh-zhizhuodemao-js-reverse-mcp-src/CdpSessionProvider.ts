/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type {
  BrowserContext,
  CDPSession,
  Frame,
  Page,
} from './third_party/index.js';

interface PendingSession {
  invalidated: boolean;
  promise: Promise<CDPSession>;
}

/**
 * CDP Session cache layer for Playwright/Patchright.
 *
 * In Puppeteer, `page._client()` is synchronous and returns the same session.
 * In Playwright, `page.context().newCDPSession(page)` is async and creates
 * a new session each time. This provider caches sessions per Page/Frame.
 */
export class CdpSessionProvider {
  #pageSessions = new WeakMap<Page, CDPSession>();
  #frameSessions = new WeakMap<Frame, CDPSession>();
  #pendingPageSessions = new WeakMap<Page, PendingSession>();
  #pendingFrameSessions = new WeakMap<Frame, PendingSession>();
  #context: BrowserContext;

  constructor(context: BrowserContext) {
    this.#context = context;
  }

  /**
   * Get a cached CDP session for a page, creating one if needed.
   */
  getSession(pageOrFrame: Page): Promise<CDPSession>;
  getSession(pageOrFrame: Frame): Promise<CDPSession>;
  getSession(pageOrFrame: Page | Frame): Promise<CDPSession> {
    // Check if it's a Page (has context() method that returns BrowserContext)
    if ('context' in pageOrFrame && typeof pageOrFrame.context === 'function') {
      // It could be either Page or Frame - check for mainFrame to distinguish
      if ('mainFrame' in pageOrFrame) {
        return this.#getPageSession(pageOrFrame as Page);
      }
    }
    return this.#getFrameSession(pageOrFrame as Frame);
  }

  #getPageSession(page: Page): Promise<CDPSession> {
    const cached = this.#pageSessions.get(page);
    if (cached) {
      return Promise.resolve(cached);
    }
    const existing = this.#pendingPageSessions.get(page);
    if (existing) {
      return existing.promise;
    }

    const operation = this.#context.newCDPSession(page);
    const pending: PendingSession = {invalidated: false, promise: operation};
    const promise = operation
      .then(async session => {
        if (
          pending.invalidated ||
          this.#pendingPageSessions.get(page) !== pending
        ) {
          await session.detach().catch(() => undefined);
          throw new Error('CDP page session creation was invalidated');
        }
        this.#pageSessions.set(page, session);
        return session;
      })
      .finally(() => {
        if (this.#pendingPageSessions.get(page) === pending) {
          this.#pendingPageSessions.delete(page);
        }
      });
    pending.promise = promise;
    this.#pendingPageSessions.set(page, pending);
    return promise;
  }

  #getFrameSession(frame: Frame): Promise<CDPSession> {
    const cached = this.#frameSessions.get(frame);
    if (cached) {
      return Promise.resolve(cached);
    }
    const existing = this.#pendingFrameSessions.get(frame);
    if (existing) {
      return existing.promise;
    }

    // Playwright's newCDPSession accepts Frame directly for OOPIFs.
    const operation = this.#context.newCDPSession(frame);
    const pending: PendingSession = {invalidated: false, promise: operation};
    const promise = operation
      .then(async session => {
        if (
          pending.invalidated ||
          this.#pendingFrameSessions.get(frame) !== pending
        ) {
          await session.detach().catch(() => undefined);
          throw new Error('CDP frame session creation was invalidated');
        }
        this.#frameSessions.set(frame, session);
        return session;
      })
      .finally(() => {
        if (this.#pendingFrameSessions.get(frame) === pending) {
          this.#pendingFrameSessions.delete(frame);
        }
      });
    pending.promise = promise;
    this.#pendingFrameSessions.set(frame, pending);
    return promise;
  }

  /**
   * Invalidate cached session for a page or frame.
   * Call this when the page/frame is closed or navigated.
   */
  invalidate(pageOrFrame: Page | Frame): void {
    if ('mainFrame' in pageOrFrame) {
      const pending = this.#pendingPageSessions.get(pageOrFrame as Page);
      if (pending) {
        pending.invalidated = true;
        this.#pendingPageSessions.delete(pageOrFrame as Page);
      }
      const session = this.#pageSessions.get(pageOrFrame as Page);
      if (session) {
        void session.detach().catch(() => undefined);
        this.#pageSessions.delete(pageOrFrame as Page);
      }
    } else {
      const pending = this.#pendingFrameSessions.get(pageOrFrame as Frame);
      if (pending) {
        pending.invalidated = true;
        this.#pendingFrameSessions.delete(pageOrFrame as Frame);
      }
      const session = this.#frameSessions.get(pageOrFrame as Frame);
      if (session) {
        void session.detach().catch(() => undefined);
        this.#frameSessions.delete(pageOrFrame as Frame);
      }
    }
  }
}
