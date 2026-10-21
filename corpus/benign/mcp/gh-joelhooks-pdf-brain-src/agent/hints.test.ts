import { describe, expect, test } from "bun:test";
import { generateHints, type CommandResult } from "./hints.js";
import { formatHintBlock, stripEmoji } from "./format.js";

describe("generateHints", () => {
  test("search with results suggests read + expand", () => {
    const result: CommandResult = {
      _tag: "search",
      query: "error handling",
      results: [
        { title: "Release It!", docId: "doc-1", score: 0.85 },
        { title: "DDIA", docId: "doc-2", score: 0.72 },
      ],
      concepts: [],
      hadExpand: false,
      wasFts: false,
    };
    const hints = generateHints(result);
    expect(hints.length).toBeGreaterThan(0);
    expect(hints.some((h) => h.includes("read"))).toBe(true);
    expect(hints.some((h) => h.includes("--expand"))).toBe(true);
  });

  test("search with expand already used does not suggest --expand again", () => {
    const result: CommandResult = {
      _tag: "search",
      query: "error handling",
      results: [{ title: "Release It!", docId: "doc-1", score: 0.85 }],
      concepts: [],
      hadExpand: true,
      wasFts: false,
    };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("--expand"))).toBe(false);
  });

  test("search with no results suggests broader query + fts", () => {
    const result: CommandResult = {
      _tag: "search",
      query: "nonexistent topic",
      results: [],
      concepts: [],
      hadExpand: false,
      wasFts: false,
    };
    const hints = generateHints(result);
    expect(hints.length).toBeGreaterThan(0);
    expect(hints.some((h) => h.includes("--fts"))).toBe(true);
    expect(hints.some((h) => h.includes("list"))).toBe(true);
  });

  test("search with concepts suggests taxonomy navigation", () => {
    const result: CommandResult = {
      _tag: "search",
      query: "design patterns",
      results: [{ title: "GoF", docId: "doc-1", score: 0.9 }],
      concepts: [{ id: "software/design-patterns", prefLabel: "Design Patterns" }],
      hadExpand: false,
      wasFts: false,
    };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("taxonomy tree"))).toBe(true);
  });

  test("noResults with FTS suggests vector search", () => {
    const result: CommandResult = {
      _tag: "noResults",
      query: "missing thing",
      wasFts: true,
    };
    const hints = generateHints(result);
    expect(hints.some((h) => !h.includes("--fts"))).toBe(true);
    expect(hints.some((h) => h.includes("list"))).toBe(true);
  });

  test("read suggests search + tag + taxonomy", () => {
    const result: CommandResult = {
      _tag: "read",
      title: "Release It!",
      id: "doc-123",
      tags: ["programming", "resilience"],
    };
    const hints = generateHints(result);
    expect(hints.length).toBeGreaterThan(0);
    expect(hints.some((h) => h.includes("search"))).toBe(true);
    expect(hints.some((h) => h.includes("--tag"))).toBe(true);
    expect(hints.some((h) => h.includes("taxonomy"))).toBe(true);
  });

  test("list suggests read + search", () => {
    const result: CommandResult = {
      _tag: "list",
      count: 42,
      firstDoc: { title: "DDIA", id: "doc-1" },
    };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("read"))).toBe(true);
    expect(hints.some((h) => h.includes("search"))).toBe(true);
  });

  test("stats suggests search + list + taxonomy + doctor", () => {
    const result: CommandResult = {
      _tag: "stats",
      documents: 100,
      chunks: 5000,
      embeddings: 5000,
    };
    const hints = generateHints(result);
    expect(hints.length).toBe(4);
    expect(hints.some((h) => h.includes("search"))).toBe(true);
    expect(hints.some((h) => h.includes("doctor"))).toBe(true);
  });

  test("taxonomySearch with matches suggests tree + search", () => {
    const result: CommandResult = {
      _tag: "taxonomySearch",
      query: "error",
      matches: [{ id: "programming/error-handling", prefLabel: "Error Handling" }],
    };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("taxonomy tree"))).toBe(true);
    expect(hints.some((h) => h.includes("search"))).toBe(true);
  });

  test("taxonomySearch with no matches suggests list + search", () => {
    const result: CommandResult = {
      _tag: "taxonomySearch",
      query: "nonexistent",
      matches: [],
    };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("taxonomy list"))).toBe(true);
  });

  test("taxonomyList suggests tree + search", () => {
    const result: CommandResult = { _tag: "taxonomyList", count: 50 };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("--tree"))).toBe(true);
    expect(hints.some((h) => h.includes("taxonomy search"))).toBe(true);
  });

  test("taxonomyTree with rootId suggests full tree", () => {
    const result: CommandResult = { _tag: "taxonomyTree", rootId: "software" };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("taxonomy tree`"))).toBe(true);
  });

  test("add suggests read + search + tag", () => {
    const result: CommandResult = { _tag: "add", title: "New Book", id: "doc-new" };
    const hints = generateHints(result);
    expect(hints.length).toBe(3);
    expect(hints.some((h) => h.includes("read"))).toBe(true);
    expect(hints.some((h) => h.includes("search"))).toBe(true);
    expect(hints.some((h) => h.includes("tag"))).toBe(true);
  });

  test("remove suggests list + stats", () => {
    const result: CommandResult = { _tag: "remove", title: "Old Book" };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("list"))).toBe(true);
    expect(hints.some((h) => h.includes("stats"))).toBe(true);
  });

  test("doctor unhealthy suggests --fix", () => {
    const result: CommandResult = { _tag: "doctor", healthy: false };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("--fix"))).toBe(true);
  });

  test("doctor healthy does not suggest --fix", () => {
    const result: CommandResult = { _tag: "doctor", healthy: true };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("--fix"))).toBe(false);
  });

  test("error suggests doctor + check + help", () => {
    const result: CommandResult = {
      _tag: "error",
      command: "search",
      message: "Connection failed",
    };
    const hints = generateHints(result);
    expect(hints.some((h) => h.includes("doctor"))).toBe(true);
    expect(hints.some((h) => h.includes("check"))).toBe(true);
    expect(hints.some((h) => h.includes("--help"))).toBe(true);
  });

  test("every variant produces non-empty hints array", () => {
    const variants: CommandResult[] = [
      { _tag: "search", query: "q", results: [{ title: "T", docId: "d", score: 0.5 }], concepts: [], hadExpand: false, wasFts: false },
      { _tag: "noResults", query: "q", wasFts: false },
      { _tag: "read", title: "T", id: "d", tags: ["t"] },
      { _tag: "list", count: 1, firstDoc: { title: "T", id: "d" } },
      { _tag: "stats", documents: 1, chunks: 1, embeddings: 1 },
      { _tag: "taxonomySearch", query: "q", matches: [{ id: "c", prefLabel: "C" }] },
      { _tag: "taxonomyList", count: 1 },
      { _tag: "taxonomyTree" },
      { _tag: "add", title: "T", id: "d" },
      { _tag: "remove", title: "T" },
      { _tag: "tag", title: "T", tags: ["t"] },
      { _tag: "doctor", healthy: true },
      { _tag: "config", subcommand: "show" },
      { _tag: "check", reachable: true },
      { _tag: "repair", orphanedChunks: 0, orphanedEmbeddings: 0 },
      { _tag: "reindex", count: 1, errors: 0 },
      { _tag: "error", command: "search", message: "fail" },
    ];

    for (const variant of variants) {
      const hints = generateHints(variant);
      expect(hints.length).toBeGreaterThan(0);
    }
  });
});

describe("formatHintBlock", () => {
  test("produces valid markdown blockquote", () => {
    const block = formatHintBlock([
      "`pdf-brain search \"test\"` -- Search",
      "`pdf-brain list` -- Browse",
    ], { documents: 42 });

    expect(block).toContain("---");
    expect(block).toContain("> **Next Actions**");
    expect(block).toContain("> -");
    expect(block).toContain("42 documents");
    expect(block).toContain("`pdf-brain --help`");
  });

  test("includes concept count when provided", () => {
    const block = formatHintBlock(["`cmd` -- desc"], {
      documents: 10,
      concepts: 50,
    });
    expect(block).toContain("50 concepts");
  });

  test("returns empty string for no hints", () => {
    expect(formatHintBlock([])).toBe("");
  });

  test("works without stats", () => {
    const block = formatHintBlock(["`cmd` -- desc"]);
    expect(block).toContain("> **Next Actions**");
    expect(block).toContain("`pdf-brain --help`");
    expect(block).not.toContain("documents");
  });
});

describe("stripEmoji", () => {
  test("removes emoji characters", () => {
    expect(stripEmoji("📚 Concepts")).toBe("Concepts");
    expect(stripEmoji("🏷️ Label")).toBe("Label");
    expect(stripEmoji("📄 Documents (5):")).toBe("Documents (5):");
  });

  test("preserves plain text", () => {
    expect(stripEmoji("Hello world")).toBe("Hello world");
    expect(stripEmoji("pdf-brain search")).toBe("pdf-brain search");
  });

  test("handles empty string", () => {
    expect(stripEmoji("")).toBe("");
  });
});
