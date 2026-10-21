#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequest,
    CallToolRequestSchema,
    ListToolsRequestSchema
} from "@modelcontextprotocol/sdk/types.js";
import { getProductsTool, GetProductsRequest, getProducts } from "./product/get_products.js";
import { getProductDetailTool, GetProductDetailRequest, getProductDetail } from "./product/get_product_detail.js";
import { getFeaturesTool, GetFeaturesRequest, getFeatures } from "./feature/get_features.js";
import { getFeatureDetailTool, GetFeatureDetailRequest, getFeatureDetail } from "./feature/get_feature_detail.js";
import { getComponentsTool, GetComponentsRequest, getComponents } from "./component/get_components.js";
import { getComponentDetailTool, GetComponentDetailRequest, getComponentDetail } from "./component/get_component_detail.js";
import { getFeatureStatusesTool, GetFeatureStatusesRequest, getFeatureStatuses } from "./feature_status/get_feature_statuses.js";
import { getNotesTool, GetNotesRequest, getNotes } from "./note/get_notes.js";
import { getNoteDetailTool, GetNoteDetailRequest, getNoteDetail } from "./note/get_note_detail.js";
import { getCompaniesTool, GetCompaniesRequest, getCompanies } from "./company/get_companies.js";
import { getCompanyDetailTool, GetCompanyDetailRequest, getCompanyDetail } from "./company/get_company_detail.js";

async function main() {
    const productboardAccessToken = process.env.PRODUCTBOARD_ACCESS_TOKEN

    if (!productboardAccessToken) {
        console.error("Please set PRODUCTBOARD_ACCESS_TOKEN environment variable");
        process.exit(1);
    }

    const server = new Server(
        {
            name: "Productboard MCP Server",
            version: "1.0.0",
        },
        {
            capabilities: {
                tools: {},
            },
        }
    );

    server.setRequestHandler(
        CallToolRequestSchema,
        async (request: CallToolRequest) => {
            console.info("Received CallToolRequest: ", request);

            try {
                const { name, arguments: args } = request.params

                switch (name) {
                    case getProductsTool.name: {
                        const request = args as unknown as GetProductsRequest;
                        const result = await getProducts(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getProductDetailTool.name: {
                        const request = args as unknown as GetProductDetailRequest;
                        const result = await getProductDetail(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getFeaturesTool.name: {
                        const request = args as unknown as GetFeaturesRequest;
                        const result = await getFeatures(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getFeatureDetailTool.name: {
                        const request = args as unknown as GetFeatureDetailRequest;
                        const result = await getFeatureDetail(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getComponentsTool.name: {
                        const request = args as unknown as GetComponentsRequest;
                        const result = await getComponents(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getComponentDetailTool.name: {
                        const request = args as unknown as GetComponentDetailRequest;
                        const result = await getComponentDetail(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getFeatureStatusesTool.name: {
                        const request = args as unknown as GetFeatureStatusesRequest;
                        const result = await getFeatureStatuses(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getNotesTool.name: {
                        const request = args as unknown as GetNotesRequest;
                        const result = await getNotes(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getNoteDetailTool.name: {
                        const request = args as unknown as GetNoteDetailRequest;
                        const result = await getNoteDetail(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getCompaniesTool.name: {
                        const request = args as unknown as GetCompaniesRequest;
                        const result = await getCompanies(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    case getCompanyDetailTool.name: {
                        const request = args as unknown as GetCompanyDetailRequest;
                        const result = await getCompanyDetail(request);
                        return {
                            content: [{ type: "text", text: JSON.stringify(result) }],
                        }
                    }

                    default:
                        throw new Error(`Unknown tool: ${name}`);
                }

            } catch (error) {
                console.error("Error executing tool: ", error);
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                error: error instanceof Error ? error.message : String(error),
                            }),
                        },
                    ],
                };
            }
        }
    )

    server.setRequestHandler(ListToolsRequestSchema, async () => {
        console.info("Received ListToolsRequest");
        return {
            tools: [
                getProductsTool,
                getProductDetailTool,
                getFeaturesTool,
                getFeatureDetailTool,
                getComponentsTool,
                getComponentDetailTool,
                getFeatureStatusesTool,
                getNotesTool,
                getNoteDetailTool,
                getCompaniesTool,
                getCompanyDetailTool
            ],
        };
    });

    const transport = new StdioServerTransport();
    console.log("Connecting server to transport...");
    await server.connect(transport);

    console.log("Productboard MCP Server running on stdio");
}

main().catch((error) => {
    console.error("Fatal error in main():", error);
    process.exit(1);
});
