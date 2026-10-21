import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { z } from "zod";
import * as notes from "./notes";

const server = new McpServer({
    name: "Notes",
    version: "1.0.0",
});

server.tool(
    "notes-create-note",
    "Create a new note in a specific folder and get back the note with its identifier",
    {
        folderId: z
            .string()
            .describe("Identifier of the folder to create the note in"),
        name: z.string().describe("Name of the note"),
        body: z.string().describe("Content of the note"),
    },
    async ({ folderId, name, body }) => {
        const result = await notes.createNote(folderId, { name, body });

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result),
                },
            ],
        };
    }
);

server.tool(
    "notes-get-folders",
    "Retrieve all folders with names and identifiers",
    async () => {
        const result = await notes.getFolders();

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result),
                },
            ],
        };
    }
);

server.tool(
    "notes-get-notes",
    "Retrieve all notes from a specific folder",
    {
        folderId: z.string().describe("ID of the folder to get notes from"),
    },
    async ({ folderId }) => {
        const result = await notes.getNotes(folderId);

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result),
                },
            ],
        };
    }
);

server.tool(
    "notes-get-note-by-id",
    "Retrieve a note by its identifier",
    {
        id: z.string().describe("Identifier of the note to retrieve"),
    },
    async ({ id }) => {
        const result = await notes.getNoteById(id);

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result),
                },
            ],
        };
    }
);

server.tool(
    "notes-get-note-by-title",
    "Retrieve a note by its exact title match",
    {
        title: z.string().describe("Title of the note to retrieve"),
    },
    async ({ title }) => {
        const result = await notes.getNoteByTitle(title);

        return {
            content: [
                {
                    type: "text",
                    text: JSON.stringify(result),
                },
            ],
        };
    }
);

server.tool("notes-note-count", "Get the total number of notes", async () => {
    const result = await notes.noteCount();

    return {
        content: [
            {
                type: "text",
                text: JSON.stringify({
                    count: result,
                }),
            },
        ],
    };
});

export { server };
