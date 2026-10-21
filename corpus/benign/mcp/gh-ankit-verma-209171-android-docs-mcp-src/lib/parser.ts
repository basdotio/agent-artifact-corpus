/**
 * HTML → Markdown parser using cheerio (pre-cleaning) + turndown (conversion).
 * Specialized extractors for search results, API reference, guides, and release notes.
 */

import * as cheerio from "cheerio";
import TurndownService from "turndown";

// ─── Turndown instance with custom rules ───────────────────────────────────

function createTurndown(): TurndownService {
    const td = new TurndownService({
        headingStyle: "atx",
        codeBlockStyle: "fenced",
        bulletListMarker: "-",
        emDelimiter: "*",
    });

    // Better code block handling — preserve language hints
    td.addRule("fencedCodeBlock", {
        filter: (node) => {
            return (
                node.nodeName === "PRE" &&
                node.firstChild !== null &&
                node.firstChild.nodeName === "CODE"
            );
        },
        replacement: (_content, node) => {
            const codeEl = node.firstChild as { getAttribute?: (s: string) => string | null; className?: string; textContent?: string | null } | null;
            const code = codeEl;
            if (!code) return _content;
            const lang =
                code.getAttribute?.("data-language") ||
                code.className?.replace(/^language-/, "").split(" ")[0] ||
                "";
            const text = code.textContent || "";
            return `\n\`\`\`${lang}\n${text.trim()}\n\`\`\`\n`;
        },
    });

    return td;
}

const turndown = createTurndown();

// ─── Shared: strip noise elements from any page ────────────────────────────

function stripNoise($: cheerio.CheerioAPI): void {
    // Remove scripts, styles, and hidden elements
    $("script, style, noscript, iframe, svg").remove();

    // Remove site navigation, header, footer, sidebar, ToC
    $(
        [
            "nav",
            "header",
            "footer",
            ".devsite-nav",
            ".devsite-toc",
            ".devsite-book-nav",
            ".devsite-header",
            ".devsite-footer",
            ".devsite-banner",
            ".devsite-top-button",
            ".devsite-search-background",
            "#gc-wrapper > nav",
            '[role="navigation"]',
            '[role="banner"]',
            '[role="contentinfo"]',
            ".nocontent",
            ".hide",
            ".dac-fab",
        ].join(", "),
    ).remove();

    // Remove "Was this helpful?" feedback widgets
    $(".devsite-content-footer, .devsite-thumbs-container").remove();

    // Remove icon/material-icon elements that produce garbage text
    $(".material-icons, .google-material-icons").remove();
}

// ─── Generic HTML → Markdown ───────────────────────────────────────────────

/**
 * Convert any HTML to clean markdown. Falls back to full-page conversion.
 */
export function htmlToMarkdown(html: string): string {
    const $ = cheerio.load(html);
    stripNoise($);

    // Try to find main content container
    const mainContent =
        $("article").html() ||
        $('[role="main"]').html() ||
        $(".devsite-article-body").html() ||
        $("main").html() ||
        $("body").html() ||
        "";

    return turndown.turndown(mainContent).trim();
}

// ─── Search Results Parser ─────────────────────────────────────────────────

export interface SearchApiResult {
    name: string;
    url: string;
}

export interface SearchGuideResult {
    title: string;
    url: string;
    snippet: string;
}

export interface SearchResults {
    apiResults: SearchApiResult[];
    guideResults: SearchGuideResult[];
    query: string;
}

/**
 * Parse the search results page at /s/results?q=...
 * Extracts API reference matches and guide/tutorial results.
 */
export function parseSearchResults(html: string, query: string): SearchResults {
    const $ = cheerio.load(html);

    const apiResults: SearchApiResult[] = [];
    const guideResults: SearchGuideResult[] = [];

    // API reference results — they appear as links in a list/section
    // The search page shows class names as links under "API reference" heading
    $("a").each((_i, el) => {
        const href = $(el).attr("href") || "";
        const text = $(el).text().trim();

        // Match API reference links
        if (
            href.includes("/reference/") &&
            text &&
            !text.includes("API reference") &&
            !text.includes("Class Index") &&
            !text.includes("Package Index") &&
            text.length < 200
        ) {
            const url = href.startsWith("http")
                ? href
                : `https://developer.android.com${href}`;

            // Avoid duplicates
            if (!apiResults.some((r) => r.url === url.split("?")[0])) {
                apiResults.push({
                    name: text,
                    url: (url.split("?")[0] ?? url), // strip hl= params
                });
            }
        }
    });

    // Guide/tutorial results — cards with thumbnail, title, URL, and snippet
    // These appear as link blocks with descriptive text
    $("a[href]").each((_i, el) => {
        const href = $(el).attr("href") || "";
        const text = $(el).text().trim();

        // Match guide/develop/training links that look like result cards
        if (
            (href.includes("/guide/") ||
                href.includes("/develop/") ||
                href.includes("/training/") ||
                href.includes("/jetpack/")) &&
            !href.includes("/reference/") &&
            text.length > 10 &&
            text.length < 300
        ) {
            const url = href.startsWith("http")
                ? href
                : `https://developer.android.com${href}`;

            // Extract title from the link text (first line / sentence)
            const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
            const title = lines[0] || text;
            const snippet = lines.slice(1).join(" ").trim();

            if (
                title &&
                !guideResults.some((r) => r.url === url.split("?")[0]) &&
                !title.includes("Android Developers")
            ) {
                guideResults.push({
                    title,
                    url: (url.split("?")[0] ?? url),
                    snippet: snippet.slice(0, 300),
                });
            }
        }
    });

    return { apiResults, guideResults, query };
}

// ─── API Reference Parser ──────────────────────────────────────────────────

/**
 * Parse an API reference page (/reference/...).
 * Returns clean markdown preserving class hierarchy, methods, constants, etc.
 */
export function parseApiReference(html: string): string {
    const $ = cheerio.load(html);
    stripNoise($);

    // Find the main API content
    const content =
        $("article").html() ||
        $('[role="main"]').html() ||
        $(".devsite-article-body").html() ||
        $("main").html() ||
        "";

    if (!content) {
        return htmlToMarkdown(html);
    }

    // Convert to markdown
    let md = turndown.turndown(content).trim();

    // Clean up excessive whitespace and repeated headings
    md = md
        .replace(/\n{4,}/g, "\n\n\n")
        .replace(/bookmark_border/g, "")
        .replace(/arrow_drop_down/g, "")
        .replace(/content_copy/g, "")
        .replace(/\s*expand_more\s*/g, "")
        .replace(/\s*more_horiz\s*/g, "");

    return md;
}

// ─── Guide Page Parser ─────────────────────────────────────────────────────

/**
 * Parse a developer guide page (/guide/..., /develop/..., /training/...).
 * Returns clean markdown with headings, paragraphs, code samples, and links.
 */
export function parseGuidePage(html: string): string {
    const $ = cheerio.load(html);
    stripNoise($);

    // Guide content is typically in the article or devsite-article-body
    const content =
        $("article").html() ||
        $(".devsite-article-body").html() ||
        $('[role="main"]').html() ||
        $("main").html() ||
        "";

    if (!content) {
        return htmlToMarkdown(html);
    }

    let md = turndown.turndown(content).trim();

    // Clean up UI artifacts
    md = md
        .replace(/\n{4,}/g, "\n\n\n")
        .replace(/bookmark_border/g, "")
        .replace(/content_copy/g, "")
        .replace(/arrow_drop_down/g, "")
        .replace(/\s*expand_more\s*/g, "")
        .replace(/\s*more_horiz\s*/g, "")
        .replace(/light_mode/g, "")
        .replace(/dark_mode/g, "");

    return md;
}

// ─── Release Notes Parser ──────────────────────────────────────────────────

export interface ReleaseEntry {
    version: string;
    date: string;
    content: string;
}

/**
 * Parse a Jetpack release notes page (/jetpack/androidx/releases/...).
 * Returns structured release entries.
 */
export function parseReleaseNotes(html: string): ReleaseEntry[] {
    const $ = cheerio.load(html);
    stripNoise($);

    const entries: ReleaseEntry[] = [];

    // Release notes pages use h2/h3 headings for versions like "Version 2.8.0"
    $("h2, h3").each((_i, el) => {
        const heading = $(el).text().trim();

        // Match version headings like "Version 2.8.0", "1.0.0-alpha01"
        const versionMatch = heading.match(
            /(?:Version\s+)?(\d+\.\d+[\w.-]*)/i,
        );
        if (!versionMatch) return;

        const version = versionMatch[1];

        // Look for date in a nearby element or within the heading
        let date = "";
        const nextEl = $(el).next();
        const dateText = nextEl.text();
        const dateMatch = dateText.match(
            /(\w+ \d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})/,
        );
        if (dateMatch) {
            date = dateMatch[1] ?? "";
        }

        // Collect content until next version heading
        let contentHtml = "";
        let sibling = $(el).next();
        while (sibling.length && !sibling.is("h2") && !sibling.is("h3")) {
            // Skip if it's another version heading
            const sibText = sibling.text().trim();
            if (/^(?:Version\s+)?\d+\.\d+/.test(sibText) && sibling.is("h2, h3")) {
                break;
            }
            contentHtml += $.html(sibling);
            sibling = sibling.next();
        }

        const content = contentHtml
            ? turndown.turndown(contentHtml).trim()
            : "";

        if (content) {
            entries.push({ version: version ?? "", date, content });
        }
    });

    // If no structured entries found, fall back to generic parsing
    if (entries.length === 0) {
        const md = htmlToMarkdown(html);
        if (md) {
            entries.push({ version: "latest", date: "", content: md });
        }
    }

    return entries;
}

// ─── Package List Parser ───────────────────────────────────────────────────

export interface PackageInfo {
    name: string;
    url: string;
    description: string;
}

/**
 * Parse a package index page (/reference/packages, /reference/kotlin/androidx/packages, etc.)
 */
export function parsePackageList(html: string): PackageInfo[] {
    const $ = cheerio.load(html);
    stripNoise($);

    const packages: PackageInfo[] = [];

    // Package pages list packages as links, often in tables or lists
    $("a[href]").each((_i, el) => {
        const href = $(el).attr("href") || "";
        const text = $(el).text().trim();

        // Match package links (contain /reference/ and look like package names)
        if (
            href.includes("/reference/") &&
            (href.includes("package-summary") || href.match(/\/reference\/(?:kotlin\/)?(?:android|androidx|java|com)\//)) &&
            text &&
            text.match(/^[a-z][\w.]*$/i) && // looks like a package name
            text.length < 100
        ) {
            const url = href.startsWith("http")
                ? href
                : `https://developer.android.com${href}`;

            // Get description from parent or sibling
            const parent = $(el).parent();
            const desc =
                parent.find("td:last-child, .desc, p").first().text().trim() || "";

            if (!packages.some((p) => p.name === text)) {
                packages.push({
                    name: text,
                    url: (url.split("?")[0] ?? url),
                    description: desc.slice(0, 200),
                });
            }
        }
    });

    return packages;
}

// ─── Auto-detect page type and parse ───────────────────────────────────────

export type PageType =
    | "api-reference"
    | "guide"
    | "release-notes"
    | "package-list"
    | "search"
    | "unknown";

export function detectPageType(url: string): PageType {
    const path = new URL(url).pathname;

    if (path.includes("/s/results")) return "search";
    if (path.match(/\/reference\/.+\/packages?$/)) return "package-list";
    if (path.includes("/reference/")) return "api-reference";
    if (path.includes("/jetpack/androidx/releases/")) return "release-notes";
    if (
        path.includes("/guide/") ||
        path.includes("/develop/") ||
        path.includes("/training/") ||
        path.includes("/codelabs/")
    )
        return "guide";

    return "unknown";
}

/**
 * Auto-detect page type from URL and apply the right parser.
 */
export function parsePage(html: string, url: string): string {
    const type = detectPageType(url);

    switch (type) {
        case "api-reference":
            return parseApiReference(html);
        case "guide":
            return parseGuidePage(html);
        case "release-notes": {
            const entries = parseReleaseNotes(html);
            return entries
                .map((e) => `## ${e.version}${e.date ? ` (${e.date})` : ""}\n\n${e.content}`)
                .join("\n\n---\n\n");
        }
        case "package-list": {
            const pkgs = parsePackageList(html);
            return pkgs
                .map((p) => `- [${p.name}](${p.url})${p.description ? ` — ${p.description}` : ""}`)
                .join("\n");
        }
        default:
            return htmlToMarkdown(html);
    }
}
