/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {constants as fsConstants} from 'node:fs';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import {CdpSessionProvider} from './CdpSessionProvider.js';
import {DebuggerContext} from './DebuggerContext.js';
import {extractUrlLikeFromDevToolsTitle, urlsEqual} from './DevtoolsUtils.js';
import type {TrafficSummary} from './formatters/websocketFormatter.js';
import {assertLocalFileWriteAllowed} from './LocalFileAccess.js';
import {NetworkCollector, ConsoleCollector} from './PageCollector.js';
import type {ListenerMap, RequestInitiator} from './PageCollector.js';
import type {
  BrowserContext,
  ConsoleMessage,
  Debugger,
  Dialog,
  Frame,
  HTTPRequest,
  Page,
} from './third_party/index.js';
import {ToolError} from './ToolError.js';
import {selectPage} from './tools/pages.js';
import {CLOSE_PAGE_ERROR} from './tools/ToolDefinition.js';
import type {
  Context,
  DevToolsData,
  ToolCapability,
} from './tools/ToolDefinition.js';
import {WaitForHelper} from './WaitForHelper.js';
import type {WebSocketData} from './WebSocketCollector.js';
import {WebSocketCollector} from './WebSocketCollector.js';

const DEFAULT_TIMEOUT = 5_000;
const NAVIGATION_TIMEOUT = 10_000;
const MAX_TRAFFIC_SUMMARY_CACHE_ENTRIES = 100;

function getExtensionFromMimeType(mimeType: string) {
  switch (mimeType) {
    case 'image/png':
      return 'png';
    case 'image/jpeg':
      return 'jpeg';
    case 'image/webp':
      return 'webp';
  }
  throw new Error(`No mapping for Mime type ${mimeType}.`);
}

export class McpContext implements Context {
  browserContext: BrowserContext;
  sessionProvider: CdpSessionProvider;
  logger: Debugger;

  // The most recent page state.
  #pages: Page[] = [];
  #pageToDevToolsPage = new Map<Page, Page>();
  #selectedPage?: Page;
  #networkCollector: NetworkCollector;
  #consoleCollector: ConsoleCollector;
  #webSocketCollector: WebSocketCollector;

  #dialog?: Dialog;
  #debuggerContext: DebuggerContext = new DebuggerContext();
  #selectedFrame?: Frame;

  #trafficSummaryCache = new WeakMap<
    Page,
    Map<number, {version: number; summary: TrafficSummary}>
  >();

  private constructor(browserContext: BrowserContext, logger: Debugger) {
    this.browserContext = browserContext;
    this.sessionProvider = new CdpSessionProvider(browserContext);
    this.logger = logger;

    this.#networkCollector = new NetworkCollector(
      this.browserContext,
      this.sessionProvider,
      undefined,
    );

    this.#consoleCollector = new ConsoleCollector(
      this.browserContext,
      collect => {
        return {
          console: event => {
            collect(event);
          },
          pageerror: event => {
            if (event instanceof Error) {
              collect(event);
            } else {
              const error = new Error(`${event}`);
              error.stack = undefined;
              collect(error);
            }
          },
        } as ListenerMap;
      },
    );

    this.#webSocketCollector = new WebSocketCollector(
      this.browserContext,
      this.sessionProvider,
    );
  }

  #initializedCapabilities = new Set<ToolCapability>();
  #capabilityInitializers = new Map<ToolCapability, Promise<void>>();

  async #init() {
    await this.createPagesSnapshot();
    // NOTE: addInitScript is already called in browser.ts (launch/connect).
    // Do NOT call it again here — double injection causes scripts to run twice
    // per page load, which can create detectable discrepancies.

    // Initialize Playwright-level listeners early so that page load requests
    // and console messages are captured immediately. These only register
    // Node.js event listeners on Playwright objects — no extra CDP domains
    // are activated, so anti-bot systems cannot detect them.
    await this.#networkCollector.init();
    await this.#consoleCollector.init();

    // NOTE: CDP-heavy collectors (initiator collection, WebSocket CDP events,
    // Debugger.enable) are NOT initialized here.
    // They are lazily initialized on first tool use that needs them,
    // via ensureCapabilities(). This prevents unrelated CDP domain activation
    // from leaking automation signals during page navigation.
  }

  /**
   * Lazily initialize CDP-dependent collectors (network, websocket, debugger).
   * Called before any tool that needs collected data.
   * This defers CDP domain activation so that page navigations happen in a
   * "clean" state without Debugger/Network/Runtime domains enabled.
   */
  async ensureCapabilities(
    capabilities: readonly ToolCapability[],
  ): Promise<void> {
    for (const capability of capabilities) {
      await this.#ensureCapability(capability);
    }
  }

  async #ensureCapability(capability: ToolCapability): Promise<void> {
    if (this.#initializedCapabilities.has(capability)) {
      // A popup can be created by the page between tool calls. Collector init
      // is idempotent and drains any per-page setup already started by the
      // browser-context event, so "capability ready" also covers current pages.
      if (capability === 'network') {
        await this.#networkCollector.initCdp();
      } else if (capability === 'websocket') {
        await this.#webSocketCollector.init();
      }
      return;
    }
    const pending = this.#capabilityInitializers.get(capability);
    if (pending) {
      await pending;
      return;
    }

    const initializer = (async () => {
      this.logger(`Initializing capability: ${capability}`);
      switch (capability) {
        case 'network':
          await this.#networkCollector.initCdp();
          break;
        case 'websocket':
          await this.#webSocketCollector.init();
          break;
        case 'debugger':
          await this.#initDebugger();
          break;
        case 'devtools-ui':
          await this.detectOpenDevToolsWindows();
          break;
      }
      this.#initializedCapabilities.add(capability);
    })();
    this.#capabilityInitializers.set(capability, initializer);
    try {
      await initializer;
    } finally {
      this.#capabilityInitializers.delete(capability);
    }
  }

  async #initDebugger(frame?: Frame): Promise<void> {
    const page = this.getSelectedPage();
    if (!page) {
      return;
    }
    const savedBreakpoints = this.#debuggerContext.getBreakpoints();
    try {
      let client;
      if (frame && frame !== page.mainFrame()) {
        client = await this.sessionProvider.getSession(frame);
      } else {
        client = await this.sessionProvider.getSession(page);
      }
      await this.#debuggerContext.enable(client);
      if (savedBreakpoints.length > 0) {
        await this.#debuggerContext.restoreBreakpoints(savedBreakpoints);
      }
      await this.#debuggerContext.restoreXHRBreakpoints();
    } catch (error) {
      this.logger('Failed to initialize debugger context', error);
      throw error;
    }
  }

  dispose() {
    this.#networkCollector.dispose();
    this.#consoleCollector.dispose();
    this.#webSocketCollector.dispose();
    void this.#debuggerContext.disable();
  }

  /**
   * Get the debugger context for script/breakpoint management.
   */
  get debuggerContext(): DebuggerContext {
    return this.#debuggerContext;
  }

  /**
   * Reinitialize the debugger for the current page.
   * Clears stale script IDs, re-enables the debugger to receive fresh
   * scriptParsed events, and restores any previously set breakpoints.
   * Called after selecting a new page or after in-page navigation
   * (goto/reload/back/forward).
   */
  async reinitDebugger(): Promise<void> {
    if (!this.#initializedCapabilities.has('debugger')) return;
    await this.#debuggerContext.disable({preserveBreakpoints: true});
    try {
      await this.#initDebugger();
    } catch (error) {
      // The capability is no longer ready. A later debugger tool call will
      // retry initialization through the normal single-flight path.
      this.#initializedCapabilities.delete('debugger');
      throw error;
    }
  }

  /**
   * Reinitialize the debugger for a specific frame's CDP session.
   * This enables script collection from cross-origin iframes (OOPIFs).
   */
  async reinitDebuggerForFrame(frame: Frame): Promise<void> {
    if (!this.#initializedCapabilities.has('debugger')) return;
    await this.#debuggerContext.disable({preserveBreakpoints: true});
    try {
      await this.#initDebugger(frame);
    } catch (error) {
      this.#initializedCapabilities.delete('debugger');
      throw error;
    }
  }

  static async from(browserContext: BrowserContext, logger: Debugger) {
    const context = new McpContext(browserContext, logger);
    await context.#init();
    return context;
  }

  resolveCdpRequestId(cdpRequestId: string): number | undefined {
    const selectedPage = this.getSelectedPage();
    if (!cdpRequestId) {
      this.logger('no network request');
      return;
    }
    const request = this.#networkCollector.find(selectedPage, request => {
      return this.#networkCollector.getCdpRequestId(request) === cdpRequestId;
    });
    if (!request) {
      this.logger('no network request for ' + cdpRequestId);
      return;
    }
    return this.#networkCollector.getIdForResource(request);
  }

  getNetworkRequests(): HTTPRequest[] {
    const page = this.getSelectedPage();
    return this.#networkCollector.getData(page);
  }

  clearNetworkRequests(): {requestCount: number; reclaimedBytes: number} {
    const page = this.getSelectedPage();
    return this.#networkCollector.clear(page);
  }

  getConsoleData(
    includePreservedMessages?: boolean,
  ): Array<ConsoleMessage | Error> {
    const page = this.getSelectedPage();
    return this.#consoleCollector.getData(page, includePreservedMessages);
  }

  getConsoleMessageStableId(message: ConsoleMessage | Error): number {
    return this.#consoleCollector.getIdForResource(message);
  }

  getConsoleMessageById(id: number): ConsoleMessage | Error {
    return this.#consoleCollector.getById(this.getSelectedPage(), id);
  }

  async newPage(): Promise<Page> {
    const page = await this.browserContext.newPage();
    await this.createPagesSnapshot();
    await this.selectPage(page);
    // Always add to network/console collectors — their Playwright listeners
    // are active from startup. addPage() internally handles CDP setup if
    // initCdp() has already been called.
    await this.#networkCollector.addPage(page);
    await this.#consoleCollector.addPage(page);
    // WebSocket collector is fully CDP-based, only add if initialized.
    if (this.#initializedCapabilities.has('websocket')) {
      await this.#webSocketCollector.addPage(page);
    }
    return page;
  }
  async closePage(pageIdx: number): Promise<void> {
    if (this.#pages.length === 1) {
      throw new Error(CLOSE_PAGE_ERROR);
    }
    const page = this.getPageByIdx(pageIdx);
    await page.close({runBeforeUnload: false});
  }

  async stopPageLoading(page: Page): Promise<void> {
    const session = await this.sessionProvider.getSession(page);
    await session.send('Page.stopLoading');
  }

  getNetworkRequestById(reqid: number): HTTPRequest {
    return this.#networkCollector.getById(this.getSelectedPage(), reqid);
  }

  getDialog(): Dialog | undefined {
    return this.#dialog;
  }

  clearDialog(): void {
    this.#dialog = undefined;
  }

  getSelectedPage(): Page {
    const page = this.#selectedPage;
    if (!page) {
      throw new Error('No page selected');
    }
    if (page.isClosed()) {
      throw new Error(
        `The selected page has been closed. Call ${selectPage.name} to see open pages.`,
      );
    }
    return page;
  }

  getPageByIdx(idx: number): Page {
    const pages = this.#pages;
    const page = pages[idx];
    if (!page) {
      throw new Error('No page found');
    }
    return page;
  }

  #dialogHandler = (dialog: Dialog): void => {
    this.#dialog = dialog;
  };

  isPageSelected(page: Page): boolean {
    return this.#selectedPage === page;
  }

  async selectPage(newPage: Page): Promise<void> {
    const oldPage = this.#selectedPage;
    const oldFrame = this.#selectedFrame;
    if (oldPage) {
      oldPage.off('dialog', this.#dialogHandler);
    }
    this.#selectedPage = newPage;
    this.#selectedFrame = undefined;
    newPage.on('dialog', this.#dialogHandler);
    try {
      this.#setSelectedPageTimeouts();
      // Reinitialize debugger for the new page before exposing the selection
      // to the next tool call.
      await this.reinitDebugger();
    } catch (error) {
      newPage.off('dialog', this.#dialogHandler);
      if (oldPage && !oldPage.isClosed()) {
        this.#selectedPage = oldPage;
        this.#selectedFrame = oldFrame?.isDetached() ? undefined : oldFrame;
        oldPage.on('dialog', this.#dialogHandler);
        this.#setSelectedPageTimeouts();
      }
      throw error;
    }
  }

  getSelectedFrame(): Frame {
    return this.#selectedFrame ?? this.getSelectedPage().mainFrame();
  }

  async selectFrame(frame: Frame): Promise<void> {
    // Reinitialize debugger for the frame's CDP session
    // so that scripts from cross-origin iframes (OOPIFs) are visible
    await this.reinitDebuggerForFrame(frame);
    if (frame.isDetached()) {
      throw new ToolError(
        'CONFLICT',
        'The selected frame was detached while its debugger session was being initialized. List frames and retry with the new frame index.',
        {retryable: true},
      );
    }
    this.#selectedFrame = frame;
  }

  async resetSelectedFrame(): Promise<void> {
    // Reinitialize debugger for the main page's CDP session
    await this.reinitDebugger();
    this.#selectedFrame = undefined;
  }

  #setSelectedPageTimeouts() {
    const page = this.getSelectedPage();
    page.setDefaultTimeout(DEFAULT_TIMEOUT);
    page.setDefaultNavigationTimeout(NAVIGATION_TIMEOUT);
  }

  /**
   * Creates a snapshot of the pages.
   */
  async createPagesSnapshot(): Promise<Page[]> {
    const allPages = this.browserContext.pages();

    this.#pages = allPages.filter(
      page => !page.url().startsWith('devtools://'),
    );

    if (!this.#selectedPage || this.#pages.indexOf(this.#selectedPage) === -1) {
      await this.selectPage(this.#pages[0]);
    }

    // Skip DevTools window detection when collectors aren't initialized.
    // detectOpenDevToolsWindows() creates CDP sessions which leak automation
    // signals to anti-bot systems during navigation.
    if (this.#initializedCapabilities.has('devtools-ui')) {
      await this.detectOpenDevToolsWindows();
    }

    return this.#pages;
  }

  async detectOpenDevToolsWindows() {
    this.logger('Detecting open DevTools windows');
    const pages = this.browserContext.pages();
    this.#pageToDevToolsPage = new Map<Page, Page>();
    for (const devToolsPage of pages) {
      if (devToolsPage.url().startsWith('devtools://')) {
        try {
          this.logger('Calling getTargetInfo for ' + devToolsPage.url());
          const session = await this.sessionProvider.getSession(devToolsPage);
          const data = await session.send('Target.getTargetInfo');
          const devtoolsPageTitle = data.targetInfo.title;
          const urlLike = extractUrlLikeFromDevToolsTitle(devtoolsPageTitle);
          if (!urlLike) {
            continue;
          }
          // TODO: lookup without a loop.
          for (const page of this.#pages) {
            if (urlsEqual(page.url(), urlLike)) {
              this.#pageToDevToolsPage.set(page, devToolsPage);
            }
          }
        } catch (error) {
          this.logger('Issue occurred while trying to find DevTools', error);
        }
      }
    }
  }

  getPages(): Page[] {
    return this.#pages;
  }

  getDevToolsPage(page: Page): Page | undefined {
    return this.#pageToDevToolsPage.get(page);
  }

  async getDevToolsData(): Promise<DevToolsData> {
    try {
      this.logger('Getting DevTools UI data');
      const selectedPage = this.getSelectedPage();
      const devtoolsPage = this.getDevToolsPage(selectedPage);
      if (!devtoolsPage) {
        this.logger('No DevTools page detected');
        return {};
      }
      const {cdpRequestId, cdpBackendNodeId} = await devtoolsPage.evaluate(
        async () => {
          // @ts-expect-error no types
          const UI = await import('/bundled/ui/legacy/legacy.js');
          // @ts-expect-error no types
          const SDK = await import('/bundled/core/sdk/sdk.js');
          const request = UI.Context.Context.instance().flavor(
            SDK.NetworkRequest.NetworkRequest,
          );
          const node = UI.Context.Context.instance().flavor(
            SDK.DOMModel.DOMNode,
          );
          return {
            cdpRequestId: request?.requestId(),
            cdpBackendNodeId: node?.backendNodeId(),
          };
        },
      );
      return {cdpBackendNodeId, cdpRequestId};
    } catch (err) {
      this.logger('error getting devtools data', err);
    }
    return {};
  }

  async saveTemporaryFile(
    data: Uint8Array<ArrayBufferLike>,
    mimeType: 'image/png' | 'image/jpeg' | 'image/webp',
  ): Promise<{filename: string}> {
    try {
      const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'js-reverse-mcp-'));

      const filename = path.join(
        dir,
        `screenshot.${getExtensionFromMimeType(mimeType)}`,
      );
      await fs.writeFile(filename, data, {mode: 0o600});
      return {filename};
    } catch (err) {
      this.logger(err);
      throw new Error('Could not save a screenshot to a file', {cause: err});
    }
  }
  async saveFile(
    data: Uint8Array<ArrayBufferLike>,
    filename: string,
    options: {confirmOverwrite?: boolean} = {},
  ): Promise<{filename: string}> {
    let filePath = path.resolve(filename);
    try {
      filePath = assertLocalFileWriteAllowed(filePath);
      const flags =
        fsConstants.O_WRONLY |
        fsConstants.O_CREAT |
        fsConstants.O_NOFOLLOW |
        fsConstants.O_NONBLOCK |
        (options.confirmOverwrite ? 0 : fsConstants.O_EXCL);
      const handle = await fs.open(filePath, flags, 0o600);
      try {
        if (!(await handle.stat()).isFile()) {
          throw new ToolError(
            'INVALID_ARGUMENT',
            `Local file output must target a regular file: ${filePath}`,
          );
        }
        await handle.chmod(0o600);
        if (options.confirmOverwrite) {
          await handle.truncate(0);
        }
        await handle.writeFile(data);
      } finally {
        await handle.close();
      }
      return {filename: filePath};
    } catch (err) {
      if (err instanceof ToolError) {
        throw err;
      }
      if (
        typeof err === 'object' &&
        err !== null &&
        'code' in err &&
        err.code === 'EEXIST'
      ) {
        throw new ToolError(
          'CONFIRMATION_REQUIRED',
          `File already exists: ${filePath}. Pass confirmOverwrite=true to replace it.`,
          {cause: err},
        );
      }
      if (
        typeof err === 'object' &&
        err !== null &&
        'code' in err &&
        (err.code === 'ELOOP' || err.code === 'EMLINK')
      ) {
        throw new ToolError(
          'PERMISSION_DENIED',
          `Refusing to write through a symbolic link: ${filePath}`,
          {cause: err},
        );
      }
      this.logger(err);
      throw new ToolError('IO_ERROR', 'Could not save file', {cause: err});
    }
  }

  getWaitForHelper(page: Page) {
    return WaitForHelper.create(page, this.sessionProvider);
  }

  async waitForEventsAfterAction(
    action: () => Promise<unknown>,
  ): Promise<void> {
    const page = this.getSelectedPage();
    const waitForHelper = await this.getWaitForHelper(page);
    return waitForHelper.waitForEventsAfterAction(action);
  }

  getNetworkRequestStableId(request: HTTPRequest): number {
    return this.#networkCollector.getIdForResource(request);
  }

  /**
   * Get the initiator (call stack) for a network request.
   */
  getRequestInitiator(request: HTTPRequest): RequestInitiator | undefined {
    const page = this.getSelectedPage();
    return this.#networkCollector.getInitiator(page, request);
  }

  /**
   * Get the initiator by request ID.
   */
  getRequestInitiatorById(requestId: number): RequestInitiator | undefined {
    const page = this.getSelectedPage();
    const request = this.#networkCollector.getById(page, requestId);
    return this.#networkCollector.getInitiator(page, request);
  }

  /**
   * Get all WebSocket connections for the selected page.
   */
  getWebSocketConnections(includePreservedData?: boolean): WebSocketData[] {
    const page = this.getSelectedPage();
    return this.#webSocketCollector.getData(page, includePreservedData);
  }

  /**
   * Get a WebSocket connection by stable ID.
   */
  getWebSocketById(wsid: number): WebSocketData {
    const page = this.getSelectedPage();
    return this.#webSocketCollector.getById(page, wsid);
  }

  /**
   * Get stable ID for a WebSocket connection.
   */
  getWebSocketStableId(ws: WebSocketData): number {
    return this.#webSocketCollector.getIdForResource(ws);
  }

  /**
   * Cache traffic summary for a WebSocket connection.
   */
  cacheTrafficSummary(
    wsid: number,
    version: number,
    summary: TrafficSummary,
  ): void {
    const page = this.getSelectedPage();
    let cache = this.#trafficSummaryCache.get(page);
    if (!cache) {
      cache = new Map();
      this.#trafficSummaryCache.set(page, cache);
    }
    cache.delete(wsid);
    cache.set(wsid, {version, summary});
    while (cache.size > MAX_TRAFFIC_SUMMARY_CACHE_ENTRIES) {
      const oldestWsid = cache.keys().next().value;
      if (oldestWsid === undefined) {
        break;
      }
      cache.delete(oldestWsid);
    }
  }

  /**
   * Get cached traffic summary for a WebSocket connection.
   */
  getCachedTrafficSummary(
    wsid: number,
    version: number,
  ): TrafficSummary | undefined {
    const cache = this.#trafficSummaryCache.get(this.getSelectedPage());
    const entry = cache?.get(wsid);
    if (entry?.version !== version) {
      cache?.delete(wsid);
      return undefined;
    }
    return entry.summary;
  }

  async waitForTextOnPage({
    text,
    timeout,
  }: {
    text: string;
    timeout?: number | undefined;
  }): Promise<Element> {
    const page = this.getSelectedPage();
    const frames = page.frames();

    // Use Promise.race with Playwright's getByText across all frames
    const locators = frames.flatMap(frame => [
      frame.getByRole('link', {name: text}),
      frame.getByRole('button', {name: text}),
      frame.getByText(text),
    ]);

    const waitPromises = locators.map(locator =>
      locator.waitFor({timeout: timeout ?? 5000}).catch(() => null),
    );

    await Promise.race(waitPromises);
    return undefined as unknown as Element;
  }

  /**
   * We need to ignore favicon request as they make our test flaky
   */
  async setUpNetworkCollectorForTesting() {
    this.#networkCollector = new NetworkCollector(
      this.browserContext,
      this.sessionProvider,
      collect => {
        return {
          request: req => {
            if (req.url().includes('favicon.ico')) {
              return;
            }
            collect(req);
          },
        } as ListenerMap;
      },
    );
    await this.#networkCollector.init();
  }
}
