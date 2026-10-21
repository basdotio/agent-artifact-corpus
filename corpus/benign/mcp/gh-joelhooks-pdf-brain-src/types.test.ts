/**
 * Tests for unified search result types
 */

import { describe, test, expect } from "bun:test";
import {
  EntityType,
  ConceptSearchResult,
  DocumentSearchResult,
  UnifiedSearchResult,
  SearchResult,
  SearchOptions,
} from "./types";

describe("Unified Search Types", () => {
  describe("EntityType", () => {
    test("should accept 'document' literal", () => {
      const entityType: EntityType = "document";
      expect(entityType).toBe("document");
    });

    test("should accept 'concept' literal", () => {
      const entityType: EntityType = "concept";
      expect(entityType).toBe("concept");
    });
  });

  describe("DocumentSearchResult", () => {
    test("should create valid document search result", () => {
      const result = new DocumentSearchResult({
        chunkId: "doc-123-0",
        docId: "doc-123",
        title: "Test Document",
        page: 1,
        chunkIndex: 0,
        content: "Test content",
        score: 0.95,
        rawScore: 0.95,
        scoreType: "cosine_similarity",
        vectorScore: 0.95,
        matchType: "vector",
        entityType: "document",
      });

      expect(result.entityType).toBe("document");
      expect(result.docId).toBe("doc-123");
      expect(result.score).toBe(0.95);
    });

    test("should support optional expanded content", () => {
      const result = new DocumentSearchResult({
        chunkId: "doc-123-0",
        docId: "doc-123",
        title: "Test Document",
        page: 1,
        chunkIndex: 0,
        content: "Test content",
        score: 0.95,
        rawScore: 0.95,
        scoreType: "cosine_similarity",
        vectorScore: 0.95,
        matchType: "vector",
        entityType: "document",
        expandedContent: "Expanded test content",
        expandedRange: { start: 0, end: 2 },
      });

      expect(result.expandedContent).toBe("Expanded test content");
      expect(result.expandedRange).toEqual({ start: 0, end: 2 });
    });
  });

  describe("ConceptSearchResult", () => {
    test("should create valid concept search result", () => {
      const result = new ConceptSearchResult({
        conceptId: "concept-456",
        prefLabel: "Machine Learning",
        definition: "A subset of artificial intelligence...",
        score: 0.88,
        rawScore: 0.88,
        scoreType: "cosine_similarity",
        entityType: "concept",
      });

      expect(result.entityType).toBe("concept");
      expect(result.conceptId).toBe("concept-456");
      expect(result.prefLabel).toBe("Machine Learning");
      expect(result.score).toBe(0.88);
    });
  });

  describe("UnifiedSearchResult", () => {
    test("should accept DocumentSearchResult", () => {
      const docResult: UnifiedSearchResult = new DocumentSearchResult({
        chunkId: "doc-123-0",
        docId: "doc-123",
        title: "Test Document",
        page: 1,
        chunkIndex: 0,
        content: "Test content",
        score: 0.95,
        rawScore: 0.95,
        scoreType: "cosine_similarity",
        vectorScore: 0.95,
        matchType: "vector",
        entityType: "document",
      });

      expect(docResult.entityType).toBe("document");
    });

    test("should accept ConceptSearchResult", () => {
      const conceptResult: UnifiedSearchResult = new ConceptSearchResult({
        conceptId: "concept-456",
        prefLabel: "Machine Learning",
        definition: "A subset of artificial intelligence...",
        score: 0.88,
        rawScore: 0.88,
        scoreType: "cosine_similarity",
        entityType: "concept",
      });

      expect(conceptResult.entityType).toBe("concept");
    });

    test("should discriminate by entityType", () => {
      const results: UnifiedSearchResult[] = [
        new DocumentSearchResult({
          chunkId: "doc-123-0",
          docId: "doc-123",
          title: "Test Document",
          page: 1,
          chunkIndex: 0,
          content: "Test content",
          score: 0.95,
          rawScore: 0.95,
          scoreType: "cosine_similarity",
          vectorScore: 0.95,
          matchType: "vector",
          entityType: "document",
        }),
        new ConceptSearchResult({
          conceptId: "concept-456",
          prefLabel: "Machine Learning",
          definition: "A subset of artificial intelligence...",
          score: 0.88,
          rawScore: 0.88,
          scoreType: "cosine_similarity",
          entityType: "concept",
        }),
      ];

      const docResults = results.filter(
        (r): r is DocumentSearchResult => r.entityType === "document"
      );
      const conceptResults = results.filter(
        (r): r is ConceptSearchResult => r.entityType === "concept"
      );

      expect(docResults).toHaveLength(1);
      expect(conceptResults).toHaveLength(1);
      expect(docResults[0].docId).toBe("doc-123");
      expect(conceptResults[0].conceptId).toBe("concept-456");
    });
  });

  describe("SearchOptions with entityTypes", () => {
    test("should accept entityTypes filter", () => {
      const options = new SearchOptions({
        limit: 10,
        entityTypes: ["document", "concept"],
      });

      expect(options.entityTypes).toEqual(["document", "concept"]);
    });

    test("should accept single entity type", () => {
      const options = new SearchOptions({
        limit: 10,
        entityTypes: ["document"],
      });

      expect(options.entityTypes).toEqual(["document"]);
    });

    test("should be optional (backwards compatibility)", () => {
      const options = new SearchOptions({
        limit: 10,
      });

      expect(options.entityTypes).toBeUndefined();
    });
  });

  describe("Backward compatibility", () => {
    test("SearchResult should still work as before", () => {
      const result = new SearchResult({
        docId: "doc-123",
        title: "Test Document",
        page: 1,
        chunkIndex: 0,
        content: "Test content",
        score: 0.95,
        matchType: "vector",
      });

      expect(result.docId).toBe("doc-123");
      expect(result.title).toBe("Test Document");
      expect(result.score).toBe(0.95);
    });

    test("SearchResult should NOT have entityType", () => {
      const result = new SearchResult({
        docId: "doc-123",
        title: "Test Document",
        page: 1,
        chunkIndex: 0,
        content: "Test content",
        score: 0.95,
        matchType: "vector",
      });

      // @ts-expect-error - entityType should not exist on SearchResult
      expect(result.entityType).toBeUndefined();
    });
  });
});
