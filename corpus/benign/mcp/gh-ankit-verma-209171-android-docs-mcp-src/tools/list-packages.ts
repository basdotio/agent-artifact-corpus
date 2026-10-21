/**
 * MCP Tool: list_android_packages
 * List available Android SDK or AndroidX (Jetpack) packages from the official package index.
 */

import { z } from "zod";
import { fetchPage } from "../lib/fetcher.js";
import { parsePackageList } from "../lib/parser.js";
import { getPackageIndexUrl, type Language } from "../lib/url-resolver.js";

export const listPackagesToolName = "list_android_packages";

export const listPackagesToolDescription =
    "List available Android packages from the official package index. " +
    "Choose 'platform' for core Android SDK packages (android.*, java.*, etc.) " +
    "or 'androidx' for Jetpack/AndroidX library packages. " +
    "Returns package names, URLs, and brief descriptions. " +
    "Use this to discover available packages before looking up specific classes.";

export const listPackagesToolSchema = {
    type: z
        .enum(["platform", "androidx"])
        .default("androidx")
        .describe(
            "Which package set to list: 'platform' for core Android SDK, 'androidx' for Jetpack libraries.",
        ),
    language: z
        .enum(["java", "kotlin"])
        .optional()
        .describe(
            "Documentation language variant. Defaults to 'java'.",
        ),
    filter: z
        .string()
        .optional()
        .describe(
            "Optional substring filter to narrow results (e.g., 'compose', 'lifecycle'). Case-insensitive.",
        ),
};

export async function listPackagesToolHandler(args: {
    type: "platform" | "androidx";
    language?: "java" | "kotlin";
    filter?: string;
}): Promise<string> {
    const { type, language, filter } = args;
    const lang: Language = language ?? "java";

    const url = getPackageIndexUrl(type, lang);
    const html = await fetchPage(url);
    let packages = parsePackageList(html);

    // Apply optional filter
    if (filter) {
        const lowerFilter = filter.toLowerCase();
        packages = packages.filter(
            (p) =>
                p.name.toLowerCase().includes(lowerFilter) ||
                p.description.toLowerCase().includes(lowerFilter),
        );
    }

    if (packages.length === 0) {
        const filterNote = filter ? ` matching "${filter}"` : "";
        return `No packages found${filterNote} in the ${type} index (${lang}). Source: ${url}`;
    }

    const lines: string[] = [];
    const label = type === "androidx" ? "AndroidX / Jetpack" : "Android Platform SDK";
    lines.push(`## ${label} Packages (${lang})\n`);
    lines.push(`*${packages.length} packages found | Source: ${url}*\n`);

    for (const pkg of packages) {
        if (pkg.description) {
            lines.push(`- **${pkg.name}** — ${pkg.description}`);
        } else {
            lines.push(`- **${pkg.name}**`);
        }
        lines.push(`  ${pkg.url}`);
    }

    return lines.join("\n");
}
