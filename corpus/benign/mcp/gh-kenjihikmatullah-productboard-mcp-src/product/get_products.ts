import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getProductsTool: Tool = {
    "name": "get_products",
    "description": "Returns detail of all products. This API is paginated and the page limit is always 100",
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

interface GetProductsRequest {
    page?: number
}

const getProducts = async (request: GetProductsRequest): Promise<any> => {
    let endpoint = "/products"
    if (request.page && request.page > 1) {
        endpoint += `?pageOffset=${(request.page - 1) * 100}`
    }

    return productboardClient.get(endpoint)
}

export { getProductsTool, GetProductsRequest, getProducts }
