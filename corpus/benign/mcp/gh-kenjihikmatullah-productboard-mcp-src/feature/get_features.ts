import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getFeaturesTool: Tool = {
    "name": "get_features",
    "description": "Returns a list of all features. This API is paginated and the page limit is always 100",
    "inputSchema": {
        "type": "object",
        "properties": {
            "page": {
                "type": "number",
                "default": 1
            }
        }
    }
}

interface GetFeaturesRequest {
    page?: number
}

const getFeatures = async (request: GetFeaturesRequest): Promise<any> => {
    let endpoint = "/features"
    if (request.page && request.page > 1) {
        endpoint += `?pageOffset=${(request.page - 1) * 100}`
    }

    return productboardClient.get(endpoint)
}

export { getFeaturesTool, GetFeaturesRequest, getFeatures }
