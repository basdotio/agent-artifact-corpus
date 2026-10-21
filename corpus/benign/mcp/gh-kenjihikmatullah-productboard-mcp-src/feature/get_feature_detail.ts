import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getFeatureDetailTool: Tool = {
    "name": "get_feature_detail",
    "description": "Returns detailed information about a specific feature",
    "inputSchema": {
        "type": "object",
        "properties": {
            "featureId": {
                "type": "string",
                "description": "ID of the feature to retrieve"
            }
        },
        "required": ["featureId"]
    }
}

interface GetFeatureDetailRequest {
    featureId: string
}

const getFeatureDetail = async (request: GetFeatureDetailRequest): Promise<any> => {
    const endpoint = `/features/${request.featureId}`
    return productboardClient.get(endpoint)
}

export { getFeatureDetailTool, GetFeatureDetailRequest, getFeatureDetail }
