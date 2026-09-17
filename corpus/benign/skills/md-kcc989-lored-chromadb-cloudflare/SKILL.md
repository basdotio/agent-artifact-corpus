---
name: chromadb-cloudflare
description: Use when building vector search, semantic search, or RAG applications with ChromaDB Cloud and Cloudflare Workers - covers TypeScript setup, Schema API for index configuration, embedding functions with Cloudflare Workers AI, hybrid search with RRF, and the Search API for filtering and ranking
---

# Schema API Reference

Configure indexes at collection creation for optimized performance and hybrid search.

## Imports

```typescript
import {
  Schema,
  VectorIndexConfig,
  SparseVectorIndexConfig,
  StringInvertedIndexConfig,
  IntInvertedIndexConfig,
  FloatInvertedIndexConfig,
  BoolInvertedIndexConfig,
  FTSIndexConfig,
  K,
} from "chromadb";
```

## Schema Structure

### Defaults vs Keys

- **Defaults**: Apply to ALL metadata fields of a type
- **Keys**: Override defaults for specific fields

Precedence: Key-specific > Default > Built-in default

## Creating Indexes

### Method Signature

```typescript
schema.createIndex(config: IndexConfig, key?: string): Schema
```

- `config`: Index configuration object
- `key`: Optional metadata field name (omit for global)

Returns `Schema` for method chaining.

### Vector Index

Configure dense vector embeddings:

```typescript
import { OpenAIEmbeddingFunction } from "chromadb";

const embeddingFunction = new OpenAIEmbeddingFunction({
  apiKey: "your-api-key",
  model: "text-embedding-3-small",
});

schema.createIndex(
  new VectorIndexConfig({
    space: "cosine", // 'cosine' | 'l2' | 'ip'
    embeddingFunction,
  }),
);
```

### Sparse Vector Index

Enable keyword-based search for hybrid retrieval:

```typescript
import { ChromaCloudSpladeEmbeddingFunction } from "@chroma-core/chroma-cloud-splade";

const sparseEf = new ChromaCloudSpladeEmbeddingFunction({
  apiKeyEnvVar: "CHROMA_API_KEY",
});

schema.createIndex(
  new SparseVectorIndexConfig({
    sourceKey: K.DOCUMENT, // Source field for embeddings
    embeddingFunction: sparseEf,
  }),
  "sparse_embedding", // Metadata key to store sparse vectors
);
```

**Only one sparse vector index per collection.**

### Inverted Indexes

Enable filtering on metadata types:

```typescript
// For specific keys
schema.createIndex(new StringInvertedIndexConfig(), "category");
schema.createIndex(new IntInvertedIndexConfig(), "year");
schema.createIndex(new FloatInvertedIndexConfig(), "score");
schema.createIndex(new BoolInvertedIndexConfig(), "published");
```

## Deleting Indexes

### Method Signature

```typescript
schema.deleteIndex(config?: IndexConfig, key?: string): Schema
```

### Examples

```typescript
// Disable string indexing globally
schema.deleteIndex(new StringInvertedIndexConfig());

// Disable int indexing for specific key
schema.deleteIndex(new IntInvertedIndexConfig(), "temp_count");

// Disable all indexes for a key
schema.deleteIndex(undefined, "unindexed_field");
```

**Cannot delete:** Vector Index, FTS Index

## Method Chaining

```typescript
const schema = new Schema()
  .deleteIndex(new StringInvertedIndexConfig()) // Disable strings globally
  .createIndex(new StringInvertedIndexConfig(), "category") // Enable for category
  .createIndex(new StringInvertedIndexConfig(), "tags") // Enable for tags
  .deleteIndex(new IntInvertedIndexConfig()); // Disable ints globally
```

## Default Index Behavior

Without Schema, collections use these defaults:

| Field Type               | Index Type     | Default |
| ------------------------ | -------------- | ------- |
| String metadata          | Inverted Index | Enabled |
| Int metadata             | Inverted Index | Enabled |
| Float metadata           | Inverted Index | Enabled |
| Bool metadata            | Inverted Index | Enabled |
| Document (`#document`)   | FTS            | Enabled |
| Embedding (`#embedding`) | Vector         | Enabled |

## Using Schema with Collections

```typescript
// Create with schema
const collection = await client.createCollection({
  name: "my_collection",
  schema,
});

// Get or create (schema only applied on creation)
const collection = await client.getOrCreateCollection({
  name: "my_collection",
  schema,
});

// Schema persists - no need to pass on getCollection
const collection = await client.getCollection({ name: "my_collection" });
```

## Complete Hybrid Search Setup

```typescript
import {
  CloudClient,
  Schema,
  VectorIndexConfig,
  SparseVectorIndexConfig,
  K,
  Search,
  Knn,
  Rrf,
} from "chromadb";
import { CloudflareWorkerAIEmbeddingFunction } from "@chroma-core/cloudflare-worker-ai";
import { ChromaBm25EmbeddingFunction } from "@chroma-core/chroma-bm25";

// 1. Initialize embedding functions
const denseEf = new CloudflareWorkerAIEmbeddingFunction({
  apiKey: env.CLOUDFLARE_API_TOKEN,
  accountId: env.CLOUDFLARE_ACCOUNT_ID,
  modelName: "@cf/google/embeddinggemma-300m",
});

const sparseEf = new ChromaBm25EmbeddingFunction({
  k: 1.2,
  b: 0.75,
  avgDocLength: 256.0,
  tokenMaxLength: 40,
});

// 2. Create schema with BOTH dense and sparse vector indexes
const schema = new Schema();

// Dense vector index for semantic search
schema.createIndex(
  new VectorIndexConfig({
    space: "cosine",
    embeddingFunction: denseEf,
  }),
);

// Sparse vector index for keyword matching
schema.createIndex(
  new SparseVectorIndexConfig({
    sourceKey: K.DOCUMENT,
    embeddingFunction: sparseEf,
  }),
  "sparse_embedding",
);

// 3. Create collection with schema (embedding functions already configured in schema)
const collection = await client.getOrCreateCollection({
  name: "hybrid_collection",
  schema,
});

// 4. Add documents (both embeddings auto-generated)
await collection.add({
  ids: ["doc1", "doc2"],
  documents: ["First document text", "Second document text"],
  metadatas: [{ category: "tech" }, { category: "science" }],
});

// 5. Hybrid search with RRF
const search = new Search()
  .rank(
    Rrf({
      ranks: [
        Knn({ query: "search query", returnRank: true, limit: 200 }),
        Knn({
          query: "search query",
          key: "sparse_embedding",
          returnRank: true,
          limit: 200,
        }),
      ],
      weights: [0.7, 0.3],
    }),
  )
  .limit(20)
  .select(K.DOCUMENT, K.SCORE);

const results = await collection.search(search);
```

## Sparse Embedding Functions

| Function                             | Package                            |
| ------------------------------------ | ---------------------------------- |
| `ChromaBm25EmbeddingFunction`        | `@chroma-core/chroma-bm25`         |
| `ChromaCloudSpladeEmbeddingFunction` | `@chroma-core/chroma-cloud-splade` |
| `HuggingFaceSparseEmbeddingFunction` | chromadb                           |
| `FastembedSparseEmbeddingFunction`   | chromadb                           |

### BM25 Configuration

```typescript
import { ChromaBm25EmbeddingFunction } from "@chroma-core/chroma-bm25";

const bm25Ef = new ChromaBm25EmbeddingFunction({
  k: 1.2, // Term frequency saturation
  b: 0.75, // Length normalization
  avgDocLength: 256.0,
  tokenMaxLength: 40,
});
```

## Sparse Vector Format

```typescript
interface SparseVector {
  indices: number[]; // Non-zero positions
  values: number[]; // Corresponding weights
}

// Example
const sparse = {
  indices: [1, 5, 10, 50],
  values: [0.5, 0.3, 0.8, 0.2],
};
```

## Limitations

- Schema only configurable at `createCollection` time
- Only one sparse vector index per collection
- Dense embeddings only in `#embedding` field (not custom metadata keys)
- Vector and FTS indexes cannot be deleted
