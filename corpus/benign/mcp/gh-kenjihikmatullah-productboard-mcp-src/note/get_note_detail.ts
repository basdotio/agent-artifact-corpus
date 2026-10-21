import { Tool } from "@modelcontextprotocol/sdk/types.js";
import productboardClient from "../productboard_client.js";

const getNoteDetailTool: Tool = {
    "name": "get_note_detail",
    "description": "Returns detailed information about a specific note",
    "inputSchema": {
        "type": "object",
        "properties": {
            "noteId": {
                "type": "string",
                "description": "ID of the note to retrieve"
            }
        },
        "required": ["noteId"]
    }
}

interface GetNoteDetailRequest {
    noteId: string
}

const getNoteDetail = async (request: GetNoteDetailRequest): Promise<any> => {
    const endpoint = `/notes/${request.noteId}`
    return productboardClient.get(endpoint)
}

export { getNoteDetailTool, GetNoteDetailRequest, getNoteDetail }
