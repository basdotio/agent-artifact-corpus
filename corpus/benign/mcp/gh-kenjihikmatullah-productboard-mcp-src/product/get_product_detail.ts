import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getProductDetailTool: Tool = {
    "name": "get_product_detail",
    "description": "Returns detailed information about a specific product",
    "inputSchema": {
        "type": "object",
        "properties": {
            "productId": {
                "type": "string",
                "description": "ID of the product to retrieve"
            }
        },
        "required": ["productId"]
    }
}

interface GetProductDetailRequest {
    productId: string
}

const getProductDetail = async (request: GetProductDetailRequest): Promise<any> => {
    const endpoint = `/products/${request.productId}`
    return productboardClient.get(endpoint)
}

export { getProductDetailTool, GetProductDetailRequest, getProductDetail }
