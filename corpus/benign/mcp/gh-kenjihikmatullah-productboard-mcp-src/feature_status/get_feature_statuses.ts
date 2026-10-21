import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getFeatureStatusesTool: Tool = {
    "name": "get_feature_statuses",
    "description": "Returns a list of all feature statuses. This API is paginated and the page limit is always 100",
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

interface GetFeatureStatusesRequest {
    page?: number
}

const getFeatureStatuses = async (request: GetFeatureStatusesRequest): Promise<any> => {
    let endpoint = "/feature-statuses"
    if (request.page && request.page > 1) {
        endpoint += `?pageOffset=${(request.page - 1) * 100}`
    }

    return productboardClient.get(endpoint)
}

export { getFeatureStatusesTool, GetFeatureStatusesRequest, getFeatureStatuses }
