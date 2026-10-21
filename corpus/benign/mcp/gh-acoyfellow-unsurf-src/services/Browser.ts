import { Context, Effect, Layer, Ref, type Scope, Stream } from "effect";
import type { BrowserError } from "../domain/Errors.js";
import { isApiRequest, NetworkEvent } from "../domain/NetworkEvent.js";

// ==================== Service Interface ====================

export interface BrowserService {
	/** Navigate to a URL and wait for network idle */
	readonly navigate: (url: string) => Effect.Effect<void, BrowserError>;
	/** Start capturing network events, returns a stream */
	readonly captureNetwork: () => Effect.Effect<
		Stream.Stream<NetworkEvent, BrowserError>,
		BrowserError
	>;
	/** Take a screenshot (PNG bytes) */
	readonly screenshot: () => Effect.Effect<Uint8Array, BrowserError>;
	/** Evaluate JS in the page context */
	readonly evaluate: <T>(fn: string | (() => T)) => Effect.Effect<T, BrowserError>;
	/** Click an element */
	readonly click: (selector: string) => Effect.Effect<void, BrowserError>;
	/** Type into an element */
	readonly type: (selector: string, text: string) => Effect.Effect<void, BrowserError>;
	/** Wait for a selector to appear */
	readonly waitForSelector: (selector: string) => Effect.Effect<void, BrowserError>;
	/** Wait for navigation to complete */
	readonly waitForNavigation: () => Effect.Effect<void, BrowserError>;
	/** Get captured network events so far */
	readonly getNetworkEvents: () => Effect.Effect<ReadonlyArray<NetworkEvent>>;
	/** Close the browser */
	readonly close: () => Effect.Effect<void>;
}

export class Browser extends Context.Tag("Browser")<Browser, BrowserService>() {}

// ==================== Cloudflare Browser Rendering Implementation ====================

import type { BrowserWorker, HTTPResponse } from "@cloudflare/puppeteer";
import puppeteer from "@cloudflare/puppeteer";

type PendingRequest = {
	url: string;
	method: string;
	resourceType: string;
	headers: Record<string, string>;
	postData?: string | undefined;
	timestamp: number;
};

const READABLE_CONTENT_TYPES = ["json", "text", "xml", "form"];

async function tryReadResponseBody(res: HTTPResponse): Promise<string | undefined> {
	try {
		const contentType = res.headers()["content-type"] ?? "";
		if (READABLE_CONTENT_TYPES.some((t) => contentType.includes(t))) {
			return await res.text();
		}
	} catch {
		// Some responses can't be read (e.g., redirects)
	}
	return undefined;
}

async function resolveResponseEvent(
	res: HTTPResponse,
	requestIdMap: WeakMap<object, string>,
	pendingRequests: Map<string, PendingRequest>,
): Promise<NetworkEvent | null> {
	const req = res.request();
	const id = requestIdMap.get(req);
	if (!id) return null;

	const pending = pendingRequests.get(id);
	if (!pending) return null;
	pendingRequests.delete(id);

	const responseBody = await tryReadResponseBody(res);

	return new NetworkEvent({
		requestId: id,
		url: pending.url,
		method: pending.method,
		resourceType: pending.resourceType,
		requestHeaders: pending.headers,
		requestBody: pending.postData,
		responseStatus: res.status(),
		responseHeaders: res.headers(),
		responseBody,
		timestamp: pending.timestamp,
	});
}

export function makeCfBrowser(
	binding: BrowserWorker,
): Effect.Effect<BrowserService, BrowserError, Scope.Scope> {
	return Effect.gen(function* () {
		const { BrowserError: BrowserErr } = yield* Effect.promise(() => import("../domain/Errors.js"));

		const browser = yield* Effect.acquireRelease(
			Effect.tryPromise({
				try: () => puppeteer.launch(binding),
				catch: (e) => new BrowserErr({ message: `Launch failed: ${e}` }),
			}),
			(b) => Effect.promise(() => b.close().catch(() => {})),
		);

		const page = yield* Effect.tryPromise({
			try: () => browser.newPage(),
			catch: (e) => new BrowserErr({ message: `New page failed: ${e}` }),
		});

		yield* Effect.tryPromise({
			try: () => page.setUserAgent("unsurf/0.2.0 (API discovery tool; https://unsurf.coey.dev)"),
			catch: (e) => new BrowserErr({ message: `Set user-agent failed: ${e}` }),
		});

		// Collected events buffer
		const eventsRef = yield* Ref.make<NetworkEvent[]>([]);

		// Track pending requests so we can pair request → response
		const pendingRequests = new Map<string, PendingRequest>();

		let networkStreamPush: ((event: NetworkEvent) => void) | null = null;
		let networkStreamEnd: (() => void) | null = null;

		// Map request objects to our tracking IDs (avoids monkey-patching with `any`)
		const requestIdMap = new WeakMap<object, string>();

		// Wire up request interception
		yield* Effect.tryPromise({
			try: () => page.setRequestInterception(true),
			catch: (e) => new BrowserErr({ message: `Interception setup failed: ${e}` }),
		});

		page.on("request", (req) => {
			const id = `${req.method()}-${req.url()}-${Date.now()}`;
			if (isApiRequest(req.resourceType(), req.url())) {
				pendingRequests.set(id, {
					url: req.url(),
					method: req.method(),
					resourceType: req.resourceType(),
					headers: req.headers(),
					postData: req.postData(),
					timestamp: Date.now(),
				});
				requestIdMap.set(req, id);
			}
			req.continue();
		});

		page.on("response", async (res) => {
			try {
				const event = await resolveResponseEvent(res, requestIdMap, pendingRequests);
				if (!event) return;

				Effect.runSync(Ref.update(eventsRef, (arr) => [...arr, event]));
				networkStreamPush?.(event);
			} catch {
				// Swallow errors in event collection
			}
		});

		const service: BrowserService = {
			navigate: (url) =>
				Effect.tryPromise({
					try: () => page.goto(url, { waitUntil: "networkidle0", timeout: 30_000 }).then(() => {}),
					catch: (e) => new BrowserErr({ message: `Navigate to ${url} failed: ${e}` }),
				}),

			captureNetwork: () =>
				Effect.succeed(
					Stream.async<NetworkEvent, BrowserError>((emit) => {
						networkStreamPush = (event) => emit.single(event);
						networkStreamEnd = () => emit.end();
					}),
				),

			screenshot: () =>
				Effect.tryPromise({
					try: async () => {
						const buf = await page.screenshot({ type: "png" });
						if (buf instanceof Uint8Array) return buf;
						return new Uint8Array(buf as ArrayBuffer);
					},
					catch: (e) => new BrowserErr({ message: `Screenshot failed: ${e}` }),
				}),

			evaluate: ((fn: string | (() => unknown)) =>
				Effect.tryPromise({
					try: () => page.evaluate(fn as () => unknown),
					catch: (e) => new BrowserErr({ message: `Evaluate failed: ${e}` }),
				})) as BrowserService["evaluate"],

			click: (selector) =>
				Effect.tryPromise({
					try: () => page.click(selector),
					catch: (e) => new BrowserErr({ message: `Click ${selector} failed: ${e}` }),
				}),

			type: (selector, text) =>
				Effect.tryPromise({
					try: () => page.type(selector, text),
					catch: (e) => new BrowserErr({ message: `Type into ${selector} failed: ${e}` }),
				}),

			waitForSelector: (selector) =>
				Effect.tryPromise({
					try: () => page.waitForSelector(selector, { timeout: 10_000 }).then(() => {}),
					catch: (e) => new BrowserErr({ message: `Wait for ${selector} timed out: ${e}` }),
				}),

			waitForNavigation: () =>
				Effect.tryPromise({
					try: () =>
						page.waitForNavigation({ waitUntil: "networkidle0", timeout: 15_000 }).then(() => {}),
					catch: (e) => new BrowserErr({ message: `Wait for navigation failed: ${e}` }),
				}),

			getNetworkEvents: () => Ref.get(eventsRef),

			close: () =>
				Effect.sync(() => {
					networkStreamEnd?.();
				}),
		};

		return service;
	});
}

/** Layer that opens a CF browser and closes it when the scope ends */
export const BrowserCfLive = (binding: BrowserWorker) =>
	Layer.scoped(Browser, makeCfBrowser(binding));

// ==================== In-Memory Test Implementation ====================

export function makeTestBrowser(): BrowserService {
	const events: NetworkEvent[] = [];
	const pages = new Map<string, string>(); // url → "loaded"
	let currentUrl = "";

	return {
		navigate: (url) =>
			Effect.sync(() => {
				currentUrl = url;
				pages.set(url, "loaded");
			}),

		captureNetwork: () => Effect.succeed(Stream.fromIterable(events)),

		screenshot: () => Effect.succeed(new Uint8Array([0x89, 0x50, 0x4e, 0x47])), // PNG magic

		evaluate: () => Effect.succeed(undefined as never),

		click: (_selector) => Effect.void,

		type: (_selector, _text) => Effect.void,

		waitForSelector: (_selector) => Effect.void,

		waitForNavigation: () => Effect.void,

		getNetworkEvents: () => Effect.succeed(events),

		close: () => Effect.void,
	};
}

/** Configurable test browser that lets you inject network events */
export function makeTestBrowserWithEvents(injectedEvents: NetworkEvent[]): BrowserService {
	const base = makeTestBrowser();
	return {
		...base,
		captureNetwork: () => Effect.succeed(Stream.fromIterable(injectedEvents)),
		getNetworkEvents: () => Effect.succeed(injectedEvents),
	};
}

export const BrowserTestLive = Layer.succeed(Browser, makeTestBrowser());
