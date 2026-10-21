/**
 * HATEOAS-style hint engine for pdf-brain CLI.
 *
 * Pure function: CommandResult discriminated union in, string[] hints out.
 */

import type { NextAction } from "./protocol.js";

export type CommandResult =
  | {
      _tag: "search";
      query: string;
      results: { title: string; docId: string; chunkId?: string; score: number }[];
      concepts: { id: string; prefLabel: string }[];
      hadExpand: boolean;
      wasFts: boolean;
    }
  | {
      _tag: "searchPack";
      queries: string[];
      results: { title: string; docId: string; chunkId?: string; score: number }[];
    }
  | { _tag: "read"; title: string; id: string; tags: string[] }
  | {
      _tag: "list";
      count: number;
      tag?: string;
      firstDoc?: { title: string; id: string };
    }
  | {
      _tag: "stats";
      documents: number;
      chunks: number;
      embeddings: number;
    }
  | {
      _tag: "taxonomySearch";
      query: string;
      matches: { id: string; prefLabel: string }[];
    }
  | { _tag: "taxonomyList"; count: number }
  | { _tag: "taxonomyTree"; rootId?: string }
  | { _tag: "add"; title: string; id: string }
  | { _tag: "remove"; title: string }
  | { _tag: "noResults"; query: string; wasFts: boolean }
  | { _tag: "error"; command: string; message: string }
  | {
      _tag: "doctor";
      healthy: boolean;
      chunkerOutdated?: number;
      chunkerMissing?: number;
      chunkerMismatch?: number;
    }
  | { _tag: "config"; subcommand: string }
  | { _tag: "tag"; title: string; tags: string[] }
  | { _tag: "check"; reachable: boolean }
  | { _tag: "repair"; orphanedChunks: number; orphanedEmbeddings: number }
  | { _tag: "reindex"; count: number; errors: number }
  | {
      _tag: "rechunk";
      dryRun: boolean;
      planned: number;
      succeeded: number;
      failed: number;
      includeMissing?: boolean;
      skippedMissing?: number;
      plannedMissing?: number;
      plannedMismatch?: number;
    };

/**
 * Generate contextual next-action hints from a command result.
 * Returns an array of copy-pasteable command strings with descriptions.
 */
export function generateHints(result: CommandResult): string[] {
  switch (result._tag) {
    case "search": {
      const hints: string[] = [];
      if (result.results.length > 0) {
        const top = result.results[0];
        hints.push(
          `\`pdf-brain read "${top.title}"\` -- Full metadata for top result`
        );
        if (!result.hadExpand) {
          hints.push(
            `\`pdf-brain search "${result.query}" --expand 2000\` -- Get expanded context around matches`
          );
        }
      }
      if (result.concepts.length > 0) {
        const topConcept = result.concepts[0];
        hints.push(
          `\`pdf-brain taxonomy tree "${topConcept.id}"\` -- Navigate concept hierarchy`
        );
      }
      if (result.results.length > 0 && !result.wasFts) {
        hints.push(
          `\`pdf-brain search "${result.query}" --fts\` -- Try keyword matching instead`
        );
      }
      if (result.results.length === 0 && result.concepts.length === 0) {
        return generateHints({
          _tag: "noResults",
          query: result.query,
          wasFts: result.wasFts,
        });
      }
      return hints;
    }

    case "searchPack": {
      const hints: string[] = [];
      if (result.results.length > 0) {
        const top = result.results[0];
        hints.push(
          `\`pdf-brain read "${top.title}"\` -- Full metadata for top result`
        );
        if (top.chunkId) {
          hints.push(
            `\`pdf-brain chunk get "${top.chunkId}"\` -- Fetch exact top chunk text`
          );
        }
      }
      hints.push(
        `\`pdf-brain search "<query>"\` -- Drill into a single query`,
        `\`pdf-brain search-pack --with-content "${result.queries[0] ?? "query"}"\` -- Include chunk text in pack output`,
      );
      return hints;
    }

    case "noResults": {
      const hints: string[] = [];
      if (!result.wasFts) {
        hints.push(
          `\`pdf-brain search "${result.query}" --fts\` -- Try full-text keyword search`
        );
      } else {
        hints.push(
          `\`pdf-brain search "${result.query}"\` -- Try semantic vector search`
        );
      }
      hints.push(
        `\`pdf-brain list\` -- Browse all documents`,
        `\`pdf-brain taxonomy search "${result.query}"\` -- Search taxonomy concepts`
      );
      return hints;
    }

    case "read": {
      const hints: string[] = [];
      hints.push(
        `\`pdf-brain search "${result.title}" --expand 2000\` -- Search within this document's content`
      );
      if (result.tags.length > 0) {
        hints.push(
          `\`pdf-brain list --tag "${result.tags[0]}"\` -- Browse documents with same tag`
        );
      }
      hints.push(
        `\`pdf-brain taxonomy search "${result.title}"\` -- Find related concepts`
      );
      return hints;
    }

    case "list": {
      const hints: string[] = [];
      if (result.firstDoc) {
        hints.push(
          `\`pdf-brain read "${result.firstDoc.title}"\` -- View document details`
        );
      }
      hints.push(
        `\`pdf-brain search "<query>"\` -- Search across all documents`
      );
      if (!result.tag) {
        hints.push(
          `\`pdf-brain taxonomy list\` -- Browse concept categories`
        );
      }
      return hints;
    }

    case "stats": {
      const hints: string[] = [];
      hints.push(
        `\`pdf-brain search "<query>"\` -- Search across ${result.documents} documents`,
        `\`pdf-brain list\` -- Browse all documents`,
        `\`pdf-brain taxonomy list\` -- Browse concept taxonomy`,
        `\`pdf-brain doctor\` -- Run health check`
      );
      return hints;
    }

    case "taxonomySearch": {
      const hints: string[] = [];
      if (result.matches.length > 0) {
        const top = result.matches[0];
        hints.push(
          `\`pdf-brain taxonomy tree "${top.id}"\` -- Navigate hierarchy from "${top.prefLabel}"`
        );
        hints.push(
          `\`pdf-brain search "${top.prefLabel}"\` -- Find documents tagged with this concept`
        );
      } else {
        hints.push(
          `\`pdf-brain taxonomy list\` -- Browse all concepts`,
          `\`pdf-brain search "${result.query}"\` -- Search documents instead`
        );
      }
      return hints;
    }

    case "taxonomyList": {
      const hints: string[] = [];
      hints.push(
        `\`pdf-brain taxonomy list --tree\` -- Show hierarchy tree view`,
        `\`pdf-brain taxonomy search "<query>"\` -- Find specific concepts`,
        `\`pdf-brain search "<query>"\` -- Search documents by content`
      );
      return hints;
    }

    case "taxonomyTree": {
      const hints: string[] = [];
      hints.push(
        `\`pdf-brain taxonomy search "<query>"\` -- Find concepts by keyword`,
        `\`pdf-brain search "<query>"\` -- Search documents by content`
      );
      if (result.rootId) {
        hints.push(
          `\`pdf-brain taxonomy tree\` -- View full concept tree`
        );
      }
      return hints;
    }

    case "add": {
      return [
        `\`pdf-brain read "${result.title}"\` -- View document details`,
        `\`pdf-brain search "${result.title}" --expand 2000\` -- Search within this document`,
        `\`pdf-brain tag "${result.id}" "topic1,topic2"\` -- Add tags`,
      ];
    }

    case "remove": {
      return [
        `\`pdf-brain list\` -- Browse remaining documents`,
        `\`pdf-brain stats\` -- Check library statistics`,
      ];
    }

    case "tag": {
      return [
        `\`pdf-brain read "${result.title}"\` -- View updated document`,
        `\`pdf-brain list --tag "${result.tags[0]}"\` -- Browse documents with this tag`,
      ];
    }

    case "doctor": {
      const hints: string[] = [];
      if (!result.healthy) {
        hints.push(
          `\`pdf-brain doctor --fix\` -- Auto-repair detected issues`
        );
      }
      const missing = result.chunkerMissing ?? 0;
      const mismatch = result.chunkerMismatch ?? 0;

      if (mismatch > 0) {
        hints.push(
          `\`pdf-brain rechunk --dry-run\` -- Preview docs with stale chunker metadata`,
          `\`pdf-brain rechunk\` -- Apply rechunk (rebuild chunks + embeddings)`,
        );
      }

      if (missing > 0) {
        hints.push(
          `\`pdf-brain rechunk --dry-run --include-missing\` -- Preview docs missing chunker metadata (upgrade sweep)`,
          `\`pdf-brain rechunk --include-missing --max-docs 25\` -- Rechunk a small batch (expensive)`,
        );
      }
      hints.push(
        `\`pdf-brain stats\` -- Check library statistics`,
        `\`pdf-brain search "<query>"\` -- Search documents`
      );
      return hints;
    }

    case "config": {
      return [
        `\`pdf-brain config show\` -- View all settings`,
        `\`pdf-brain config set embedding.model <model>\` -- Change embedding model`,
        `\`pdf-brain stats\` -- Check library statistics`,
      ];
    }

    case "check": {
      const hints: string[] = [];
      if (result.reachable) {
        hints.push(
          `\`pdf-brain search "<query>"\` -- Search documents`,
          `\`pdf-brain stats\` -- Check library statistics`
        );
      } else {
        hints.push(
          `\`pdf-brain doctor\` -- Run full health check`,
          `\`pdf-brain config show\` -- Check configuration`
        );
      }
      return hints;
    }

    case "repair": {
      return [
        `\`pdf-brain doctor\` -- Run full health check`,
        `\`pdf-brain stats\` -- Check library statistics`,
      ];
    }

    case "rechunk": {
      const hints: string[] = [];
      if (result.dryRun) {
        if (result.includeMissing) {
          hints.push(
            `\`pdf-brain rechunk --include-missing --max-docs 25\` -- Rechunk a small batch (rebuild chunks + embeddings)`,
          );
        } else {
          hints.push(
            `\`pdf-brain rechunk\` -- Apply rechunk (rebuild chunks + embeddings)`,
          );
          if ((result.skippedMissing ?? 0) > 0) {
            hints.push(
              `\`pdf-brain rechunk --dry-run --include-missing\` -- Include missing-metadata docs in the plan`,
            );
          }
        }
      } else {
        hints.push(
          `\`pdf-brain stats\` -- Verify counts after rechunk`,
          `\`pdf-brain search "<query>"\` -- Sanity-check retrieval quality`,
        );
      }
      return hints;
    }

    case "reindex": {
      return [
        `\`pdf-brain stats\` -- Check updated statistics`,
        `\`pdf-brain search "<query>"\` -- Test search with new embeddings`,
      ];
    }

    case "error": {
      return [
        `\`pdf-brain doctor\` -- Run health check`,
        `\`pdf-brain check\` -- Verify embedding provider`,
        `\`pdf-brain --help\` -- View all commands`,
      ];
    }

    default: {
      const _exhaustive: never = result;
      return [];
    }
  }
}

/**
 * Structured follow-up actions for agent workflows.
 * These are equivalent to `generateHints`, but machine-friendly.
 */
export function generateNextActions(result: CommandResult): NextAction[] {
  switch (result._tag) {
    case "search": {
      const actions: NextAction[] = [];
      if (result.results.length > 0) {
        const top = result.results[0];
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "read", top.docId],
          description: "Full metadata for top result",
        });

        if (top.chunkId) {
          actions.push({
            kind: "shell",
            argv: ["pdf-brain", "chunk", "get", top.chunkId],
            description: "Fetch exact top chunk text",
          });
        }

        if (!result.hadExpand) {
          actions.push({
            kind: "shell",
            argv: ["pdf-brain", "search", result.query, "--expand", "2000"],
            description: "Get expanded context around matches",
          });
        }
      }

      if (result.concepts.length > 0) {
        const topConcept = result.concepts[0];
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "taxonomy", "tree", topConcept.id],
          description: "Navigate concept hierarchy",
        });
      }

      if (result.results.length > 0 && !result.wasFts) {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "search", result.query, "--fts"],
          description: "Try keyword matching instead",
        });
      }

      if (result.results.length === 0 && result.concepts.length === 0) {
        return generateNextActions({
          _tag: "noResults",
          query: result.query,
          wasFts: result.wasFts,
        });
      }

      return actions;
    }

    case "searchPack": {
      const actions: NextAction[] = [];
      if (result.results.length > 0) {
        const top = result.results[0];
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "read", top.docId],
          description: "Read top document metadata",
        });
        if (top.chunkId) {
          actions.push({
            kind: "shell",
            argv: ["pdf-brain", "chunk", "get", top.chunkId],
            description: "Fetch exact top chunk text",
          });
        }
      }
      actions.push({
        kind: "shell",
        argv: ["pdf-brain", "search", "your query here"],
        description: "Drill into a single query",
      });
      return actions;
    }

    case "noResults": {
      const actions: NextAction[] = [];
      if (!result.wasFts) {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "search", result.query, "--fts"],
          description: "Try full-text keyword search",
        });
      } else {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "search", result.query],
          description: "Try semantic vector search",
        });
      }
      actions.push(
        { kind: "shell", argv: ["pdf-brain", "list"], description: "Browse all documents" },
        {
          kind: "shell",
          argv: ["pdf-brain", "taxonomy", "search", result.query],
          description: "Search taxonomy concepts",
        },
      );
      return actions;
    }

    case "read": {
      const actions: NextAction[] = [];
      actions.push({
        kind: "shell",
        argv: ["pdf-brain", "search", result.title, "--expand", "2000"],
        description: "Search within this document's content",
      });
      if (result.tags.length > 0) {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "list", "--tag", result.tags[0]],
          description: "Browse documents with same tag",
        });
      }
      actions.push({
        kind: "shell",
        argv: ["pdf-brain", "taxonomy", "search", result.title],
        description: "Find related concepts",
      });
      return actions;
    }

    case "list": {
      const actions: NextAction[] = [];
      if (result.firstDoc) {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "read", result.firstDoc.id],
          description: "Read the first listed document",
        });
      }
      actions.push({
        kind: "shell",
        argv: ["pdf-brain", "search", "your query here"],
        description: "Search the library",
      });
      return actions;
    }

    case "stats": {
      return [
        { kind: "shell", argv: ["pdf-brain", "search", "your question here"], description: "Search the library" },
        { kind: "shell", argv: ["pdf-brain", "list"], description: "Browse all documents" },
        { kind: "shell", argv: ["pdf-brain", "taxonomy", "list"], description: "Browse taxonomy concepts" },
        { kind: "shell", argv: ["pdf-brain", "doctor"], description: "Check database health" },
      ];
    }

    case "taxonomySearch": {
      const actions: NextAction[] = [];
      if (result.matches.length > 0) {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "taxonomy", "tree", result.matches[0].id],
          description: "Navigate concept hierarchy",
        });
      } else {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "taxonomy", "list"],
          description: "Browse all concepts",
        });
      }
      actions.push({
        kind: "shell",
        argv: ["pdf-brain", "search", result.query],
        description: "Search documents for this concept",
      });
      return actions;
    }

    case "taxonomyList": {
      return [
        { kind: "shell", argv: ["pdf-brain", "taxonomy", "tree"], description: "View full concept tree" },
        { kind: "shell", argv: ["pdf-brain", "taxonomy", "search", "your query"], description: "Search concepts" },
      ];
    }

    case "taxonomyTree": {
      return [
        { kind: "shell", argv: ["pdf-brain", "taxonomy", "tree"], description: "View full concept tree" },
      ];
    }

    case "add": {
      return [
        { kind: "shell", argv: ["pdf-brain", "read", result.id], description: "Read the new document" },
        { kind: "shell", argv: ["pdf-brain", "search", result.title], description: "Search for related content" },
        { kind: "shell", argv: ["pdf-brain", "tag", result.id, "tag1,tag2"], description: "Apply tags" },
      ];
    }

    case "remove": {
      return [
        { kind: "shell", argv: ["pdf-brain", "list"], description: "Browse remaining documents" },
        { kind: "shell", argv: ["pdf-brain", "stats"], description: "Verify counts" },
      ];
    }

    case "tag": {
      const actions: NextAction[] = [
        { kind: "shell", argv: ["pdf-brain", "read", result.title], description: "Read document metadata" },
        { kind: "shell", argv: ["pdf-brain", "list", "--tag", result.tags[0] ?? ""], description: "Browse by tag" },
      ];
      return actions.filter((a) => a.argv[a.argv.length - 1] !== "");
    }

    case "doctor": {
      const actions: NextAction[] = [];
      if (!result.healthy) {
        actions.push({
          kind: "shell",
          argv: ["pdf-brain", "doctor", "--fix"],
          description: "Attempt auto-repair",
        });
      }
      const missing = result.chunkerMissing ?? 0;
      const mismatch = result.chunkerMismatch ?? 0;

      if (mismatch > 0) {
        actions.push(
          {
            kind: "shell",
            argv: ["pdf-brain", "rechunk", "--dry-run"],
            description: "Preview docs with stale chunker metadata",
          },
          {
            kind: "shell",
            argv: ["pdf-brain", "rechunk"],
            description: "Apply rechunk (rebuild chunks + embeddings)",
          },
        );
      }

      if (missing > 0) {
        actions.push(
          {
            kind: "shell",
            argv: ["pdf-brain", "rechunk", "--dry-run", "--include-missing"],
            description: "Preview docs missing chunker metadata (upgrade sweep)",
          },
          {
            kind: "shell",
            argv: ["pdf-brain", "rechunk", "--include-missing", "--max-docs", "25"],
            description: "Rechunk a small batch (expensive)",
          },
        );
      }
      actions.push({
        kind: "shell",
        argv: ["pdf-brain", "stats"],
        description: "Verify counts",
      });
      return actions;
    }

    case "config": {
      return [
        { kind: "shell", argv: ["pdf-brain", "config", "show"], description: "Show config" },
      ];
    }

    case "check": {
      return [
        { kind: "shell", argv: ["pdf-brain", "stats"], description: "Check library stats" },
      ];
    }

    case "repair": {
      return [
        { kind: "shell", argv: ["pdf-brain", "doctor"], description: "Re-run health check" },
      ];
    }

    case "reindex": {
      return [
        { kind: "shell", argv: ["pdf-brain", "stats"], description: "Verify counts" },
      ];
    }

    case "rechunk": {
      if (result.dryRun) {
        if (result.includeMissing) {
          return [
            {
              kind: "shell",
              argv: ["pdf-brain", "rechunk", "--include-missing", "--max-docs", "25"],
              description: "Rechunk a small batch (rebuild chunks + embeddings)",
            },
          ];
        }

        const actions: NextAction[] = [
          {
            kind: "shell",
            argv: ["pdf-brain", "rechunk"],
            description: "Apply rechunk (rebuild chunks + embeddings)",
          },
        ];

        if ((result.skippedMissing ?? 0) > 0) {
          actions.push({
            kind: "shell",
            argv: ["pdf-brain", "rechunk", "--dry-run", "--include-missing"],
            description: "Include missing-metadata docs in the plan",
          });
        }

        return actions;
      }
      return [
        { kind: "shell", argv: ["pdf-brain", "stats"], description: "Verify counts" },
      ];
    }

    case "error": {
      return [
        { kind: "shell", argv: ["pdf-brain", "doctor"], description: "Check database health" },
        { kind: "shell", argv: ["pdf-brain", "check"], description: "Check embedding provider connectivity" },
        { kind: "shell", argv: ["pdf-brain", "--help"], description: "Show available commands" },
      ];
    }
  }
}
