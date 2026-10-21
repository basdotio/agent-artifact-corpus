import { beforeEach, describe, expect, mock, test } from "bun:test";
import { Effect } from "effect";
import { Database } from "./Database.js";
import { Document } from "../types.js";

type PointId = string | number;

type PointRecord = {
  id: PointId;
  payload?: Record<string, unknown>;
  vector?: number[];
};

type CollectionState = {
  points: PointRecord[];
  vectors?: unknown;
  payloadIndexes: Array<{ field_name: string; field_schema?: unknown }>;
};

class FakeQdrantClient {
  readonly config: Record<string, unknown>;
  readonly collections = new Map<string, CollectionState>();

  constructor(config: Record<string, unknown>) {
    this.config = config;
  }

  async collectionExists(collection: string): Promise<{ exists: boolean }> {
    return { exists: this.collections.has(collection) };
  }

  async createCollection(
    collection: string,
    args: { vectors?: unknown },
  ): Promise<boolean> {
    if (!this.collections.has(collection)) {
      this.collections.set(collection, {
        points: [],
        vectors: args.vectors,
        payloadIndexes: [],
      });
    }
    return true;
  }

  async createPayloadIndex(
    collection: string,
    args: { field_name: string; field_schema?: unknown },
  ): Promise<{ status: string }> {
    const state = this.requireCollection(collection);
    state.payloadIndexes.push({
      field_name: args.field_name,
      field_schema: args.field_schema,
    });
    return { status: "ok" };
  }

  async upsert(
    collection: string,
    args: { points?: PointRecord[] },
  ): Promise<{ status: string }> {
    const state = this.requireCollection(collection);
    const points = args.points ?? [];

    for (const point of points) {
      const index = state.points.findIndex((candidate) => candidate.id === point.id);
      const nextPoint: PointRecord = {
        id: point.id,
        payload: point.payload,
        vector: point.vector,
      };
      if (index >= 0) {
        state.points[index] = nextPoint;
      } else {
        state.points.push(nextPoint);
      }
    }

    return { status: "ok" };
  }

  async retrieve(
    collection: string,
    args: { ids: PointId[]; with_payload?: boolean; with_vector?: boolean },
  ): Promise<PointRecord[]> {
    const state = this.requireCollection(collection);

    return args.ids
      .map((id) => state.points.find((point) => point.id === id))
      .filter((point): point is PointRecord => point !== undefined)
      .map((point) => this.projectPoint(point, args.with_payload, args.with_vector));
  }

  async scroll(
    collection: string,
    args?: {
      filter?: Record<string, unknown>;
      limit?: number;
      offset?: PointId;
      with_payload?: boolean;
      with_vector?: boolean;
    },
  ): Promise<{ points: PointRecord[]; next_page_offset: PointId | null }> {
    const state = this.requireCollection(collection);
    const filtered = state.points.filter((point) => this.matchesFilter(point, args?.filter));
    const sorted = [...filtered].sort((a, b) => compareIds(a.id, b.id));

    let start = 0;
    if (args?.offset !== undefined && args.offset !== null) {
      start = sorted.findIndex((point) => compareIds(point.id, args.offset as PointId) > 0);
      if (start < 0) start = sorted.length;
    }

    const limit = args?.limit ?? 10;
    const page = sorted.slice(start, start + limit);
    const next =
      start + limit < sorted.length && page.length > 0
        ? page[page.length - 1]!.id
        : null;

    return {
      points: page.map((point) =>
        this.projectPoint(point, args?.with_payload, args?.with_vector),
      ),
      next_page_offset: next,
    };
  }

  async delete(
    collection: string,
    args: { points?: PointId[]; filter?: Record<string, unknown> },
  ): Promise<{ status: string }> {
    const state = this.requireCollection(collection);

    if (args.points && args.points.length > 0) {
      state.points = state.points.filter((point) => !args.points!.includes(point.id));
      return { status: "ok" };
    }

    if (args.filter) {
      state.points = state.points.filter((point) => !this.matchesFilter(point, args.filter));
      return { status: "ok" };
    }

    return { status: "ok" };
  }

  async setPayload(
    collection: string,
    args: {
      payload: Record<string, unknown>;
      points?: PointId[];
      filter?: Record<string, unknown>;
    },
  ): Promise<{ status: string }> {
    const state = this.requireCollection(collection);

    for (const point of state.points) {
      const matchesPoints = args.points ? args.points.includes(point.id) : false;
      const matchesFilter = args.filter ? this.matchesFilter(point, args.filter) : false;
      const shouldUpdate =
        (args.points && matchesPoints) || (args.filter && matchesFilter);

      if (!shouldUpdate) continue;

      point.payload = {
        ...(point.payload ?? {}),
        ...args.payload,
      };
    }

    return { status: "ok" };
  }

  async count(
    collection: string,
    args?: { filter?: Record<string, unknown> },
  ): Promise<{ count: number }> {
    const state = this.requireCollection(collection);
    return {
      count: state.points.filter((point) => this.matchesFilter(point, args?.filter)).length,
    };
  }

  async search(
    collection: string,
    args: {
      vector: number[];
      limit?: number;
      with_payload?: boolean;
      with_vector?: boolean;
      filter?: Record<string, unknown>;
      score_threshold?: number;
    },
  ): Promise<Array<PointRecord & { score: number }>> {
    const state = this.requireCollection(collection);

    const scored = state.points
      .filter((point) => Array.isArray(point.vector))
      .filter((point) => this.matchesFilter(point, args.filter))
      .map((point) => {
        const score = cosineSimilarity(point.vector!, args.vector);
        return {
          ...this.projectPoint(point, args.with_payload, args.with_vector),
          score,
        };
      })
      .filter((point) => {
        if (args.score_threshold === undefined || args.score_threshold === null) {
          return true;
        }
        return point.score >= args.score_threshold;
      })
      .sort((a, b) => b.score - a.score);

    return scored.slice(0, args.limit ?? 10);
  }

  private projectPoint(
    point: PointRecord,
    withPayload: boolean | undefined,
    withVector: boolean | undefined,
  ): PointRecord {
    return {
      id: point.id,
      payload: withPayload === false ? undefined : point.payload,
      vector: withVector ? point.vector : undefined,
    };
  }

  private matchesFilter(point: PointRecord, filter?: Record<string, unknown>): boolean {
    if (!filter) return true;

    const must = toArray((filter as any).must);
    if (must.length > 0 && !must.every((condition) => this.matchesCondition(point, condition))) {
      return false;
    }

    const should = toArray((filter as any).should);
    if (should.length > 0 && !should.some((condition) => this.matchesCondition(point, condition))) {
      return false;
    }

    const mustNot = toArray((filter as any).must_not);
    if (mustNot.some((condition) => this.matchesCondition(point, condition))) {
      return false;
    }

    return true;
  }

  private matchesCondition(point: PointRecord, condition: Record<string, unknown>): boolean {
    if ((condition as any).must || (condition as any).should || (condition as any).must_not) {
      return this.matchesFilter(point, condition);
    }

    const key = String((condition as any).key ?? "");
    const value = getPayloadValue(point.payload ?? {}, key);
    const match = (condition as any).match;

    if (match?.value !== undefined) {
      if (Array.isArray(value)) return value.includes(match.value);
      return value === match.value;
    }

    if (match?.any !== undefined) {
      const expected = Array.isArray(match.any) ? match.any : [];
      if (Array.isArray(value)) {
        return value.some((item) => expected.includes(item));
      }
      return expected.includes(value);
    }

    if (match?.text !== undefined) {
      return textMatch(value, String(match.text));
    }

    if (match?.phrase !== undefined) {
      return textMatch(value, String(match.phrase));
    }

    return false;
  }

  private requireCollection(collection: string): CollectionState {
    const existing = this.collections.get(collection);
    if (existing) return existing;

    const created: CollectionState = {
      points: [],
      vectors: undefined,
      payloadIndexes: [],
    };
    this.collections.set(collection, created);
    return created;
  }
}

const fakeClients: FakeQdrantClient[] = [];

mock.module("@qdrant/js-client-rest", () => ({
  QdrantClient: class extends FakeQdrantClient {
    constructor(config: Record<string, unknown>) {
      super(config);
      fakeClients.push(this);
    }
  },
}));

const { QdrantDatabase } = await import("./QdrantDatabase.js");

function toArray<T>(value: T | T[] | undefined): T[] {
  if (value === undefined) return [];
  return Array.isArray(value) ? value : [value];
}

function compareIds(a: PointId, b: PointId): number {
  const aNum = typeof a === "number" ? a : Number.NaN;
  const bNum = typeof b === "number" ? b : Number.NaN;
  if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) return aNum - bNum;
  return String(a).localeCompare(String(b));
}

function getPayloadValue(payload: Record<string, unknown>, key: string): unknown {
  const path = key.split(".");
  let cursor: unknown = payload;

  for (const segment of path) {
    if (cursor === null || cursor === undefined) return undefined;
    if (typeof cursor !== "object") return undefined;
    cursor = (cursor as Record<string, unknown>)[segment];
  }

  return cursor;
}

function textMatch(value: unknown, query: string): boolean {
  if (typeof value !== "string") return false;
  return value.toLowerCase().includes(query.toLowerCase());
}

function cosineSimilarity(a: number[], b: number[]): number {
  const len = Math.min(a.length, b.length);
  let dot = 0;
  let normA = 0;
  let normB = 0;

  for (let i = 0; i < len; i++) {
    dot += a[i]! * b[i]!;
    normA += a[i]! * a[i]!;
    normB += b[i]! * b[i]!;
  }

  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

function makeLayer(embeddingDimension = 3) {
  return QdrantDatabase.make({
    url: "http://localhost:6333",
    collection: "pdf-brain",
    embeddingDimension,
  });
}

async function collectGenerator<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const results: T[] = [];
  for await (const item of gen) {
    results.push(item);
  }
  return results;
}

describe("QdrantDatabase", () => {
  beforeEach(() => {
    fakeClients.length = 0;
  });

  test("auto-creates collections and payload indexes using configured embedding dimension", async () => {
    const program = Effect.gen(function* () {
      const db = yield* Database;
      return yield* db.getStats();
    });

    const stats = await Effect.runPromise(program.pipe(Effect.provide(makeLayer(384))));
    expect(stats).toEqual({ documents: 0, chunks: 0, embeddings: 0 });

    const client = fakeClients[0]!;
    const docs = client.collections.get("pdf-brain-documents");
    const chunks = client.collections.get("pdf-brain-chunks");

    expect(docs?.vectors).toEqual({ size: 1, distance: "Cosine" });
    expect(chunks?.vectors).toEqual({ size: 384, distance: "Cosine" });
    expect(chunks?.payloadIndexes.map((index) => index.field_name)).toEqual(
      expect.arrayContaining(["docId", "content", "tags"]),
    );
  });

  test("supports document CRUD and tag filtering", async () => {
    const doc = new Document({
      id: "doc-1",
      title: "Guide",
      path: "/tmp/guide.pdf",
      addedAt: new Date("2025-01-01T00:00:00Z"),
      pageCount: 9,
      sizeBytes: 1024,
      tags: ["alpha"],
      metadata: { source: "test" },
    });

    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const db = yield* Database;

        yield* db.addDocument(doc);
        const byId = yield* db.getDocument("doc-1");
        const byPath = yield* db.getDocumentByPath("/tmp/guide.pdf");

        yield* db.updateTags("doc-1", ["alpha", "beta"]);
        const tagged = yield* db.listDocuments("beta");

        yield* db.deleteDocument("doc-1");
        const deleted = yield* db.getDocument("doc-1");

        return { byId, byPath, tagged, deleted };
      }).pipe(Effect.provide(makeLayer())),
    );

    expect(result.byId?.title).toBe("Guide");
    expect(result.byPath?.id).toBe("doc-1");
    expect(result.tagged).toHaveLength(1);
    expect(result.tagged[0]?.tags).toEqual(["alpha", "beta"]);
    expect(result.deleted).toBeNull();
  });

  test("stores chunks and embeddings and returns vector + fts search results", async () => {
    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const db = yield* Database;

        yield* db.addDocument(
          new Document({
            id: "doc-search",
            title: "Search Doc",
            path: "/tmp/search.pdf",
            addedAt: new Date("2025-01-01T00:00:00Z"),
            pageCount: 1,
            sizeBytes: 100,
            tags: ["ml"],
          }),
        );

        yield* db.addChunks([
          {
            id: "chunk-1",
            docId: "doc-search",
            page: 1,
            chunkIndex: 0,
            content: "TypeScript vectors and embeddings",
          },
          {
            id: "chunk-2",
            docId: "doc-search",
            page: 1,
            chunkIndex: 1,
            content: "Notebook about gardening",
          },
        ]);

        yield* db.addEmbeddings([
          { chunkId: "chunk-1", embedding: [1, 0, 0] },
          { chunkId: "chunk-2", embedding: [0, 1, 0] },
        ]);

        const vectorResults = yield* db.vectorSearch([1, 0, 0], {
          limit: 5,
          tags: ["ml"],
          threshold: 0.5,
        });
        const ftsResults = yield* db.ftsSearch("TypeScript", { limit: 5 });

        return { vectorResults, ftsResults };
      }).pipe(Effect.provide(makeLayer())),
    );

    expect(result.vectorResults).toHaveLength(1);
    expect(result.vectorResults[0]?.chunkId).toBe("chunk-1");
    expect(result.vectorResults[0]?.matchType).toBe("vector");

    expect(result.ftsResults).toHaveLength(1);
    expect(result.ftsResults[0]?.chunkId).toBe("chunk-1");
    expect(result.ftsResults[0]?.matchType).toBe("fts");
  });

  test("replaceDocument replaces chunks and embeddings atomically", async () => {
    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const db = yield* Database;

        const doc = new Document({
          id: "doc-replace",
          title: "Before",
          path: "/tmp/replace.pdf",
          addedAt: new Date("2025-01-01T00:00:00Z"),
          pageCount: 1,
          sizeBytes: 100,
          tags: ["old"],
        });

        yield* db.addDocument(doc);
        yield* db.addChunks([
          {
            id: "chunk-old",
            docId: "doc-replace",
            page: 1,
            chunkIndex: 0,
            content: "Old content",
          },
        ]);
        yield* db.addEmbeddings([{ chunkId: "chunk-old", embedding: [1, 0, 0] }]);

        yield* db.replaceDocument(
          new Document({
            ...doc,
            title: "After",
            tags: ["new"],
          }),
          [
            {
              id: "chunk-new",
              docId: "doc-replace",
              page: 1,
              chunkIndex: 0,
              content: "New content",
            },
          ],
          [{ chunkId: "chunk-new", embedding: [0, 1, 0] }],
        );

        const chunks = yield* db.listChunksByDocument("doc-replace");
        const vector = yield* db.vectorSearch([0, 1, 0], { limit: 5 });

        return { chunks, vector };
      }).pipe(Effect.provide(makeLayer())),
    );

    expect(result.chunks).toHaveLength(1);
    expect(result.chunks[0]?.id).toBe("chunk-new");
    expect(result.vector[0]?.chunkId).toBe("chunk-new");
  });

  test("streams embeddings in batches and expands nearby chunk context", async () => {
    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const db = yield* Database;

        yield* db.addDocument(
          new Document({
            id: "doc-stream",
            title: "Stream",
            path: "/tmp/stream.pdf",
            addedAt: new Date("2025-01-01T00:00:00Z"),
            pageCount: 2,
            sizeBytes: 200,
            tags: [],
          }),
        );

        yield* db.addChunks([
          { id: "s-0", docId: "doc-stream", page: 1, chunkIndex: 0, content: "A" },
          { id: "s-1", docId: "doc-stream", page: 1, chunkIndex: 1, content: "B" },
          { id: "s-2", docId: "doc-stream", page: 1, chunkIndex: 2, content: "C" },
        ]);
        yield* db.addEmbeddings([
          { chunkId: "s-0", embedding: [1, 0, 0] },
          { chunkId: "s-1", embedding: [0, 1, 0] },
          { chunkId: "s-2", embedding: [0, 0, 1] },
        ]);

        const batches = yield* Effect.promise(() => collectGenerator(db.streamEmbeddings(2)));
        const expanded = yield* db.getExpandedContext("doc-stream", 1, 1, {
          maxChars: 100,
          direction: "both",
        });

        return { batches, expanded };
      }).pipe(Effect.provide(makeLayer())),
    );

    expect(result.batches).toHaveLength(2);
    expect(result.batches[0]).toHaveLength(2);
    expect(result.batches[1]).toHaveLength(1);

    expect(result.expanded.content).toContain("A");
    expect(result.expanded.content).toContain("B");
    expect(result.expanded.content).toContain("C");
    expect(result.expanded.startChunk).toBe("p1c0");
    expect(result.expanded.endChunk).toBe("p1c2");
  });

  test("repair removes orphaned chunks and embeddings", async () => {
    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const db = yield* Database;

        yield* db.addDocument(
          new Document({
            id: "doc-ok",
            title: "Kept",
            path: "/tmp/ok.pdf",
            addedAt: new Date("2025-01-01T00:00:00Z"),
            pageCount: 1,
            sizeBytes: 100,
            tags: [],
          }),
        );

        yield* db.addChunks([
          { id: "chunk-ok", docId: "doc-ok", page: 1, chunkIndex: 0, content: "ok" },
          { id: "chunk-orphan", docId: "missing-doc", page: 1, chunkIndex: 0, content: "orphan" },
        ]);
        yield* db.addEmbeddings([
          { chunkId: "chunk-ok", embedding: [1, 0, 0] },
          { chunkId: "chunk-orphan", embedding: [0, 1, 0] },
          { chunkId: "missing-chunk", embedding: [0, 0, 1] },
        ]);

        const repair = yield* db.repair();
        const orphanChunk = yield* db.getChunk("chunk-orphan");
        const streamed = yield* Effect.promise(() => collectGenerator(db.streamEmbeddings(10)));

        return {
          repair,
          orphanChunk,
          embeddingIds: streamed.flat().map((item) => item.chunkId),
        };
      }).pipe(Effect.provide(makeLayer())),
    );

    expect(result.repair).toEqual({
      orphanedChunks: 1,
      orphanedEmbeddings: 1,
      zeroVectorEmbeddings: 0,
    });
    expect(result.orphanChunk).toBeNull();
    expect(result.embeddingIds).toEqual(["chunk-ok"]);
  });

  test("countChunksByDocumentIds returns counts including zeros", async () => {
    const counts = await Effect.runPromise(
      Effect.gen(function* () {
        const db = yield* Database;

        yield* db.addDocument(
          new Document({
            id: "doc-a",
            title: "A",
            path: "/tmp/a.pdf",
            addedAt: new Date("2025-01-01T00:00:00Z"),
            pageCount: 1,
            sizeBytes: 100,
            tags: [],
          }),
        );
        yield* db.addDocument(
          new Document({
            id: "doc-b",
            title: "B",
            path: "/tmp/b.pdf",
            addedAt: new Date("2025-01-01T00:00:00Z"),
            pageCount: 1,
            sizeBytes: 100,
            tags: [],
          }),
        );

        yield* db.addChunks([
          { id: "a-1", docId: "doc-a", page: 1, chunkIndex: 0, content: "one" },
          { id: "a-2", docId: "doc-a", page: 1, chunkIndex: 1, content: "two" },
        ]);

        return yield* db.countChunksByDocumentIds(["doc-a", "doc-b", "doc-c"]);
      }).pipe(Effect.provide(makeLayer())),
    );

    expect(counts).toEqual({
      "doc-a": 2,
      "doc-b": 0,
      "doc-c": 0,
    });
  });
});
