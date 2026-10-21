import { Context, Effect, Layer, Option } from "effect";
import {
	createDb,
	type Db,
	getEndpointsBySite,
	getPath,
	getPathsBySite,
	getSite,
	insertRun,
	upsertEndpoint,
	upsertPath,
	upsertSite,
} from "../db/queries.js";
import type { NewRun } from "../db/schema.js";
import type { CapturedEndpoint } from "../domain/Endpoint.js";
import { NotFoundError, StoreError } from "../domain/Errors.js";
import type { ScoutedPath } from "../domain/Path.js";
import type { Site } from "../domain/Site.js";

// ==================== Service Interface ====================

export interface StoreService {
	readonly saveSite: (site: Site) => Effect.Effect<void, StoreError>;
	readonly getSite: (id: string) => Effect.Effect<Site, NotFoundError | StoreError>;
	readonly saveEndpoints: (
		endpoints: ReadonlyArray<CapturedEndpoint>,
	) => Effect.Effect<void, StoreError>;
	readonly getEndpoints: (
		siteId: string,
	) => Effect.Effect<ReadonlyArray<CapturedEndpoint>, StoreError>;
	readonly savePath: (path: ScoutedPath) => Effect.Effect<void, StoreError>;
	readonly getPath: (id: string) => Effect.Effect<ScoutedPath, NotFoundError | StoreError>;
	readonly listPaths: (siteId: string) => Effect.Effect<ReadonlyArray<ScoutedPath>, StoreError>;
	readonly saveRun: (run: NewRun) => Effect.Effect<void, StoreError>;
	readonly saveBlob: (key: string, data: Uint8Array) => Effect.Effect<void, StoreError>;
	readonly getBlob: (key: string) => Effect.Effect<Uint8Array | null, StoreError>;
}

export class Store extends Context.Tag("Store")<Store, StoreService>() {}

// ==================== D1 + R2 Live Implementation ====================

export function makeD1Store(db: Db, r2: R2Bucket): StoreService {
	const tryDb = <A>(fn: () => Promise<A> | A) =>
		Effect.tryPromise({
			try: () => Promise.resolve(fn()),
			catch: (e) => new StoreError({ message: String(e) }),
		});

	return {
		saveSite: (site) =>
			tryDb(() =>
				upsertSite(db, {
					id: site.id,
					url: site.url,
					domain: site.domain,
					firstScoutedAt: site.firstScoutedAt,
					lastScoutedAt: site.lastScoutedAt,
				}),
			).pipe(Effect.asVoid),

		getSite: (id) =>
			tryDb(() => getSite(db, id)).pipe(
				Effect.flatMap((row) =>
					row
						? Effect.succeed(row as unknown as Site)
						: Effect.fail(new NotFoundError({ id, resource: "site" })),
				),
			),

		saveEndpoints: (endpoints) =>
			Effect.forEach(endpoints, (ep) =>
				tryDb(() =>
					upsertEndpoint(db, {
						id: ep.id,
						siteId: ep.siteId,
						method: ep.method,
						pathPattern: ep.pathPattern,
						requestSchema: JSON.stringify(ep.requestSchema),
						responseSchema: JSON.stringify(ep.responseSchema),
						sampleCount: ep.sampleCount,
						firstSeenAt: ep.firstSeenAt,
						lastSeenAt: ep.lastSeenAt,
					}),
				),
			).pipe(Effect.asVoid),

		getEndpoints: (siteId) =>
			tryDb(() => getEndpointsBySite(db, siteId)).pipe(
				Effect.map((rows) =>
					rows.map(
						(r) =>
							({
								id: r.id,
								siteId: r.siteId,
								method: r.method,
								pathPattern: r.pathPattern,
								requestSchema: r.requestSchema ? JSON.parse(r.requestSchema) : undefined,
								responseSchema: r.responseSchema ? JSON.parse(r.responseSchema) : undefined,
								sampleCount: r.sampleCount,
								firstSeenAt: r.firstSeenAt,
								lastSeenAt: r.lastSeenAt,
							}) as unknown as CapturedEndpoint,
					),
				),
			),

		savePath: (path) =>
			tryDb(() =>
				upsertPath(db, {
					id: path.id,
					siteId: path.siteId,
					task: path.task,
					steps: JSON.stringify(path.steps),
					endpointIds: JSON.stringify(path.endpointIds),
					status: path.status,
					createdAt: path.createdAt,
					lastUsedAt: Option.getOrUndefined(path.lastUsedAt),
					failCount: path.failCount,
					healCount: path.healCount,
				}),
			).pipe(Effect.asVoid),

		getPath: (id) =>
			tryDb(() => getPath(db, id)).pipe(
				Effect.flatMap((row) =>
					row
						? Effect.succeed({
								...row,
								steps: JSON.parse(row.steps),
								endpointIds: JSON.parse(row.endpointIds),
							} as unknown as ScoutedPath)
						: Effect.fail(new NotFoundError({ id, resource: "path" })),
				),
			),

		listPaths: (siteId) =>
			tryDb(() => getPathsBySite(db, siteId)).pipe(
				Effect.map((rows) =>
					rows.map(
						(r) =>
							({
								...r,
								steps: JSON.parse(r.steps),
								endpointIds: JSON.parse(r.endpointIds),
								lastUsedAt: r.lastUsedAt ? Option.some(r.lastUsedAt) : Option.none(),
							}) as unknown as ScoutedPath,
					),
				),
			),

		saveRun: (run) => tryDb(() => insertRun(db, run)).pipe(Effect.asVoid),

		saveBlob: (key, data) =>
			Effect.tryPromise({
				try: () => r2.put(key, data),
				catch: (e) => new StoreError({ message: `R2 put failed: ${e}` }),
			}).pipe(Effect.asVoid),

		getBlob: (key) =>
			Effect.tryPromise({
				try: async () => {
					const obj = await r2.get(key);
					if (!obj) return null;
					const buf = await obj.arrayBuffer();
					return new Uint8Array(buf);
				},
				catch: (e) => new StoreError({ message: `R2 get failed: ${e}` }),
			}),
	};
}

export const StoreD1Live = (d1: D1Database, r2: R2Bucket) =>
	Layer.succeed(Store, makeD1Store(createDb(d1), r2));

// ==================== In-Memory Test Implementation ====================

export function makeTestStore(): StoreService {
	const sites = new Map<string, Site>();
	const endpoints = new Map<string, CapturedEndpoint[]>();
	const pathsMap = new Map<string, ScoutedPath>();
	const runs: NewRun[] = [];
	const blobs = new Map<string, Uint8Array>();

	return {
		saveSite: (site) =>
			Effect.sync(() => {
				sites.set(site.id, site);
			}),

		getSite: (id) =>
			Effect.sync(() => sites.get(id)).pipe(
				Effect.flatMap((s) =>
					s ? Effect.succeed(s) : Effect.fail(new NotFoundError({ id, resource: "site" })),
				),
			),

		saveEndpoints: (eps) =>
			Effect.sync(() => {
				for (const ep of eps) {
					const existing = endpoints.get(ep.siteId) ?? [];
					const idx = existing.findIndex((e) => e.id === ep.id);
					if (idx >= 0) {
						existing[idx] = ep;
					} else {
						existing.push(ep);
					}
					endpoints.set(ep.siteId, existing);
				}
			}),

		getEndpoints: (siteId) => Effect.succeed(endpoints.get(siteId) ?? []),

		savePath: (path) =>
			Effect.sync(() => {
				pathsMap.set(path.id, path);
			}),

		getPath: (id) =>
			Effect.sync(() => pathsMap.get(id)).pipe(
				Effect.flatMap((p) =>
					p ? Effect.succeed(p) : Effect.fail(new NotFoundError({ id, resource: "path" })),
				),
			),

		listPaths: (siteId) =>
			Effect.succeed([...pathsMap.values()].filter((p) => p.siteId === siteId)),

		saveRun: (run) =>
			Effect.sync(() => {
				runs.push(run);
			}),

		saveBlob: (key, data) =>
			Effect.sync(() => {
				blobs.set(key, data);
			}),

		getBlob: (key) => Effect.succeed(blobs.get(key) ?? null),
	};
}

export const StoreTestLive = Layer.succeed(Store, makeTestStore());
