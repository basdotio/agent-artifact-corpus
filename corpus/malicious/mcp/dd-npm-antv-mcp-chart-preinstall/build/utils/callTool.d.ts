/**
 * Call a tool to generate a chart based on the provided name and arguments.
 * @param tool The name of the tool to call, e.g., "generate_area_chart".
 * @param args The arguments for the tool, which should match the expected schema for the chart type.
 * @returns
 */
export declare function callTool(tool: string, args?: object): Promise<{
    content: import("@modelcontextprotocol/sdk/types.js").CallToolResult["content"];
    isError?: import("@modelcontextprotocol/sdk/types.js").CallToolResult["isError"];
} | {
    content: {
        type: string;
        text: string;
    }[];
    _meta: {
        description: string;
        spec: {
            type: "area" | "bar" | "boxplot" | "column" | "district-map" | "dual-axes" | "fishbone-diagram" | "flow-diagram" | "funnel" | "histogram" | "line" | "liquid" | "mind-map" | "network-graph" | "organization-chart" | "path-map" | "pie" | "pin-map" | "radar" | "sankey" | "scatter" | "treemap" | "venn" | "violin" | "waterfall" | "word-cloud" | "spreadsheet";
        };
    };
}>;
