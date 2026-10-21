import type { DocSearch } from "../search.js";

export function handleListCategories(
    search: DocSearch
): { content: Array<{ type: "text"; text: string }> } {
    const categories = search.getCategories();

    if (categories.length === 0) {
        return {
            content: [
                {
                    type: "text",
                    text: "No documentation has been indexed yet. The server may still be crawling. Try again shortly.",
                },
            ],
        };
    }

    const lines = [
        `## S&box Documentation Categories\n`,
        `Total: ${search.pageCount} pages across ${categories.length} categories\n`,
    ];

    for (const cat of categories) {
        lines.push(`### ${cat.name} (${cat.pageCount} pages)\n`);
        for (const p of cat.pages) {
            lines.push(`- [${p.title}](${p.url})`);
        }
        lines.push("");
    }

    return {
        content: [{ type: "text", text: lines.join("\n") }],
    };
}
