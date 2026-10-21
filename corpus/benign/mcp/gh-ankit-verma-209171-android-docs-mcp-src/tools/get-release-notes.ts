/**
 * MCP Tool: get_release_notes
 * Fetch release notes for a Jetpack (AndroidX) library.
 */

import { z } from "zod";
import { fetchPage, FetchError } from "../lib/fetcher.js";
import { parseReleaseNotes } from "../lib/parser.js";
import { getReleaseNotesUrl } from "../lib/url-resolver.js";

export const getReleaseNotesToolName = "get_release_notes";

export const getReleaseNotesToolDescription =
  "Get release notes for an AndroidX / Jetpack library. " +
  "Provide a library name (e.g., 'compose', 'navigation', 'lifecycle', 'room', 'paging') " +
  "and optionally a specific version to filter to. " +
  "Returns version history with dates, changes, bug fixes, and new features.";

export const getReleaseNotesToolSchema = {
  library: z
    .string()
    .describe(
      "Jetpack library name (e.g., 'compose', 'navigation', 'lifecycle', 'room', 'paging', 'activity', 'fragment').",
    ),
  version: z
    .string()
    .optional()
    .describe(
      "Optional version filter. Returns only release notes matching this version (e.g., '2.8.0', '1.0.0-alpha01'). Partial match supported.",
    ),
  max_entries: z
    .number()
    .int()
    .min(1)
    .max(50)
    .default(5)
    .describe("Maximum number of release entries to return (default: 5)."),
};

export async function getReleaseNotesToolHandler(args: {
  library: string;
  version?: string;
  max_entries: number;
}): Promise<string> {
  const { library, version, max_entries } = args;

  const url = getReleaseNotesUrl(library);

  try {
    const html = await fetchPage(url);
    let entries = parseReleaseNotes(html);

    // Filter by version if specified
    if (version) {
      entries = entries.filter((e) => e.version.includes(version));
      if (entries.length === 0) {
        return (
          `No release notes found for version "${version}" of "${library}". ` +
          `Try without the version filter to see all available versions. Source: ${url}`
        );
      }
    }

    // Limit entries
    const limited = entries.slice(0, max_entries);
    const hasMore = entries.length > max_entries;

    if (limited.length === 0) {
      return `No release notes found for "${library}". Source: ${url}`;
    }

    const lines: string[] = [];
    lines.push(`## Release Notes: ${library}\n`);
    lines.push(
      `*${limited.length}${hasMore ? ` of ${entries.length}` : ""} entries | Source: ${url}*\n`,
    );

    for (const entry of limited) {
      const datePart = entry.date ? ` (${entry.date})` : "";
      lines.push(`### ${entry.version}${datePart}\n`);
      lines.push(entry.content);
      lines.push(""); // blank line separator
    }

    if (hasMore) {
      lines.push(
        `\n*${entries.length - max_entries} more entries available — increase max_entries or visit ${url}*`,
      );
    }

    return lines.join("\n");
  } catch (error) {
    if (error instanceof FetchError && error.statusCode === 404) {
      return (
        `Could not find release notes for "${library}" at ${url}. ` +
        `Check the library name — common values: compose, navigation, lifecycle, room, paging, activity, fragment, work.`
      );
    }
    throw error;
  }
}
