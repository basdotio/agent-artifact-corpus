import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
/**
 * Generate a chart URL using the provided configuration.
 * @param type The type of chart to generate
 * @param options Chart options
 * @returns {Promise<string>} The generated chart URL.
 * @throws {Error} If the chart generation fails.
 */
export declare function generateChartUrl(type: string, options: Record<string, any>): Promise<string>;
type ResponseResult = {
    metadata: unknown;
    /**
     * @docs https://modelcontextprotocol.io/specification/2025-03-26/server/tools#tool-result
     */
    content: CallToolResult["content"];
    isError?: CallToolResult["isError"];
};
/**
 * Generate a map
 * @param tool - The tool name
 * @param input - The input
 * @returns
 */
export declare function generateMap(tool: string, input: unknown): Promise<ResponseResult>;
export {};
