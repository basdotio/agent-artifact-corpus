/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type {Protocol} from 'devtools-protocol';

import {addCdpEventListener, removeCdpEventListener} from './CdpEvents.js';
import type {CdpSessionProvider} from './CdpSessionProvider.js';
import {logger} from './logger.js';
import type {
  BrowserContext,
  ConsoleMessage,
  Frame,
  HTTPRequest,
  Page,
  Response as HTTPResponse,
} from './third_party/index.js';

/**
 * Initiator information for a network request.
 * Contains the call stack when the request was initiated.
 */
export interface RequestInitiator {
  type:
    | 'parser'
    | 'script'
    | 'preload'
    | 'SignedExchange'
    | 'preflight'
    | 'other';
  url?: string;
  lineNumber?: number;
  columnNumber?: number;
  stack?: {
    callFrames: Array<{
      functionName: string;
      scriptId: string;
      url: string;
      lineNumber: number;
      columnNumber: number;
    }>;
    parent?: {
      callFrames: Array<{
        functionName: string;
        scriptId: string;
        url: string;
        lineNumber: number;
        columnNumber: number;
      }>;
    };
  };
}

// Playwright page events relevant for collection
interface PageEvents {
  console: ConsoleMessage;
  pageerror: Error;
  request: HTTPRequest;
  requestfailed: HTTPRequest;
  requestfinished: HTTPRequest;
  response: HTTPResponse;
  framenavigated: Frame;
}

export type ListenerMap<EventMap extends PageEvents = PageEvents> = {
  [K in keyof EventMap]?: (event: EventMap[K]) => void;
};

type PageEventName = keyof PageEvents;
type PageEventListener = (event: PageEvents[PageEventName]) => void;
type PageEventRegistrar = (
  name: PageEventName,
  listener: PageEventListener,
) => Page;

function pageListenerEntries(
  listeners: ListenerMap,
): Array<[PageEventName, PageEventListener]> {
  return Object.entries(listeners) as unknown as Array<
    [PageEventName, PageEventListener]
  >;
}

function addPageListener(
  page: Page,
  name: PageEventName,
  listener: PageEventListener,
): void {
  const onPageEvent = page.on.bind(page) as unknown as PageEventRegistrar;
  onPageEvent(name, listener);
}

function removePageListener(
  page: Page,
  name: PageEventName,
  listener: PageEventListener,
): void {
  const offPageEvent = page.off.bind(page) as unknown as PageEventRegistrar;
  offPageEvent(name, listener);
}

function createIdGenerator() {
  let i = 1;
  return () => {
    if (i === Number.MAX_SAFE_INTEGER) {
      i = 0;
    }
    return i++;
  };
}

export const stableIdSymbol = Symbol('stableIdSymbol');
export const networkRequestObservedAtSymbol = Symbol(
  'networkRequestObservedAtSymbol',
);

/**
 * Caches the response body buffer eagerly captured at `requestfinished` time,
 * before a subsequent navigation lets the browser evict it. Stored as a
 * Promise so concurrent readers dedupe onto a single capture. Lives on the
 * request object, so it is GC'd together with the request when its navigation
 * bucket is dropped.
 */
export const responseBodyCacheSymbol = Symbol('responseBodyCacheSymbol');

/**
 * Resolved size in bytes of the cached response body that was counted against
 * the per-page budget. Read synchronously when a request is evicted, so its
 * bytes can be reclaimed from the budget.
 */
const responseBodySizeSymbol = Symbol('responseBodySizeSymbol');

export type CachedResponseBody =
  | {ok: true; buffer: Buffer}
  | {ok: false; error: string}
  | {ok: 'skipped'; reason: string};

/**
 * Per-response size cap. Responses larger than this are not cached (they would
 * dominate memory); reads fall back to a live fetch instead.
 */
export const MAX_CACHED_BODY_BYTES = 5 * 1024 * 1024;

/**
 * Per-page total budget for cached response bodies. Once exceeded, further
 * responses are marked skipped rather than cached.
 */
export const MAX_CACHED_TOTAL_BYTES = 50 * 1024 * 1024;

/**
 * Bound simultaneous response.body() allocations independently of declared
 * byte sizes. Servers can omit or lie about content-length, so byte reservation
 * alone cannot constrain transient memory.
 */
export const MAX_IN_FLIGHT_BODY_CAPTURES = 8;

/**
 * Upper bound on retained network request records per page. The network
 * collector keeps a single flat FIFO queue (navigation-agnostic): once the
 * queue exceeds this cap the oldest request is evicted, and evicting a record
 * also reclaims its cached body bytes from the per-page budget so that budget is
 * a rolling window rather than a one-way ratchet. The analyst establishes a
 * clean baseline on demand via clear_network_requests, not via navigation — so
 * this is a memory backstop, not the workflow.
 */
const MAX_RETAINED_REQUESTS = 5000;

const BODY_CAPTURE_TIMEOUT_MS = 5000;

class BodyCaptureTimeoutError extends Error {}

/**
 * Upper bound on retained per-page initiator entries, sized to match the request
 * queue cap so an in-queue request still finds its initiator: initiators are
 * recorded on a different CDP event than the request record, so the two FIFOs
 * trim in lockstep rather than one stranding the other. Bounded by a FIFO cap
 * (oldest dropped first) and wiped wholesale by clear_network_requests.
 */
const MAX_INITIATOR_ENTRIES = 5000;

type WithSymbolId<T> = T & {
  [stableIdSymbol]?: number;
};

export class PageCollector<T> {
  #context: BrowserContext;
  #listenersInitializer: (
    collector: (item: T) => void,
  ) => ListenerMap<PageEvents>;
  #listeners = new WeakMap<Page, ListenerMap>();
  #pageCloseListeners = new WeakMap<Page, () => void>();
  #maxNavigationSaved = 3;
  #maxItemsPerNavigation = 1000;

  /**
   * This maps a Page to a list of navigations with a sub-list
   * of all collected resources.
   * The newer navigations come first.
   */
  protected storage = new WeakMap<Page, Array<Array<WithSymbolId<T>>>>();

  constructor(
    context: BrowserContext,
    listeners: (collector: (item: T) => void) => ListenerMap<PageEvents>,
  ) {
    this.#context = context;
    this.#listenersInitializer = listeners;
  }

  protected get context(): BrowserContext {
    return this.#context;
  }

  async init() {
    const pages = this.#context.pages();
    for (const page of pages) {
      await this.addPage(page);
    }

    this.#context.on('page', this.#onPageCreated);
  }

  dispose() {
    this.#context.off('page', this.#onPageCreated);
    for (const page of this.#context.pages()) {
      this.cleanupPageDestroyed(page);
    }
  }

  #onPageCreated = (page: Page) => {
    const initialization = this.addPage(page);
    void initialization.catch(error => {
      logger('Failed to initialize collector for a new page', error);
    });
  };

  public async addPage(page: Page): Promise<void> {
    this.#initializePage(page);
  }

  #initializePage(page: Page) {
    if (this.storage.has(page)) {
      return;
    }
    const idGenerator = createIdGenerator();
    const storedLists: Array<Array<WithSymbolId<T>>> = [[]];
    this.storage.set(page, storedLists);
    const onClose = () => this.cleanupPageDestroyed(page);
    this.#pageCloseListeners.set(page, onClose);
    page.on('close', onClose);

    const listeners = this.#listenersInitializer(value => {
      const withId = value as WithSymbolId<T>;
      withId[stableIdSymbol] = idGenerator();
      this.store(page, withId);
    });

    listeners['framenavigated'] = (frame: Frame) => {
      // Only split the storage on main frame navigation
      if (frame !== page.mainFrame()) {
        return;
      }
      this.splitAfterNavigation(page);
    };

    for (const [name, listener] of pageListenerEntries(listeners)) {
      addPageListener(page, name, listener);
    }

    this.#listeners.set(page, listeners);
  }

  /**
   * Append a collected item to the page's storage. Default implementation keeps
   * the bucketed-by-navigation model (current bucket capped at
   * #maxItemsPerNavigation). NetworkCollector overrides this with a flat FIFO.
   */
  protected store(page: Page, withId: WithSymbolId<T>): void {
    const navigations = this.storage.get(page) ?? [[]];
    navigations[0].push(withId);
    if (navigations[0].length > this.#maxItemsPerNavigation) {
      navigations[0].shift();
    }
  }

  protected splitAfterNavigation(page: Page) {
    const navigations = this.storage.get(page);
    if (!navigations) {
      return;
    }
    // Add the latest navigation first
    navigations.unshift([]);
    navigations.splice(this.#maxNavigationSaved);
  }

  protected cleanupPageDestroyed(page: Page) {
    const onClose = this.#pageCloseListeners.get(page);
    if (onClose) {
      page.off('close', onClose);
      this.#pageCloseListeners.delete(page);
    }
    const listeners = this.#listeners.get(page);
    if (listeners) {
      for (const [name, listener] of pageListenerEntries(listeners)) {
        removePageListener(page, name, listener);
      }
    }
    this.#listeners.delete(page);
    this.storage.delete(page);
  }

  getData(page: Page, includePreservedData?: boolean): T[] {
    const navigations = this.storage.get(page);
    if (!navigations) {
      return [];
    }

    if (!includePreservedData) {
      return navigations[0];
    }

    const data: T[] = [];
    // Return every retained navigation bucket, not a fixed window. Collectors
    // that trim on navigation (e.g. console) stay bounded; the network
    // collector keeps all buckets until the page closes, so a request stays
    // reachable as long as its object is alive — which is also what the eagerly
    // cached response body relies on.
    for (let index = navigations.length - 1; index >= 0; index--) {
      if (navigations[index]) {
        data.push(...navigations[index]);
      }
    }
    return data;
  }

  getIdForResource(resource: WithSymbolId<T>): number {
    return resource[stableIdSymbol] ?? -1;
  }

  getById(page: Page, stableId: number): T {
    const navigations = this.storage.get(page);
    if (!navigations) {
      throw new Error('No requests found for selected page');
    }

    const item = this.find(page, item => item[stableIdSymbol] === stableId);

    if (item) {
      return item;
    }

    throw new Error('Request not found for selected page');
  }

  find(
    page: Page,
    filter: (item: WithSymbolId<T>) => boolean,
  ): WithSymbolId<T> | undefined {
    const navigations = this.storage.get(page);
    if (!navigations) {
      return;
    }

    for (const navigation of navigations) {
      const item = navigation.find(filter);
      if (item) {
        return item;
      }
    }
    return;
  }
}

export class ConsoleCollector extends PageCollector<ConsoleMessage | Error> {}

const cdpRequestIdSymbol = Symbol('cdpRequestId');
const responseBodyPageSymbol = Symbol('responseBodyPage');
type RequestWithNetworkMetadata = HTTPRequest & {
  [cdpRequestIdSymbol]?: string;
  [networkRequestObservedAtSymbol]?: number;
  [responseBodyCacheSymbol]?: Promise<CachedResponseBody>;
  [responseBodySizeSymbol]?: number;
  [responseBodyPageSymbol]?: Page;
};

/**
 * Per-page running total of cached response body bytes. Keyed weakly so it is
 * released when the page is GC'd; also cleared explicitly on page destroy.
 */
interface ResponseBodyCacheState {
  bytes: number;
  generation: number;
  retained: Set<RequestWithNetworkMetadata>;
  reservedBytes: number;
  reservations: Set<{bytes: number; generation: number}>;
}

const responseBodyBudget = new WeakMap<Page, ResponseBodyCacheState>();

function getResponseBodyState(page: Page): ResponseBodyCacheState {
  let state = responseBodyBudget.get(page);
  if (!state) {
    state = {
      bytes: 0,
      generation: 0,
      retained: new Set(),
      reservedBytes: 0,
      reservations: new Set(),
    };
    responseBodyBudget.set(page, state);
  }
  return state;
}

function reserveResponseBodyCapture(
  state: ResponseBodyCacheState,
  declaredBytes: number,
): {bytes: number; generation: number} | undefined {
  if (state.reservations.size >= MAX_IN_FLIGHT_BODY_CAPTURES) {
    return undefined;
  }

  // Missing/zero lengths reserve the full per-response allowance. A declared
  // length still uses an in-flight slot in case the server understates it.
  const bytes =
    Number.isFinite(declaredBytes) && declaredBytes > 0
      ? declaredBytes
      : MAX_CACHED_BODY_BYTES;
  if (state.bytes + state.reservedBytes + bytes > MAX_CACHED_TOTAL_BYTES) {
    return undefined;
  }

  const reservation = {bytes, generation: state.generation};
  state.reservations.add(reservation);
  state.reservedBytes += bytes;
  return reservation;
}

function releaseResponseBodyReservation(
  state: ResponseBodyCacheState,
  reservation: {bytes: number; generation: number},
): void {
  if (!state.reservations.delete(reservation)) {
    return;
  }
  state.reservedBytes = Math.max(0, state.reservedBytes - reservation.bytes);
}

function pageForRequest(req: HTTPRequest): Page | undefined {
  try {
    // frame() can throw for service worker requests.
    return req.frame()?.page();
  } catch {
    return undefined;
  }
}

function withCaptureTimeout<T>(promise: Promise<T>): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  return Promise.race([
    promise,
    new Promise<never>(
      (_, reject) =>
        (timeoutId = setTimeout(
          () =>
            reject(
              new BodyCaptureTimeoutError('Timed out capturing response body'),
            ),
          BODY_CAPTURE_TIMEOUT_MS,
        )),
    ),
  ]).finally(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  });
}

/**
 * Eagerly fetch and cache a response body while the producing loader is still
 * alive (called from `requestfinished`). After a navigation the browser evicts
 * the body and a later `body()` call would fail; the cache lets inspect/export
 * still return it. Fire-and-forget: the Promise is stored on the request so
 * concurrent readers await the same capture.
 */
function captureResponseBody(req: HTTPRequest): void {
  const request = req as RequestWithNetworkMetadata;
  if (request[responseBodyCacheSymbol]) {
    return;
  }
  const page = pageForRequest(req) ?? request[responseBodyPageSymbol];
  if (!page) {
    request[responseBodyCacheSymbol] = Promise.resolve({
      ok: 'skipped',
      reason: 'request is not associated with a page cache budget',
    });
    return;
  }
  const state = getResponseBodyState(page);
  request[responseBodyCacheSymbol] = (async (): Promise<CachedResponseBody> => {
    let reservation: {bytes: number; generation: number} | undefined;
    try {
      if (!state.retained.has(request)) {
        return {
          ok: 'skipped',
          reason: 'response body cache generation was invalidated',
        };
      }
      const resp = await req.response();
      if (!resp) {
        return {ok: false, error: 'No response available'};
      }
      if (
        responseBodyBudget.get(page) !== state ||
        !state.retained.has(request)
      ) {
        return {
          ok: 'skipped',
          reason: 'response body cache generation was invalidated',
        };
      }
      const declared = Number(resp.headers()['content-length'] ?? 0);
      if (declared > MAX_CACHED_BODY_BYTES) {
        return {
          ok: 'skipped',
          reason: `content-length ${declared} exceeds cache limit`,
        };
      }
      reservation = reserveResponseBodyCapture(state, declared);
      if (!reservation) {
        return {
          ok: 'skipped',
          reason: 'page cache capture capacity exhausted',
        };
      }
      const bodyPromise = resp.body();
      let buffer: Buffer;
      try {
        buffer = await withCaptureTimeout(bodyPromise);
      } catch (error) {
        if (error instanceof BodyCaptureTimeoutError && reservation) {
          // The timeout only bounds readers of the cache promise; it does not
          // cancel Patchright's underlying body allocation. Keep the slot and
          // byte reservation until that operation really settles so repeated
          // timeouts cannot create unbounded concurrent allocations.
          const heldReservation = reservation;
          reservation = undefined;
          void bodyPromise
            .then(
              () => undefined,
              () => undefined,
            )
            .finally(() => {
              releaseResponseBodyReservation(state, heldReservation);
            });
        }
        throw error;
      }
      if (buffer.length > MAX_CACHED_BODY_BYTES) {
        return {
          ok: 'skipped',
          reason: `body ${buffer.length} bytes exceeds cache limit`,
        };
      }
      if (
        responseBodyBudget.get(page) !== state ||
        state.generation !== reservation.generation ||
        !state.retained.has(request)
      ) {
        return {
          ok: 'skipped',
          reason: 'response body cache generation was invalidated',
        };
      }
      if (
        state.bytes + state.reservedBytes - reservation.bytes + buffer.length >
        MAX_CACHED_TOTAL_BYTES
      ) {
        return {ok: 'skipped', reason: 'page cache budget exhausted'};
      }
      releaseResponseBodyReservation(state, reservation);
      reservation = undefined;
      state.bytes += buffer.length;
      // Record the counted size so eviction can reclaim it from the budget.
      request[responseBodySizeSymbol] = buffer.length;
      return {ok: true, buffer};
    } catch (error) {
      return {
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      };
    } finally {
      if (reservation) {
        releaseResponseBodyReservation(state, reservation);
      }
    }
  })();
}

function initiatorKey(url: string, method: string): string {
  return `${method} ${url}`;
}

export class NetworkCollector extends PageCollector<HTTPRequest> {
  // Initiators keyed by CDP requestId. Requires cdpRequestIdSymbol to have been
  // mapped onto the request, which races against event delivery.
  #initiators = new WeakMap<Page, Map<string, RequestInitiator>>();
  // Initiators keyed by "METHOD url". Order-independent fallback used when the
  // requestId mapping lost the race, so the initiator is still recoverable.
  #initiatorsByKey = new WeakMap<Page, Map<string, RequestInitiator>>();
  #cdpListeners = new WeakMap<Page, () => void>();
  #sessionProvider: CdpSessionProvider;
  #cdpRequested = false;
  #cdpInitialization?: Promise<void>;
  #pageCdpInitializations = new WeakMap<Page, Promise<void>>();
  #pendingCdpInitializations = new Set<Promise<void>>();

  constructor(
    context: BrowserContext,
    sessionProvider: CdpSessionProvider,
    listeners?: (
      collector: (item: HTTPRequest) => void,
    ) => ListenerMap<PageEvents>,
  ) {
    const baseListeners =
      listeners ??
      (collect => {
        return {
          request: req => {
            const request = req as RequestWithNetworkMetadata;
            request[networkRequestObservedAtSymbol] = Date.now();
            collect(req);
          },
        } as ListenerMap;
      });
    // Always capture the response body at requestfinished — before a navigation
    // can evict it — regardless of which listeners variant is supplied.
    super(context, collect => {
      const map = baseListeners(collect);
      const existingFinished = map.requestfinished;
      map.requestfinished = req => {
        captureResponseBody(req);
        existingFinished?.(req);
      };
      return map;
    });
    this.#sessionProvider = sessionProvider;
  }

  override async addPage(page: Page): Promise<void> {
    await super.addPage(page);
    if (this.#cdpRequested) {
      await this.#setupInitiatorCollection(page);
    }
  }

  /**
   * Initialize CDP-dependent features (initiator collection).
   * Called lazily to avoid leaking CDP signals during navigation.
   */
  async initCdp(): Promise<void> {
    this.#cdpRequested = true;
    if (this.#cdpInitialization) {
      await this.#cdpInitialization;
      return;
    }

    const initialization = this.#initializeCdp();
    this.#cdpInitialization = initialization;
    try {
      await initialization;
    } finally {
      if (this.#cdpInitialization === initialization) {
        this.#cdpInitialization = undefined;
      }
    }
  }

  async #initializeCdp(): Promise<void> {
    for (const page of this.context.pages()) {
      if (this.storage.has(page)) {
        // The pending set below is the source of truth; this catch prevents an
        // event-loop unhandled rejection before the drain observes a failure.
        void this.#setupInitiatorCollection(page).catch(() => undefined);
      }
    }
    await this.#drainCdpInitializations();
  }

  async #drainCdpInitializations(): Promise<void> {
    let firstError: unknown;
    let failed = false;
    while (this.#pendingCdpInitializations.size > 0) {
      const pending = [...this.#pendingCdpInitializations];
      const results = await Promise.allSettled(pending);
      const rejection = results.find(result => result.status === 'rejected');
      if (!failed && rejection?.status === 'rejected') {
        failed = true;
        firstError = rejection.reason;
      }
    }
    if (failed) {
      throw firstError;
    }
  }

  #setupInitiatorCollection(page: Page): Promise<void> {
    if (this.#cdpListeners.has(page)) {
      return Promise.resolve();
    }
    const pending = this.#pageCdpInitializations.get(page);
    if (pending) {
      return pending;
    }

    const operation = this.#performInitiatorSetup(page);
    const initialization = operation.finally(() => {
      if (this.#pageCdpInitializations.get(page) === initialization) {
        this.#pageCdpInitializations.delete(page);
      }
      this.#pendingCdpInitializations.delete(initialization);
    });
    this.#pageCdpInitializations.set(page, initialization);
    this.#pendingCdpInitializations.add(initialization);
    return initialization;
  }

  async #performInitiatorSetup(page: Page): Promise<void> {
    const initiatorMap = new Map<string, RequestInitiator>();
    const initiatorByKey = new Map<string, RequestInitiator>();
    const client = await this.#sessionProvider.getSession(page);
    if (!this.storage.has(page)) {
      return;
    }

    // Listen before enabling the domain so the first emitted request cannot
    // land in the gap between Network.enable and listener registration.
    const onRequestWillBeSent = (
      event: Protocol.Network.RequestWillBeSentEvent,
    ): void => {
      if (event.initiator) {
        initiatorMap.set(event.requestId, event.initiator as RequestInitiator);
        // Also key by URL+method so getInitiator can recover the initiator
        // even when the requestId mapping below loses the delivery race.
        initiatorByKey.set(
          initiatorKey(event.request.url, event.request.method),
          event.initiator as RequestInitiator,
        );
        // Bound memory: drop oldest entries beyond the cap (Map preserves
        // insertion order, so the first key is the oldest).
        while (initiatorMap.size > MAX_INITIATOR_ENTRIES) {
          const oldest = initiatorMap.keys().next().value;
          if (oldest === undefined) {
            break;
          }
          initiatorMap.delete(oldest);
        }
        while (initiatorByKey.size > MAX_INITIATOR_ENTRIES) {
          const oldest = initiatorByKey.keys().next().value;
          if (oldest === undefined) {
            break;
          }
          initiatorByKey.delete(oldest);
        }
      }

      // Map CDP request ID to Playwright Request via URL+method matching.
      const navigations = this.storage.get(page);
      if (navigations) {
        for (const navigation of navigations) {
          for (const request of navigation) {
            const req = request as RequestWithNetworkMetadata;
            if (
              !req[cdpRequestIdSymbol] &&
              req.url() === event.request.url &&
              req.method() === event.request.method
            ) {
              req[cdpRequestIdSymbol] = event.requestId;
              break;
            }
          }
        }
      }
    };

    const cleanup = () => {
      removeCdpEventListener(
        client,
        'Network.requestWillBeSent',
        onRequestWillBeSent,
      );
    };

    let listenerAttached = false;
    try {
      addCdpEventListener(
        client,
        'Network.requestWillBeSent',
        onRequestWillBeSent,
      );
      listenerAttached = true;
      await client.send('Network.enable');
      if (!this.storage.has(page)) {
        cleanup();
        return;
      }

      this.#initiators.set(page, initiatorMap);
      this.#initiatorsByKey.set(page, initiatorByKey);
      this.#cdpListeners.set(page, cleanup);
    } catch (error) {
      if (listenerAttached) {
        cleanup();
      }
      throw error;
    }
  }

  protected override cleanupPageDestroyed(page: Page): void {
    super.cleanupPageDestroyed(page);

    const cleanup = this.#cdpListeners.get(page);
    if (cleanup) {
      try {
        cleanup();
      } catch {
        // Page might already be closed
      }
    }
    this.#cdpListeners.delete(page);
    this.#initiators.delete(page);
    this.#initiatorsByKey.delete(page);
    responseBodyBudget.delete(page);
  }

  /**
   * Get the CDP request ID for a request.
   */
  getCdpRequestId(request: HTTPRequest): string | undefined {
    return (request as RequestWithNetworkMetadata)[cdpRequestIdSymbol];
  }

  /**
   * Get the initiator info for a request.
   * @param page The page the request belongs to
   * @param request The HTTP request
   * @returns The initiator info or undefined if not found
   */
  getInitiator(page: Page, request: HTTPRequest): RequestInitiator | undefined {
    // Preferred: exact CDP requestId match (when the mapping won the race).
    const requestId = this.getCdpRequestId(request);
    const byId = requestId
      ? this.#initiators.get(page)?.get(requestId)
      : undefined;
    if (byId) {
      return byId;
    }

    // Fallback: URL+method correlation. The requestId mapping requires the
    // Playwright request to already be in storage when the CDP event fires,
    // which races against event delivery; this lookup is order-independent.
    let url: string;
    let method: string;
    try {
      url = request.url();
      method = request.method();
    } catch {
      return undefined;
    }
    return this.#initiatorsByKey.get(page)?.get(initiatorKey(url, method));
  }

  /**
   * Get initiator by CDP request ID.
   */
  getInitiatorByRequestId(
    page: Page,
    requestId: string,
  ): RequestInitiator | undefined {
    const initiatorMap = this.#initiators.get(page);
    return initiatorMap?.get(requestId);
  }

  /**
   * Append a request to the page's flat FIFO queue. The network collector is
   * navigation-agnostic: a single bucket (index 0) holds the most recent
   * MAX_RETAINED_REQUESTS requests. Evicting the oldest reclaims its cached
   * response body bytes from the per-page budget, so the 50MB budget is a
   * rolling window, never a one-way ratchet.
   */
  protected override store(
    page: Page,
    withId: WithSymbolId<HTTPRequest>,
  ): void {
    const navigations = this.storage.get(page) ?? [[]];
    const queue = navigations[0];
    (withId as RequestWithNetworkMetadata)[responseBodyPageSymbol] = page;
    queue.push(withId);
    getResponseBodyState(page).retained.add(
      withId as RequestWithNetworkMetadata,
    );
    while (queue.length > MAX_RETAINED_REQUESTS) {
      const evicted = queue.shift();
      if (evicted) {
        this.#reclaimResponseBodyBudget(page, [evicted]);
      }
    }
  }

  /**
   * Navigation does not split or trim the network queue. Requests accumulate in
   * one FIFO bucket regardless of navigation, so a request that already fired
   * (e.g. the POST that triggered a redirect) stays inspectable afterwards. The
   * analyst trims on demand via clear(), not on navigation — see the method doc
   * and MAX_RETAINED_REQUESTS.
   */
  override splitAfterNavigation(_page: Page) {
    // Intentionally a no-op.
  }

  /**
   * Drop all collected requests for a page and release every parallel structure
   * that tracks them: the cached response body budget and both initiator maps.
   * Lets the analyst establish a clean baseline before the action they want to
   * study (the DevTools "clear, then act" workflow). The per-page stable-id
   * counter lives in a closure in #initializePage and is intentionally out of
   * reach here, so reqids stay monotonic and are never reused after a clear.
   */
  clear(page: Page): {requestCount: number; reclaimedBytes: number} {
    const navigations = this.storage.get(page);
    let requestCount = 0;
    if (navigations) {
      for (const bucket of navigations) {
        requestCount += bucket.length;
      }
    }

    const budget = getResponseBodyState(page);
    const reclaimedBytes = budget.bytes;
    budget.bytes = 0;
    budget.generation++;
    budget.retained.clear();
    // Keep in-flight reservations until their body() calls actually settle.
    // Releasing them here would let a new generation start another full batch
    // while the invalidated buffers are still being allocated.

    if (navigations) {
      for (const bucket of navigations) {
        for (const request of bucket) {
          const metadata = request as RequestWithNetworkMetadata;
          delete metadata[responseBodyCacheSymbol];
          delete metadata[responseBodySizeSymbol];
          delete metadata[responseBodyPageSymbol];
        }
      }
      navigations.length = 1;
      navigations[0] = [];
    }
    this.#initiators.get(page)?.clear();
    this.#initiatorsByKey.get(page)?.clear();

    return {requestCount, reclaimedBytes};
  }

  #reclaimResponseBodyBudget(page: Page, evicted: HTTPRequest[]): void {
    const budget = responseBodyBudget.get(page);
    if (!budget) {
      return;
    }
    for (const request of evicted) {
      const metadata = request as RequestWithNetworkMetadata;
      budget.retained.delete(metadata);
      const size = metadata[responseBodySizeSymbol];
      if (typeof size === 'number') {
        budget.bytes -= size;
      }
      delete metadata[responseBodyCacheSymbol];
      delete metadata[responseBodySizeSymbol];
      delete metadata[responseBodyPageSymbol];
    }
    if (budget.bytes < 0) {
      budget.bytes = 0;
    }
  }
}
