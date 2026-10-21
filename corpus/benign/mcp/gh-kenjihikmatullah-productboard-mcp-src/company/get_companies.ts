import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getCompaniesTool: Tool = {
    "name": "get_companies",
    "description": "Returns a list of all companies. This API is paginated and the page limit is always 100",
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

interface GetCompaniesRequest {
    page?: number
}

const getCompanies = async (request: GetCompaniesRequest): Promise<any> => {
    let endpoint = "/companies"
    if (request.page && request.page > 1) {
        endpoint += `?pageOffset=${(request.page - 1) * 100}`
    }

    return productboardClient.get(endpoint)
}

export { getCompaniesTool, GetCompaniesRequest, getCompanies }
