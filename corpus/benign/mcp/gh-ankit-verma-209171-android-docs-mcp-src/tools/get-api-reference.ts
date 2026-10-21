/**
 * MCP Tool: get_api_reference
 * Look up API reference documentation for a specific Android class by fully-qualified class name.
 */

import { z } from "zod";
import { fetchPage, FetchError } from "../lib/fetcher.js";
import { parseApiReference } from "../lib/parser.js";
import { resolveClassUrl, isFqcn, type Language } from "../lib/url-resolver.js";

export const getApiReferenceToolName = "get_api_reference";

export const getApiReferenceToolDescription =
    "Get the API reference documentation for a specific Android class or interface. " +
    "Provide a fully-qualified class name (e.g., 'android.app.Activity', 'androidx.compose.ui.Modifier') " +
    "and get back detailed documentation including class hierarchy, constants, constructors, methods, " +
    "parameters, return types, and deprecation notices. " +
    "Use this when you need detailed API information about a specific class.";

export const getApiReferenceToolSchema = {
    class_name: z
        .string()
        .describe(
            "Fully-qualified class name (e.g., 'android.app.Activity', 'androidx.lifecycle.ViewModel', 'androidx.compose.material3.Text')",
        ),
    language: z
        .enum(["java", "kotlin"])
        .optional()
        .describe(
            "Documentation language variant. Defaults to 'kotlin' for AndroidX classes, 'java' for platform classes.",
        ),
};

export async function getApiReferenceToolHandler(args: {
    class_name: string;
    language?: "java" | "kotlin";
}): Promise<string> {
    const { class_name, language } = args;

    // Validate it looks like a FQCN
    if (!isFqcn(class_name)) {
        return (
            `Error: "${class_name}" doesn't look like a fully-qualified class name. ` +
            `Expected format: 'package.subpackage.ClassName' (e.g., 'android.app.Activity'). ` +
            `Use search_android_docs to find the correct class name.`
        );
    }

    const url = resolveClassUrl(class_name, language as Language | undefined);

    try {
        const html = await fetchPage(url);
        const markdown = parseApiReference(html);

        if (!markdown || markdown.trim().length === 0) {
            return `No API reference content found for "${class_name}" at ${url}. The class may not exist or the page format may be unexpected.`;
        }

        const lines: string[] = [];
        lines.push(`*Class: ${class_name} | Language: ${language ?? "auto"} | Source: ${url}*\n`);
        lines.push(markdown);

        return lines.join("\n");
    } catch (error) {
        if (error instanceof FetchError && error.statusCode === 404) {
            // Try the other language variant as fallback
            const altLang: Language = (language ?? "java") === "java" ? "kotlin" : "java";
            const altUrl = resolveClassUrl(class_name, altLang);

            try {
                const altHtml = await fetchPage(altUrl);
                const altMarkdown = parseApiReference(altHtml);

                if (altMarkdown && altMarkdown.trim().length > 0) {
                    const lines: string[] = [];
                    lines.push(
                        `*Class: ${class_name} | Language: ${altLang} (fallback) | Source: ${altUrl}*\n`,
                    );
                    lines.push(altMarkdown);
                    return lines.join("\n");
                }
            } catch {
                // Both variants failed
            }

            return (
                `Could not find API reference for "${class_name}". ` +
                `Tried:\n- ${url}\n- ${altUrl}\n\n` +
                `Use search_android_docs to find the correct class name.`
            );
        }
        throw error;
    }
}
