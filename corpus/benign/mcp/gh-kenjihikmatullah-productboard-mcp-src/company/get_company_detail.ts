import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getCompanyDetailTool: Tool = {
    "name": "get_company_detail",
    "description": "Returns detailed information about a specific company",
    "inputSchema": {
        "type": "object",
        "properties": {
            "companyId": {
                "type": "string",
                "description": "ID of the company to retrieve"
            }
        },
        "required": ["companyId"]
    }
}

interface GetCompanyDetailRequest {
    companyId: string
}

const getCompanyDetail = async (request: GetCompanyDetailRequest): Promise<any> => {
    const endpoint = `/companies/${request.companyId}`
    return productboardClient.get(endpoint)
}

export { getCompanyDetailTool, GetCompanyDetailRequest, getCompanyDetail }
