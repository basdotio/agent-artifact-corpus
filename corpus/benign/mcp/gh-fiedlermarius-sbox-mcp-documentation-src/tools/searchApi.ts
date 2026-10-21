import type { ApiSearch } from "../api-search.js";
import type { SearchApiParams } from "../schemas.js";

export function handleSearchApi(
    search: ApiSearch,
    params: SearchApiParams
): { content: Array<{ type: "text"; text: string }> } {
    const results = search.search(params.query, params.limit);

    if (results.length === 0) {
        return {
            content: [
                {
                    type: "text",
                    text: `No API types found for "${params.query}".\n\nTry a different class name, namespace, or method name. The API reference covers all public types in the s&box engine.`,
                },
            ],
        };
    }

    const lines = [`## API search results for "${params.query}"\n`];
    for (let i = 0; i < results.length; i++) {
        const r = results[i]!;
        const ns = r.namespace ? ` _(${r.namespace})_` : "";
        lines.push(`${i + 1}. **[${r.name}](${r.url})**${ns}`);
        if (r.description) {
            lines.push(`   > ${r.description}`);
        }
        if (r.topMembers.length > 0) {
            lines.push(`   Members: \`${r.topMembers.join("`, `")}\``);
        }
        lines.push("");
    }

    lines.push(
        `_${results.length} result(s). Use \`sbox_get_api_type\` with the full type name for properties, methods and signatures._`
    );

    return {
        content: [{ type: "text", text: lines.join("\n") }],
    };
}
