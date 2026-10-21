import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/d1";
import * as schema from "./schema.js";

export type Db = ReturnType<typeof createDb>;

export function createDb(d1: D1Database) {
	return drizzle(d1, { schema });
}

// ==================== Sites ====================

export function getSite(db: Db, id: string) {
	return db.select().from(schema.sites).where(eq(schema.sites.id, id)).get();
}

export function upsertSite(db: Db, site: schema.NewSite) {
	return db
		.insert(schema.sites)
		.values(site)
		.onConflictDoUpdate({
			target: schema.sites.id,
			set: { lastScoutedAt: site.lastScoutedAt },
		})
		.run();
}

// ==================== Endpoints ====================

export function getEndpointsBySite(db: Db, siteId: string) {
	return db.select().from(schema.endpoints).where(eq(schema.endpoints.siteId, siteId)).all();
}

export function upsertEndpoint(db: Db, endpoint: schema.NewEndpoint) {
	return db
		.insert(schema.endpoints)
		.values(endpoint)
		.onConflictDoUpdate({
			target: schema.endpoints.id,
			set: {
				requestSchema: endpoint.requestSchema,
				responseSchema: endpoint.responseSchema,
				requestHeaders: endpoint.requestHeaders,
				responseHeaders: endpoint.responseHeaders,
				sampleCount: endpoint.sampleCount,
				lastSeenAt: endpoint.lastSeenAt,
			},
		})
		.run();
}

// ==================== Paths ====================

export function getPath(db: Db, id: string) {
	return db.select().from(schema.paths).where(eq(schema.paths.id, id)).get();
}

export function getPathsBySite(db: Db, siteId: string) {
	return db.select().from(schema.paths).where(eq(schema.paths.siteId, siteId)).all();
}

export function upsertPath(db: Db, path: schema.NewPath) {
	return db
		.insert(schema.paths)
		.values(path)
		.onConflictDoUpdate({
			target: schema.paths.id,
			set: {
				steps: path.steps,
				endpointIds: path.endpointIds,
				status: path.status,
				lastUsedAt: path.lastUsedAt,
				failCount: path.failCount,
				healCount: path.healCount,
			},
		})
		.run();
}

// ==================== Runs ====================

export function insertRun(db: Db, run: schema.NewRun) {
	return db.insert(schema.runs).values(run).run();
}

export function getRunsByPath(db: Db, pathId: string) {
	return db.select().from(schema.runs).where(eq(schema.runs.pathId, pathId)).all();
}
