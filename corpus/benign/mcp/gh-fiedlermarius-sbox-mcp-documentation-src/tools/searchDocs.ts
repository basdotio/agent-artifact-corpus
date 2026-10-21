import type { DocSearch } from "../search.js";
import type { SearchDocsParams } from "../schemas.js";

export function handleSearchDocs(
    search: DocSearch,
    params: SearchDocsParams
): { content: Array<{ type: "text"; text: string }> } {
    const results = search.search(params.query, params.limit, params.category);

    if (results.length === 0) {
        return {
            content: [
                {
                    type: "text",
                    text: `No documentation found for "${params.query}".${params.category
                        ? ` Try without the category filter "${params.category}".`
                        : ""
                        }\n\nAvailable categories can be listed with sbox_list_doc_categories.`,
                },
            ],
        };
    }

    const lines = [`## Search results for "${params.query}"\n`];
    for (let i = 0; i < results.length; i++) {
        const r = results[i]!;
        lines.push(`${i + 1}. **[${r.title}](${r.url})** — _${r.category}_`);
        if (r.snippet) {
            lines.push(`   > ${r.snippet}`);
        }
        lines.push("");
    }

    lines.push(
        `_${results.length} result(s). Use sbox_get_doc_page to read the full content._`
    );

    return {
        content: [{ type: "text", text: lines.join("\n") }],
    };
}
