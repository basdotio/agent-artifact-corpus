import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getComponentsTool: Tool = {
    "name": "get_components",
    "description": "Returns a list of all components. This API is paginated and the page limit is always 100",
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

interface GetComponentsRequest {
    page?: number
}

const getComponents = async (request: GetComponentsRequest): Promise<any> => {
    let endpoint = "/components"
    if (request.page && request.page > 1) {
        endpoint += `?pageOffset=${(request.page - 1) * 100}`
    }

    return productboardClient.get(endpoint)
}

export { getComponentsTool, GetComponentsRequest, getComponents }
