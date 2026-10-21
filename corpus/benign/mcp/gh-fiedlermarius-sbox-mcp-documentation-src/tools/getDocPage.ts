import type { DocSearch } from "../search.js";
import type { DocCrawler } from "../crawler.js";
import type { GetDocPageParams } from "../schemas.js";

export async function handleGetDocPage(
    search: DocSearch,
    crawler: DocCrawler,
    params: GetDocPageParams
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
    // Normalize URL — strip trailing slash for consistency
    const url = params.url.endsWith("/") ? params.url.slice(0, -1) : params.url;

    // Try from index first, then crawl on demand
    let page = search.getPage(url);
    if (!page) {
        page = (await crawler.crawlSinglePage(url)) || undefined;
    }

    if (!page) {
        return {
            content: [
                {
                    type: "text",
                    text: `Could not fetch the page at ${url}. The page may not exist, require authentication, or be temporarily unavailable.`,
                },
            ],
        };
    }

    const markdown = page.markdown;
    const totalLength = markdown.length;
    const startIndex = Math.min(params.start_index, totalLength);
    const chunk = markdown.slice(startIndex, startIndex + params.max_length);
    const endIndex = startIndex + chunk.length;
    const hasMore = endIndex < totalLength;

    const header = `# ${page.title}\n\n**Section:** ${page.category} | **Source:** [${page.url}](${page.url})`;
    const footer = hasMore
        ? `\n\n---\n_Showing characters ${startIndex}–${endIndex} of ${totalLength}. Use start_index=${endIndex} to read the next chunk._`
        : `\n\n---\n_End of page (${totalLength} characters total)._`;

    return {
        content: [
            {
                type: "text",
                text: `${header}\n${page.lastUpdated ? `**Last updated:** ${page.lastUpdated}\n` : ""}\n---\n\n${chunk}${footer}`,
            },
        ],
    };
}
