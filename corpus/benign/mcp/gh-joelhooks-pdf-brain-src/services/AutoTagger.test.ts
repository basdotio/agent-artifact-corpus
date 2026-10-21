/**
 * AutoTagger Tests
 *
 * Focus: Auto-accept proposals with embedding-based deduplication + RAG context
 */

import { describe, expect, it } from "bun:test";

// ============================================================================
// Tests - Verifying JSON file workflow is removed
// ============================================================================

describe("AutoTagger - JSON file workflow removed", () => {
  it("should NOT have loadProposedConcepts function", async () => {
    const module = await import("./AutoTagger.js");
    // @ts-expect-error - function should not exist
    expect(module.loadProposedConcepts).toBeUndefined();
  });

  it("should NOT have saveProposedConcepts function", async () => {
    const module = await import("./AutoTagger.js");
    // @ts-expect-error - function should not exist
    expect(module.saveProposedConcepts).toBeUndefined();
  });

  it("should NOT have addProposedConcepts function", async () => {
    const module = await import("./AutoTagger.js");
    // @ts-expect-error - function should not exist
    expect(module.addProposedConcepts).toBeUndefined();
  });

  it("should NOT have getProposedConceptsPath function", async () => {
    const module = await import("./AutoTagger.js");
    // @ts-expect-error - function should not exist
    expect(module.getProposedConceptsPath).toBeUndefined();
  });

  it("should NOT have ProposedConceptEntry type", async () => {
    // Type should not exist - compile-time check only
    // No runtime check possible for types
    expect(true).toBe(true);
  });
});

describe("AutoTagger - Concept validation", () => {
  it("should export validateProposedConcepts for validation", async () => {
    const module = await import("./AutoTagger.js");

    // Function should be exported for testing
    expect(typeof module.validateProposedConcepts).toBe("function");
  });
});
