import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getNotesTool: Tool = {
    "name": "get_notes",
    "description": "Returns a list of all notes",
    "inputSchema": {
        "type": "object",
        "properties": {
            "last": {
                "type": "string",
                "description": "Return only notes created since given span of months (m), days (s), or hours (h). E.g. 6m | 10d | 24h | 1h. Cannot be combined with createdFrom, createdTo, dateFrom, or dateTo"
            },
            "createdFrom": {
                "type": "string",
                "format": "date",
                "description": "Return only notes created since given date. Cannot be combined with last"
            },
            "createdTo": {
                "type": "string",
                "format": "date",
                "description": "Return only notes created before or equal to the given date. Cannot be combined with last"
            },
            "updatedFrom": {
                "type": "string",
                "format": "date",
                "description": "Return only notes updated since given date"
            },
            "updatedTo": {
                "type": "string",
                "format": "date",
                "description": "Return only notes updated before or equal to the given date"
            },
            "term": {
                "type": "string",
                "description": "Return only notes by fulltext search"
            },
            "featureId": {
                "type": "string",
                "description": "Return only notes for specific feature ID or its descendants"
            },
            "companyId": {
                "type": "string",
                "description": "Return only notes for specific company ID"
            },
            "ownerEmail": {
                "type": "string",
                "description": "Return only notes owned by a specific owner email"
            },
            "source": {
                "type": "string",
                "description": "Return only notes from a specific source origin. This is the unique string identifying the external system from which the data came"
            },
            "anyTag": {
                "type": "string",
                "description": "Return only notes that have been assigned any of the tags in the array. Cannot be combined with allTags"
            },
            "allTags": {
                "type": "string",
                "description": "Return only notes that have been assigned all of the tags in the array. Cannot be combined with anyTag"
            },
            "pageLimit": {
                "type": "number",
                "description": "Page limit"
            },
            "pageCursor": {
                "type": "string",
                "description": "Page cursor to get next page of results"
            }
        }
    }
}

interface GetNotesRequest {
    last?: string;
    createdFrom?: string;
    createdTo?: string;
    updatedFrom?: string;
    updatedTo?: string;
    term?: string;
    featureId?: string;
    companyId?: string;
    ownerEmail?: string;
    source?: string;
    anyTag?: string;
    allTags?: string;
    pageLimit?: number;
    pageCursor?: string;
}

const getNotes = async (request: GetNotesRequest): Promise<any> => {
    // Validate mutually exclusive parameters
    if (request.last && (request.createdFrom || request.createdTo)) {
        throw new Error("'last' parameter cannot be combined with 'createdFrom' or 'createdTo'");
    }
    if (request.anyTag && request.allTags) {
        throw new Error("'anyTag' cannot be combined with 'allTags'");
    }

    const params = new URLSearchParams()
    
    if (request.last) {
        params.append('last', request.last)
    }
    if (request.createdFrom) {
        params.append('createdFrom', request.createdFrom)
    }
    if (request.createdTo) {
        params.append('createdTo', request.createdTo)
    }
    if (request.updatedFrom) {
        params.append('updatedFrom', request.updatedFrom)
    }
    if (request.updatedTo) {
        params.append('updatedTo', request.updatedTo)
    }
    if (request.term) {
        params.append('term', request.term)
    }
    if (request.featureId) {
        params.append('featureId', request.featureId)
    }
    if (request.companyId) {
        params.append('companyId', request.companyId)
    }
    if (request.ownerEmail) {
        params.append('ownerEmail', request.ownerEmail)
    }
    if (request.source) {
        params.append('source', request.source)
    }
    if (request.anyTag) {
        params.append('anyTag', request.anyTag)
    }
    if (request.allTags) {
        params.append('allTags', request.allTags)
    }
    if (request.pageLimit) {
        params.append('pageLimit', request.pageLimit.toString())
    }
    if (request.pageCursor) {
        params.append('pageCursor', request.pageCursor)
    }

    const queryString = params.toString()
    const endpoint = `/notes${queryString ? `?${queryString}` : ''}`

    return productboardClient.get(endpoint)
}

export { getNotesTool, GetNotesRequest, getNotes }
