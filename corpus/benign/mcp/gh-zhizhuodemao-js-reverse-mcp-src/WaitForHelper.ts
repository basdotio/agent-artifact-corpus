/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {addCdpEventListener, removeCdpEventListener} from './CdpEvents.js';
import type {CdpSessionProvider} from './CdpSessionProvider.js';
import {logger} from './logger.js';
import type {CDPSession, Page} from './third_party/index.js';

export class WaitForHelper {
  #abortController = new AbortController();
  #page: Page;
  #cdpSession: CDPSession;
  #stableDomTimeout: number;
  #stableDomFor: number;
  #expectNavigationIn: number;
  #navigationTimeout: number;

  private constructor(page: Page, cdpSession: CDPSession) {
    this.#stableDomTimeout = 3000;
    this.#stableDomFor = 100;
    this.#expectNavigationIn = 100;
    this.#navigationTimeout = 3000;
    this.#page = page;
    this.#cdpSession = cdpSession;
  }

  static async create(
    page: Page,
    sessionProvider: CdpSessionProvider,
  ): Promise<WaitForHelper> {
    const session = await sessionProvider.getSession(page);
    return new WaitForHelper(page, session);
  }

  /**
   * A wrapper that executes a action and waits for
   * a potential navigation, after which it waits
   * for the DOM to be stable before returning.
   */
  async waitForStableDom(): Promise<void> {
    const stableDomObserver = await this.#page.evaluateHandle(timeout => {
      let timeoutId: ReturnType<typeof setTimeout>;
      function callback() {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
          domObserver.resolver.resolve();
          domObserver.observer.disconnect();
        }, timeout);
      }
      const domObserver = {
        resolver: Promise.withResolvers<void>(),
        observer: new MutationObserver(callback),
      };
      // It's possible that the DOM is not gonna change so we
      // need to start the timeout initially.
      callback();

      domObserver.observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
      });

      return domObserver;
    }, this.#stableDomFor);

    const cleanup = async () => {
      try {
        await stableDomObserver.evaluate(observer => {
          observer.observer.disconnect();
          observer.resolver.resolve();
        });
        await stableDomObserver.dispose();
      } catch {
        // Ignored cleanup errors
      }
    };

    try {
      await Promise.race([
        stableDomObserver.evaluate(async observer => {
          return await observer.resolver.promise;
        }),
        this.timeout(this.#stableDomTimeout).then(() => {
          throw new Error('Timeout');
        }),
      ]);
    } finally {
      // Do not leave the observer/evaluation running after this helper returns.
      await cleanup();
    }
  }

  async waitForNavigationStarted() {
    const navigationStartedPromise = new Promise<boolean>(resolve => {
      const listener = (event: {navigationType: string}) => {
        if (
          [
            'historySameDocument',
            'historyDifferentDocument',
            'sameDocument',
          ].includes(event.navigationType)
        ) {
          resolve(false);
          return;
        }

        resolve(true);
      };

      addCdpEventListener(
        this.#cdpSession,
        'Page.frameStartedNavigating',
        listener,
      );
      this.#abortController.signal.addEventListener('abort', () => {
        resolve(false);
        removeCdpEventListener(
          this.#cdpSession,
          'Page.frameStartedNavigating',
          listener,
        );
      });
    });

    return await Promise.race([
      navigationStartedPromise,
      this.timeout(this.#expectNavigationIn).then(() => false),
    ]);
  }

  timeout(time: number): Promise<void> {
    return new Promise<void>(res => {
      const id = setTimeout(res, time);
      this.#abortController.signal.addEventListener('abort', () => {
        res();
        clearTimeout(id);
      });
    });
  }

  async waitForEventsAfterAction(
    action: () => Promise<unknown>,
  ): Promise<void> {
    const doAction = async () => {
      const navigationFinished = this.waitForNavigationStarted()
        .then(navigationStarted => {
          if (navigationStarted) {
            return this.#page.waitForLoadState('domcontentloaded', {
              timeout: this.#navigationTimeout,
            });
          }
          return;
        })
        .catch(error => logger(error));

      try {
        await action();
      } catch (error) {
        // Clear up pending promises
        this.#abortController.abort();
        throw error;
      }

      try {
        await navigationFinished;

        // Wait for stable dom after navigation so we execute in
        // the correct context
        await this.waitForStableDom();
      } catch (error) {
        logger(error);
      } finally {
        this.#abortController.abort();
      }
    };

    try {
      await doAction();
    } finally {
      this.#abortController.abort();
    }
  }
}
