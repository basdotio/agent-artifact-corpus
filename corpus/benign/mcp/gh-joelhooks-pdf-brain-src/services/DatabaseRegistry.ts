/**
 * Database Registry
 *
 * Selects and constructs the configured database backend.
 */

import {
  LibraryConfig,
  type Config,
  loadConfig,
  normalizeConfig,
} from "../types.js";
import { LibSQLDatabase } from "./LibSQLDatabase.js";
import { QdrantDatabase } from "./QdrantDatabase.js";

const MODEL_DIMENSIONS: Record<string, number> = {
  "mxbai-embed-large": 1024,
  "nomic-embed-text": 768,
  "all-minilm": 384,
  "all-minilm:33m": 384,
  "snowflake-arctic-embed": 1024,
  "bge-base-en": 768,
  "bge-large-en": 1024,
  "text-embedding-3-small": 1536,
  "text-embedding-3-large": 3072,
  "text-embedding-ada-002": 1536,
  "openai/text-embedding-3-small": 1536,
  "openai/text-embedding-3-large": 3072,
  "openai/text-embedding-ada-002": 1536,
};

function getModelDimension(model: string): number {
  if (MODEL_DIMENSIONS[model]) return MODEL_DIMENSIONS[model];
  for (const [key, dim] of Object.entries(MODEL_DIMENSIONS)) {
    if (model.startsWith(key)) return dim;
  }
  return 1024;
}

export class DatabaseRegistry {
  static make(opts?: { config?: Config; libraryConfig?: LibraryConfig }) {
    const config = normalizeConfig(opts?.config ?? loadConfig());
    const libraryConfig = opts?.libraryConfig ?? LibraryConfig.fromEnv();

    switch (config.database.backend) {
      case "qdrant":
        return QdrantDatabase.make({
          url: config.database.qdrant.url,
          collection: config.database.qdrant.collection,
          apiKey: config.database.qdrant.apiKey,
          embeddingDimension: getModelDimension(config.embedding.model),
        });
      case "libsql":
      default:
        return LibSQLDatabase.make({
          url: `file:${libraryConfig.dbPath}`,
          embeddingDimension: getModelDimension(config.embedding.model),
        });
    }
  }
}
