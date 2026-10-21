// MCP tools for semantic code search (thin wrappers; logic lives in src/semantic).
import { loadConfig } from "../config.js";
import { refreshReport, semanticSearchReport, similarCodeReport } from "../semantic/search.js";

export async function semantic_search(args: { query: string; path_glob?: string; language?: string; kind?: string; top_k?: number }): Promise<string> {
  return semanticSearchReport(loadConfig(), args.query, args.path_glob ?? "", args.language ?? "", args.kind ?? "", args.top_k ?? 10);
}

export async function find_similar_code(args: { file_path: string; start_line: number; end_line?: number; top_k?: number }): Promise<string> {
  return similarCodeReport(loadConfig(), args.file_path, args.start_line, args.end_line ?? 0, args.top_k ?? 8);
}

export async function refresh_semantic_index(args: { full?: boolean }): Promise<string> {
  return refreshReport(loadConfig(), args.full ?? false);
}
