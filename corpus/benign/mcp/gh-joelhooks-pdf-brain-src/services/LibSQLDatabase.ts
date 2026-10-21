/**
 * LibSQL Database Service
 *
 * Implements the Database interface using @libsql/client.
 * Designed for file-based and remote libSQL/Turso databases.
 */

import { Effect, Layer } from "effect";
import { createClient, type Client } from "@libsql/client";
import { Database } from "./Database.js";
import { DatabaseError, Document, PDFChunk } from "../types.js";

// Default embedding dimension (mxbai-embed-large)
// Can be overridden via config for other models:
// - nomic-embed-text: 768
// - all-minilm: 384
const DEFAULT_EMBEDDING_DIM = 1024;

// ============================================================================
// LibSQLDatabase Service
// ============================================================================

export class LibSQLDatabase {
  /**
   * Create a LibSQL Database layer
   *
   * @param config - Connection configuration
   *   - url: ":memory:" for in-memory, "file:./path.db" for local file, or remote URL
   *   - authToken: Optional auth token for Turso/remote databases
   *   - embeddingDimension: Vector dimension for embeddings (default: 1024 for mxbai-embed-large)
   *     Use 768 for nomic-embed-text, 384 for all-minilm, etc.
   */
  static make(config: {
    url: string;
    authToken?: string;
    embeddingDimension?: number;
  }) {
    const embeddingDim = config.embeddingDimension ?? DEFAULT_EMBEDDING_DIM;

    return Layer.scoped(
      Database,
      Effect.gen(function* () {
        // Create libSQL client
        const client = createClient({
          url: config.url,
          authToken: config.authToken,
        });

        // Initialize schema with configured embedding dimension
        yield* Effect.tryPromise({
          try: async () => {
            await initSchema(client, embeddingDim);
          },
          catch: (e) =>
            new DatabaseError({ reason: `Schema init failed: ${e}` }),
        });

        // Cleanup on scope close
        yield* Effect.addFinalizer(() =>
          Effect.sync(() => {
            client.close();
          }),
        );

        // Helper to parse document row
        const inferFileType = (path: string): "pdf" | "markdown" => {
          const lower = path.toLowerCase();
          if (lower.endsWith(".md") || lower.endsWith(".markdown")) return "markdown";
          return "pdf";
        };

        const parseDocRow = (row: any): Document =>
          new Document({
            id: row.id as string,
            title: row.title as string,
            path: row.path as string,
            addedAt: new Date(row.added_at as string),
            pageCount: row.page_count as number,
            sizeBytes: row.size_bytes as number,
            tags: JSON.parse(row.tags as string) as string[],
            fileType:
              row.file_type === "markdown" || row.file_type === "pdf"
                ? (row.file_type as "pdf" | "markdown")
                : inferFileType(row.path as string),
            metadata: JSON.parse(row.metadata as string) as Record<
              string,
              unknown
            >,
          });

        const parseChunkRow = (row: any): PDFChunk =>
          new PDFChunk({
            id: row.id as string,
            docId: row.doc_id as string,
            page: Number(row.page),
            chunkIndex: Number(row.chunk_index),
            content: row.content as string,
          });

        // Return Database implementation
        return {
          addDocument: (doc) =>
            Effect.tryPromise({
              try: async () => {
                await client.execute({
                  sql: `INSERT INTO documents (id, title, path, added_at, page_count, size_bytes, tags, metadata, file_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                          title = excluded.title,
                          path = excluded.path,
                          added_at = excluded.added_at,
                          page_count = excluded.page_count,
                          size_bytes = excluded.size_bytes,
                          tags = excluded.tags,
                          metadata = excluded.metadata,
                          file_type = excluded.file_type`,
                  args: [
                    doc.id,
                    doc.title,
                    doc.path,
                    doc.addedAt.toISOString(),
                    doc.pageCount,
                    doc.sizeBytes,
                    JSON.stringify(doc.tags),
                    JSON.stringify(doc.metadata || {}),
                    // Prefer explicit doc.fileType, but trust the path extension if they diverge.
                    doc.fileType === inferFileType(doc.path)
                      ? doc.fileType
                      : inferFileType(doc.path),
                  ],
                });
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          getDocument: (id) =>
            Effect.tryPromise({
              try: async () => {
                const result = await client.execute({
                  sql: "SELECT * FROM documents WHERE id = ?",
                  args: [id],
                });
                return result.rows.length > 0
                  ? parseDocRow(result.rows[0])
                  : null;
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          getDocumentByPath: (path) =>
            Effect.tryPromise({
              try: async () => {
                const result = await client.execute({
                  sql: "SELECT * FROM documents WHERE path = ?",
                  args: [path],
                });
                return result.rows.length > 0
                  ? parseDocRow(result.rows[0])
                  : null;
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          listDocuments: (tag) =>
            Effect.tryPromise({
              try: async () => {
                let sql = "SELECT * FROM documents";
                const args: any[] = [];

                if (tag) {
                  sql +=
                    " WHERE json_array_length(tags) > 0 AND EXISTS (SELECT 1 FROM json_each(tags) WHERE value = ?)";
                  args.push(tag);
                }

                sql += " ORDER BY added_at DESC";

                const result = await client.execute({ sql, args });
                return result.rows.map(parseDocRow);
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          deleteDocument: (id) =>
            Effect.tryPromise({
              try: async () => {
                await client.execute({
                  sql: "DELETE FROM documents WHERE id = ?",
                  args: [id],
                });
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),
          updateTags: (id, tags) =>
            Effect.tryPromise({
              try: async () => {
                await client.execute({
                  sql: "UPDATE documents SET tags = ? WHERE id = ?",
                  args: [JSON.stringify(tags), id],
                });
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          addChunks: (chunks) =>
            Effect.tryPromise({
              try: async () => {
                // Use batch for transaction
                const statements = chunks.map((chunk) => ({
                  sql: "INSERT INTO chunks (id, doc_id, page, chunk_index, content) VALUES (?, ?, ?, ?, ?)",
                  args: [
                    chunk.id,
                    chunk.docId,
                    chunk.page,
                    chunk.chunkIndex,
                    chunk.content,
                  ],
                }));
                await client.batch(statements, "write");
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          getChunk: (chunkId) =>
            Effect.tryPromise({
              try: async () => {
                const result = await client.execute({
                  sql: "SELECT id, doc_id, page, chunk_index, content FROM chunks WHERE id = ?",
                  args: [chunkId],
                });
                const row = result.rows[0];
                return row ? parseChunkRow(row) : null;
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          listChunksByDocument: (docId, opts) =>
            Effect.tryPromise({
              try: async () => {
                const page = opts?.page;
                const args: any[] = [docId];
                let sql =
                  "SELECT id, doc_id, page, chunk_index, content FROM chunks WHERE doc_id = ?";
                if (typeof page === "number") {
                  sql += " AND page = ?";
                  args.push(page);
                }
                sql += " ORDER BY page ASC, chunk_index ASC";

                const result = await client.execute({ sql, args });
                return result.rows.map(parseChunkRow);
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          addEmbeddings: (embeddings) =>
            Effect.tryPromise({
              try: async () => {
                // LibSQL stores vectors as F32_BLOB using vector32() function
                const statements = embeddings.map((item) => ({
                  sql: `INSERT INTO embeddings (chunk_id, embedding)
                        VALUES (?, vector32(?))
                        ON CONFLICT (chunk_id) DO UPDATE SET
                          embedding = excluded.embedding`,
                  args: [item.chunkId, JSON.stringify(item.embedding)],
                }));
                await client.batch(statements, "write");
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          replaceDocument: (doc, chunks, embeddings) =>
            Effect.tryPromise({
              try: async () => {
                const statements: Array<{ sql: string; args: any[] }> = [];

                // 1. Upsert document row
                statements.push({
                  sql: `INSERT INTO documents (id, title, path, added_at, page_count, size_bytes, tags, metadata, file_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                          title = excluded.title,
                          path = excluded.path,
                          added_at = excluded.added_at,
                          page_count = excluded.page_count,
                          size_bytes = excluded.size_bytes,
                          tags = excluded.tags,
                          metadata = excluded.metadata,
                          file_type = excluded.file_type`,
                  args: [
                    doc.id,
                    doc.title,
                    doc.path,
                    doc.addedAt.toISOString(),
                    doc.pageCount,
                    doc.sizeBytes,
                    JSON.stringify(doc.tags),
                    JSON.stringify(doc.metadata || {}),
                    doc.fileType === inferFileType(doc.path)
                      ? doc.fileType
                      : inferFileType(doc.path),
                  ],
                });

                // 2. Delete old chunks (cascades to embeddings + chunk_clusters)
                statements.push({
                  sql: "DELETE FROM chunks WHERE doc_id = ?",
                  args: [doc.id],
                });

                // 3. Insert new chunks
                for (const chunk of chunks) {
                  statements.push({
                    sql: "INSERT INTO chunks (id, doc_id, page, chunk_index, content) VALUES (?, ?, ?, ?, ?)",
                    args: [
                      chunk.id,
                      chunk.docId,
                      chunk.page,
                      chunk.chunkIndex,
                      chunk.content,
                    ],
                  });
                }

                // 4. Insert new embeddings
                for (const item of embeddings) {
                  statements.push({
                    sql: `INSERT INTO embeddings (chunk_id, embedding)
                          VALUES (?, vector32(?))
                          ON CONFLICT (chunk_id) DO UPDATE SET
                            embedding = excluded.embedding`,
                    args: [item.chunkId, JSON.stringify(item.embedding)],
                  });
                }

                // Single transaction: either the whole rebuild lands or nothing changes.
                await client.batch(statements, "write");
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          vectorSearch: (queryEmbedding, options) =>
            Effect.tryPromise({
              try: async () => {
                const {
                  limit = 10,
                  tags,
                  threshold = 0.0,
                  includeClusterSummaries = false,
                } = options || {};
                const queryVec = JSON.stringify(queryEmbedding);

                // RAPTOR multi-scale retrieval: query both chunks AND cluster summaries
                if (includeClusterSummaries) {
                  const fetchLimit =
                    tags && tags.length > 0 ? limit * 2 : limit;
                  const maxDistance =
                    threshold > 0 ? 2 * (1 - threshold) : null;

                  // Query chunks
                  const chunkArgs: any[] = [queryVec, queryVec, fetchLimit];
                  const chunkConditions: string[] = [];

                  if (tags && tags.length > 0) {
                    chunkConditions.push(
                      "(" +
                        tags
                          .map(
                            () =>
                              "EXISTS (SELECT 1 FROM json_each(d.tags) WHERE value = ?)",
                          )
                          .join(" OR ") +
                        ")",
                    );
                    chunkArgs.push(...tags);
                  }

                  if (maxDistance !== null) {
                    chunkConditions.push(
                      `vector_distance_cos(e.embedding, vector32(?)) <= ?`,
                    );
                    chunkArgs.push(queryVec, maxDistance);
                  }

                  const chunkResults = await client.execute({
                    sql: `
                      SELECT 
                        c.id as chunk_id,
                        c.doc_id,
                        d.title,
                        c.page,
                        c.chunk_index,
                        c.content,
                        vector_distance_cos(e.embedding, vector32(?)) as distance
                      FROM vector_top_k('embeddings_idx', vector32(?), ?) AS top
                      JOIN embeddings e ON e.rowid = top.id
                      JOIN chunks c ON c.id = e.chunk_id
                      JOIN documents d ON d.id = c.doc_id
                      ${
                        chunkConditions.length > 0
                          ? " WHERE " + chunkConditions.join(" AND ")
                          : ""
                      }
                    `,
                    args: chunkArgs,
                  });

                  // Query cluster summaries
                  const clusterArgs: any[] = [queryVec, queryVec, fetchLimit];
                  const clusterConditions: string[] = [];

                  if (maxDistance !== null) {
                    clusterConditions.push(
                      `vector_distance_cos(cs.embedding, vector32(?)) <= ?`,
                    );
                    clusterArgs.push(queryVec, maxDistance);
                  }

                  const clusterResults = await client.execute({
                    sql: `
                      SELECT 
                        ('cluster-summary-' || cs.id) as chunk_id,
                        '' as doc_id,
                        'Cluster Summary' as title,
                        0 as page,
                        cs.id as chunk_index,
                        cs.summary as content,
                        vector_distance_cos(cs.embedding, vector32(?)) as distance
                      FROM vector_top_k('cluster_summaries_idx', vector32(?), ?) AS top
                      JOIN cluster_summaries cs ON cs.rowid = top.id
                      ${
                        clusterConditions.length > 0
                          ? " WHERE " + clusterConditions.join(" AND ")
                          : ""
                      }
                    `,
                    args: clusterArgs,
                  });

                  // Merge and sort by score
                  return [...chunkResults.rows, ...clusterResults.rows]
                    .map((row: any) => ({
                      chunkId: row.chunk_id,
                      docId: row.doc_id,
                      title: row.title,
                      page: Number(row.page),
                      chunkIndex: Number(row.chunk_index),
                      content: row.content,
                      // Convert distance to similarity score: score = 1 - distance/2
                      score: 1 - Number(row.distance) / 2,
                      rawScore: 1 - Number(row.distance) / 2,
                      scoreType: "cosine_similarity" as const,
                      vectorScore: 1 - Number(row.distance) / 2,
                      matchType: "vector" as const,
                    }))
                    .sort((a, b) => b.score - a.score)
                    .slice(0, limit);
                }

                // Standard chunk-only search
                let sql = `
                  SELECT 
                    c.id as chunk_id,
                    c.doc_id,
                    d.title,
                    c.page,
                    c.chunk_index,
                    c.content,
                    vector_distance_cos(e.embedding, vector32(?)) as distance
                  FROM vector_top_k('embeddings_idx', vector32(?), ?) AS top
                  JOIN embeddings e ON e.rowid = top.id
                  JOIN chunks c ON c.id = e.chunk_id
                  JOIN documents d ON d.id = c.doc_id
                `;

                // Fetch more than limit to allow for filtering
                const fetchLimit = tags && tags.length > 0 ? limit * 3 : limit;
                const args: any[] = [queryVec, queryVec, fetchLimit];

                const conditions: string[] = [];

                if (tags && tags.length > 0) {
                  conditions.push(
                    "(" +
                      tags
                        .map(
                          () =>
                            "EXISTS (SELECT 1 FROM json_each(d.tags) WHERE value = ?)",
                        )
                        .join(" OR ") +
                      ")",
                  );
                  args.push(...tags);
                }

                // Filter by threshold (distance < 2*(1-threshold))
                // score = 1 - distance/2, so distance = 2*(1-score)
                // if score >= threshold, then distance <= 2*(1-threshold)
                if (threshold > 0) {
                  const maxDistance = 2 * (1 - threshold);
                  conditions.push(
                    `vector_distance_cos(e.embedding, vector32(?)) <= ?`,
                  );
                  args.push(queryVec, maxDistance);
                }

                if (conditions.length > 0) {
                  sql += " WHERE " + conditions.join(" AND ");
                }

                sql += ` ORDER BY distance ASC LIMIT ${limit}`;

                const result = await client.execute({ sql, args });

                return result.rows.map(
                  (row: any) =>
                    ({
                      chunkId: row.chunk_id,
                      docId: row.doc_id,
                      title: row.title,
                      page: Number(row.page),
                      chunkIndex: Number(row.chunk_index),
                      content: row.content,
                      // Convert distance to similarity score: score = 1 - distance/2
                      score: 1 - Number(row.distance) / 2,
                      rawScore: 1 - Number(row.distance) / 2,
                      scoreType: "cosine_similarity",
                      vectorScore: 1 - Number(row.distance) / 2,
                      matchType: "vector",
                    }) as any,
                );
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          ftsSearch: (query, options) =>
            Effect.tryPromise({
              try: async () => {
                const { limit = 10, tags } = options || {};

                // LibSQL FTS5 uses MATCH syntax
                // FTS5 rank() returns NEGATIVE scores - more negative = better match
                //
                // IMPORTANT: FTS5 has special query syntax where characters like
                // - (NOT), * (prefix), " (phrase), : (column), etc. have meaning.
                // We need to escape the query to treat it as a literal phrase search.
                // Wrap the entire query in double quotes for phrase matching,
                // and escape any internal double quotes.
                const escapedQuery = `"${query.replace(/"/g, '""')}"`;

                let sql = `
                  SELECT 
                    c.id as chunk_id,
                    c.doc_id,
                    d.title,
                    c.page,
                    c.chunk_index,
                    c.content,
                    fts.rank as rank
                  FROM chunks_fts fts
                  JOIN chunks c ON c.rowid = fts.rowid
                  JOIN documents d ON d.id = c.doc_id
                  WHERE fts.content MATCH ?
                `;

                const args: any[] = [escapedQuery];

                if (tags && tags.length > 0) {
                  // Filter by tags using json_each
                  sql +=
                    " AND EXISTS (SELECT 1 FROM json_each(d.tags) WHERE value IN (" +
                    tags.map(() => "?").join(", ") +
                    "))";
                  args.push(...tags);
                }

                // Order by rank ASC (more negative = better match)
                sql += ` ORDER BY fts.rank ASC LIMIT ?`;
                args.push(limit);

                const result = await client.execute({ sql, args });

                const normalizeRank = (rank: number): number => {
                  const abs = Math.abs(rank);
                  // Map 0..inf to 0..1 (higher = better).
                  return abs / (1 + abs);
                };

                return result.rows.map(
                  (row: any) =>
                    ({
                      chunkId: row.chunk_id,
                      docId: row.doc_id,
                      title: row.title,
                      page: Number(row.page),
                      chunkIndex: Number(row.chunk_index),
                      content: row.content,
                      // Keep raw rank for debugging; normalize for cross-engine ranking.
                      score: normalizeRank(Number(row.rank)),
                      rawScore: Number(row.rank),
                      scoreType: "fts_rank",
                      ftsRank: Number(row.rank),
                      matchType: "fts",
                    }) as any,
                );
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          getExpandedContext: (docId, page, chunkIndex, options) =>
            Effect.tryPromise({
              try: async () => {
                const { maxChars = 2000, direction = "both" } = options || {};

                // Get target chunk uniquely by (doc_id, page, chunk_index)
                const targetResult = await client.execute({
                  sql: "SELECT id, page, chunk_index, content FROM chunks WHERE doc_id = ? AND page = ? AND chunk_index = ?",
                  args: [docId, page, chunkIndex],
                });

                if (targetResult.rows.length === 0) {
                  return {
                    content: "",
                    startChunk: `p${page}c${chunkIndex}`,
                    endChunk: `p${page}c${chunkIndex}`,
                  };
                }

                const target = targetResult.rows[0] as any;
                let totalContent: string = target.content;
                let startPage = page;
                let startChunkIdx = chunkIndex;
                let endPage = page;
                let endChunkIdx = chunkIndex;

                // Expand before: get preceding chunks in document order
                if (direction === "before" || direction === "both") {
                  const beforeResult = await client.execute({
                    sql: `SELECT page, chunk_index, content FROM chunks
                          WHERE doc_id = ? AND (page < ? OR (page = ? AND chunk_index < ?))
                          ORDER BY page DESC, chunk_index DESC LIMIT 20`,
                    args: [docId, page, page, chunkIndex],
                  });

                  for (const row of beforeResult.rows) {
                    const content = (row as any).content as string;
                    if (totalContent.length + content.length > maxChars * 1.2) break;
                    totalContent = content + "\n" + totalContent;
                    startPage = Number((row as any).page);
                    startChunkIdx = Number((row as any).chunk_index);
                  }
                }

                // Expand after: get following chunks in document order
                if (direction === "after" || direction === "both") {
                  const afterResult = await client.execute({
                    sql: `SELECT page, chunk_index, content FROM chunks
                          WHERE doc_id = ? AND (page > ? OR (page = ? AND chunk_index > ?))
                          ORDER BY page ASC, chunk_index ASC LIMIT 20`,
                    args: [docId, page, page, chunkIndex],
                  });

                  for (const row of afterResult.rows) {
                    const content = (row as any).content as string;
                    if (totalContent.length + content.length > maxChars * 1.2) break;
                    totalContent = totalContent + "\n" + content;
                    endPage = Number((row as any).page);
                    endChunkIdx = Number((row as any).chunk_index);
                  }
                }

                return {
                  content: totalContent,
                  startChunk: `p${startPage}c${startChunkIdx}`,
                  endChunk: `p${endPage}c${endChunkIdx}`,
                };
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          getStats: () =>
            Effect.tryPromise({
              try: async () => {
                // Prefer counting a stable column rather than COUNT(*) because
                // libSQL's vector extension can report COUNT(*) incorrectly on
                // some vector-backed tables.
                const docs = await client.execute(
                  "SELECT COUNT(id) as count FROM documents",
                );
                const chunks = await client.execute(
                  "SELECT COUNT(id) as count FROM chunks",
                );
                const embeddings = await client.execute(
                  "SELECT COUNT(chunk_id) as count FROM embeddings",
                );

                return {
                  documents: Number((docs.rows[0] as any).count),
                  chunks: Number((chunks.rows[0] as any).count),
                  embeddings: Number((embeddings.rows[0] as any).count),
                };
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          countChunksByDocumentIds: (docIds) =>
            Effect.tryPromise({
              try: async () => {
                const counts: Record<string, number> = {};
                if (!docIds || docIds.length === 0) return counts;

                // SQLite has a relatively low max variable limit; chunk requests defensively.
                const chunkSize = 500;
                for (let i = 0; i < docIds.length; i += chunkSize) {
                  const slice = docIds.slice(i, i + chunkSize);
                  const placeholders = slice.map(() => "?").join(", ");
                  const sql = `
                    SELECT doc_id as doc_id, COUNT(id) as count
                    FROM chunks
                    WHERE doc_id IN (${placeholders})
                    GROUP BY doc_id
                  `;
                  const result = await client.execute({ sql, args: slice });
                  for (const row of result.rows as any[]) {
                    const docId = String(row.doc_id);
                    counts[docId] = Number(row.count);
                  }
                }

                // Ensure requested IDs exist in the result, even when count = 0.
                for (const id of docIds) {
                  if (!(id in counts)) counts[id] = 0;
                }

                return counts;
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          repair: () =>
            Effect.tryPromise({
              try: async () => {
                // Count orphaned chunks
                const orphanedChunksResult = await client.execute(`
                  SELECT COUNT(*) as count FROM chunks c
                  WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = c.doc_id)
                `);
                const orphanedChunks = Number(
                  (orphanedChunksResult.rows[0] as any).count,
                );

                // Count orphaned embeddings
                const orphanedEmbeddingsResult = await client.execute(`
                  SELECT COUNT(chunk_id) as count FROM embeddings e
                  WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.id = e.chunk_id)
                `);
                const orphanedEmbeddings = Number(
                  (orphanedEmbeddingsResult.rows[0] as any).count,
                );

                // Delete orphaned embeddings first
                if (orphanedEmbeddings > 0) {
                  await client.execute(`
                    DELETE FROM embeddings e
                    WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.id = e.chunk_id)
                  `);
                }

                // Delete orphaned chunks
                if (orphanedChunks > 0) {
                  await client.execute(`
                    DELETE FROM chunks c
                    WHERE NOT EXISTS (SELECT 1 FROM documents d WHERE d.id = c.doc_id)
                  `);
                }

                return {
                  orphanedChunks,
                  orphanedEmbeddings,
                  zeroVectorEmbeddings: 0, // LibSQL doesn't expose vector validation
                };
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),

          checkpoint: () =>
            Effect.tryPromise({
              try: async () => {
                // LibSQL file DBs auto-sync via WAL, no explicit checkpoint needed
                // client.sync() is only for Turso remote replication
                // Just run a PRAGMA to ensure WAL is flushed
                await client.execute("PRAGMA wal_checkpoint(TRUNCATE)");
              },
              catch: (e) =>
                new DatabaseError({ reason: `Checkpoint failed: ${e}` }),
            }),

          dumpDataDir: () =>
            Effect.fail(
              new DatabaseError({
                reason: "dumpDataDir not supported for LibSQL",
              }),
            ),

          streamEmbeddings: async function* (batchSize: number) {
            // Stream embeddings in batches to avoid loading all into memory
            // Useful for clustering large embedding sets
            let offset = 0;

            while (true) {
              const result = await client.execute({
                sql: `SELECT chunk_id, embedding FROM embeddings LIMIT ? OFFSET ?`,
                args: [batchSize, offset],
              });

              if (result.rows.length === 0) break;

              // Convert rows to expected format
              const batch = result.rows.map((row: any) => ({
                chunkId: row.chunk_id as string,
                embedding: Array.from(row.embedding as Float32Array),
              }));

              yield batch;

              if (result.rows.length < batchSize) break;
              offset += batchSize;
            }
          },

          bulkInsertClusterAssignments: (assignments) =>
            Effect.tryPromise({
              try: async () => {
                if (assignments.length === 0) return;

                // Use batch for atomic transaction
                const statements = assignments.map((a) => ({
                  sql: "INSERT INTO chunk_clusters (chunk_id, cluster_id, distance) VALUES (?, ?, ?)",
                  args: [a.chunkId, a.clusterId, a.distance],
                }));

                await client.batch(statements, "write");
              },
              catch: (e) => new DatabaseError({ reason: String(e) }),
            }),
        };
      }),
    );
  }
}

// ============================================================================
// Schema Initialization
// ============================================================================

async function initSchema(client: Client, embeddingDim: number): Promise<void> {
  // Set busy timeout to wait up to 30s for locks instead of failing immediately
  await client.execute("PRAGMA busy_timeout = 30000");

  // Ensure WAL mode for better concurrent access
  await client.execute("PRAGMA journal_mode = WAL");

  // Documents table
  await client.execute(`
    CREATE TABLE IF NOT EXISTS documents (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      path TEXT NOT NULL UNIQUE,
      added_at TEXT NOT NULL,
      page_count INTEGER NOT NULL,
      size_bytes INTEGER NOT NULL,
      tags TEXT DEFAULT '[]',
      file_type TEXT NOT NULL DEFAULT 'pdf',
      metadata TEXT DEFAULT '{}'
    )
  `);

  // Migration: older DBs didn't store file type (markdown vs pdf).
  // Add `file_type` column and backfill from the document path extension.
  try {
    const info = await client.execute("PRAGMA table_info(documents)");
    const hasFileType = info.rows.some(
      (r: any) => (r as any).name === "file_type",
    );
    if (!hasFileType) {
      await client.execute(
        "ALTER TABLE documents ADD COLUMN file_type TEXT NOT NULL DEFAULT 'pdf'",
      );
      await client.execute(`
        UPDATE documents
        SET file_type = CASE
          WHEN lower(path) LIKE '%.md' OR lower(path) LIKE '%.markdown' THEN 'markdown'
          ELSE 'pdf'
        END
      `);
    }
  } catch {
    // Best-effort migration; schema will still work without file_type but some
    // document metadata (markdown vs pdf) may be inaccurate.
  }

  // Chunks table
  await client.execute(`
    CREATE TABLE IF NOT EXISTS chunks (
      id TEXT PRIMARY KEY,
      doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      page INTEGER NOT NULL,
      chunk_index INTEGER NOT NULL,
      content TEXT NOT NULL
    )
  `);

  // Embeddings table with F32_BLOB for vectors
  await client.execute(`
    CREATE TABLE IF NOT EXISTS embeddings (
      chunk_id TEXT PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
      embedding F32_BLOB(${embeddingDim}) NOT NULL
    )
  `);

  // Create indexes
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(doc_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_docs_path ON documents(path)`,
  );

  // Vector index for fast ANN search (DiskANN algorithm)
  // compress_neighbors=float8 reduces index size ~4x with minimal recall loss (~1-2%)
  await client.execute(
    `CREATE INDEX IF NOT EXISTS embeddings_idx ON embeddings(libsql_vector_idx(embedding, 'compress_neighbors=float8'))`,
  );

  // FTS5 virtual table for full-text search
  await client.execute(`
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts 
    USING fts5(content, content='chunks', content_rowid='rowid')
  `);

  // ============================================================================
  // SKOS Taxonomy Schema (W3C Knowledge Organization)
  // ============================================================================
  //
  // HIERARCHY TRAVERSAL PATTERNS (LibSQL has no graph extensions)
  // Use recursive CTEs for transitive queries:
  //
  // Get all ancestors (transitive broader):
  //   WITH RECURSIVE ancestors AS (
  //     SELECT broader_id FROM concept_hierarchy WHERE concept_id = ?
  //     UNION
  //     SELECT ch.broader_id FROM concept_hierarchy ch
  //     JOIN ancestors a ON ch.concept_id = a.broader_id
  //   )
  //   SELECT * FROM concepts WHERE id IN (SELECT broader_id FROM ancestors);
  //
  // Get all descendants (transitive narrower):
  //   WITH RECURSIVE descendants AS (
  //     SELECT concept_id FROM concept_hierarchy WHERE broader_id = ?
  //     UNION
  //     SELECT ch.concept_id FROM concept_hierarchy ch
  //     JOIN descendants d ON ch.broader_id = d.concept_id
  //   )
  //   SELECT * FROM concepts WHERE id IN (SELECT concept_id FROM descendants);

  // Concepts table - stores controlled vocabulary terms
  await client.execute(`
    CREATE TABLE IF NOT EXISTS concepts (
      id TEXT PRIMARY KEY,
      pref_label TEXT NOT NULL,
      alt_labels TEXT DEFAULT '[]',
      definition TEXT,
      created_at TEXT NOT NULL
    )
  `);

  // Concept Hierarchy - polyhierarchy support (multiple parents)
  // Uses broader/narrower semantics from SKOS
  await client.execute(`
    CREATE TABLE IF NOT EXISTS concept_hierarchy (
      concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
      broader_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
      PRIMARY KEY(concept_id, broader_id)
    )
  `);

  // Concept Relations - associative relationships (SKOS 'related')
  await client.execute(`
    CREATE TABLE IF NOT EXISTS concept_relations (
      concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
      related_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
      relation_type TEXT DEFAULT 'related',
      PRIMARY KEY(concept_id, related_id)
    )
  `);

  // Document-Concept mappings - link documents to concepts
  await client.execute(`
    CREATE TABLE IF NOT EXISTS document_concepts (
      doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
      concept_id TEXT NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
      confidence REAL DEFAULT 1.0,
      source TEXT DEFAULT 'llm',
      PRIMARY KEY(doc_id, concept_id)
    )
  `);

  // Concept Embeddings - vector representations of concepts (unified with document embeddings)
  await client.execute(`
    CREATE TABLE IF NOT EXISTS concept_embeddings (
      concept_id TEXT PRIMARY KEY REFERENCES concepts(id) ON DELETE CASCADE,
      embedding F32_BLOB(${embeddingDim}) NOT NULL
    )
  `);

  // Taxonomy indexes for efficient hierarchy traversal
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_concept_hierarchy_concept ON concept_hierarchy(concept_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_concept_hierarchy_broader ON concept_hierarchy(broader_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_concept_relations_concept ON concept_relations(concept_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_concept_relations_related ON concept_relations(related_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_document_concepts_doc ON document_concepts(doc_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_document_concepts_concept ON document_concepts(concept_id)`,
  );

  // Vector index for concept embeddings (same compression as document embeddings)
  await client.execute(
    `CREATE INDEX IF NOT EXISTS concept_embeddings_idx ON concept_embeddings(libsql_vector_idx(embedding, 'compress_neighbors=float8'))`,
  );

  // ============================================================================
  // RAPTOR Clustering Schema (Hard Clustering with K-means)
  // ============================================================================
  //
  // RAPTOR-style multi-scale retrieval where queries can match:
  // 1. Individual chunks (leaf nodes)
  // 2. Cluster summaries (intermediate nodes)
  //
  // Uses hard clustering (k-means) where each chunk belongs to exactly one cluster
  // with a distance metric to the centroid.

  // Chunk-Cluster assignments (hard membership with distance to centroid)
  await client.execute(`
    CREATE TABLE IF NOT EXISTS chunk_clusters (
      chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
      cluster_id INTEGER NOT NULL,
      distance REAL NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      PRIMARY KEY(chunk_id, cluster_id)
    )
  `);

  // Cluster summaries with embedded metadata
  // Combines cluster metadata, summary, and concept mapping in a single table
  await client.execute(`
    CREATE TABLE IF NOT EXISTS cluster_summaries (
      id INTEGER PRIMARY KEY,
      centroid F32_BLOB(${embeddingDim}),
      summary TEXT,
      embedding F32_BLOB(${embeddingDim}),
      concept_id TEXT,
      concept_confidence REAL,
      chunk_count INTEGER NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `);

  // Indexes for efficient cluster queries
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_chunk_clusters_cluster ON chunk_clusters(cluster_id)`,
  );
  await client.execute(
    `CREATE INDEX IF NOT EXISTS idx_cluster_summaries_concept ON cluster_summaries(concept_id)`,
  );

  // Vector index for cluster summary embeddings (for multi-scale retrieval)
  await client.execute(
    `CREATE INDEX IF NOT EXISTS cluster_summaries_idx ON cluster_summaries(libsql_vector_idx(embedding, 'compress_neighbors=float8'))`,
  );

  // Triggers to keep FTS5 in sync with chunks table
  await client.execute(`
    CREATE TRIGGER IF NOT EXISTS chunks_ai 
    AFTER INSERT ON chunks 
    BEGIN 
      INSERT INTO chunks_fts(rowid, content) 
      VALUES (new.rowid, new.content); 
    END
  `);

  await client.execute(`
    CREATE TRIGGER IF NOT EXISTS chunks_ad 
    AFTER DELETE ON chunks 
    BEGIN 
      INSERT INTO chunks_fts(chunks_fts, rowid, content) 
      VALUES('delete', old.rowid, old.content); 
    END
  `);

  await client.execute(`
    CREATE TRIGGER IF NOT EXISTS chunks_au 
    AFTER UPDATE ON chunks 
    BEGIN 
      INSERT INTO chunks_fts(chunks_fts, rowid, content) 
      VALUES('delete', old.rowid, old.content);
      INSERT INTO chunks_fts(rowid, content) 
      VALUES (new.rowid, new.content);
    END
  `);
}
