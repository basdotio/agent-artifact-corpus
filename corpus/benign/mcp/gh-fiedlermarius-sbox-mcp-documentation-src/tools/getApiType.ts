import type { ApiSearch } from "../api-search.js";
import { formatTypeDetail } from "../api-search.js";
import type { GetApiTypeParams } from "../schemas.js";

export function handleGetApiType(
    search: ApiSearch,
    params: GetApiTypeParams
): { content: Array<{ type: "text"; text: string }> } {
    // Try exact lookup first (FullName or Name), then fuzzy search fallback
    let type = search.getType(params.name);

    if (!type) {
        // Fuzzy fallback: first search result
        const results = search.search(params.name, 1);
        if (results.length > 0) {
            type = search.getType(results[0]!.fullName);
        }
    }

    if (!type) {
        return {
            content: [
                {
                    type: "text",
                    text: `No API type found for "${params.name}".\n\nUse \`sbox_search_api\` to find the correct type name. Types should be specified by short name (e.g. "Component") or full name (e.g. "Sandbox.Component").`,
                },
            ],
        };
    }

    const text = formatTypeDetail(type, params.start_index, params.max_length);

    return {
        content: [{ type: "text", text }],
    };
}
