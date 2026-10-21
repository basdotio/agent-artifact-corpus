#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

/**
 * Create an MCP server with capabilities for resources (to list/read notes),
 * tools (to create new notes), and prompts (to summarize notes).
 */
const server = new Server(
  {
    name: "anki-mcp",
    version: "0.1.0",
  },
  {
    capabilities: {
      resources: {},
      tools: {},
    },
  },
);

type AnkiRequestResult<T> = {
  result: T;
  error: string;
};
/**
 * Make a request to the AnkiConnect API
 */
async function ankiRequest<T>(action: string, params: any = {}): Promise<T> {
  const response = await fetch("http://localhost:8765", {
    method: "POST",
    body: JSON.stringify({
      action,
      version: 6,
      params,
    }),
  });
  const { result } = (await response.json()) as AnkiRequestResult<T>;
  return result;
}

type DeckNamesToIds = Record<string, number>;
type ModelNamesToIds = Record<string, number>;

/**
 * Handler that lists available tools.
 * Exposes a single "create_note" tool that lets clients create new notes.
 */
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  const decks = await ankiRequest<DeckNamesToIds>("deckNamesAndIds");
  const models = await ankiRequest<ModelNamesToIds>("modelNamesAndIds");

  const deckResources = Object.entries(decks).map(([name, id]) => ({
    uri: `anki://decks/${id}`,
    name,
  }));

  const modelResources = Object.entries(models).map(([name, id]) => ({
    uri: `anki://models/${id}`,
    name,
  }));

  return {
    resources: deckResources.concat(modelResources),
  };
});

/**
 * Handler that lists available tools.
 * Exposes a single "create_note" tool that lets clients create new notes.
 */
server.setRequestHandler(ReadResourceRequestSchema, async (resource) => {
  const uri = resource.params.uri;

  if (uri.startsWith("anki://decks/")) {
    const deckId = parseInt(uri.replace("anki://decks/", ""));
    // TODO: return something real
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify({ deckId }),
        },
      ],
    };
  } else if (uri.startsWith("anki://models/")) {
    const modelId = parseInt(uri.replace("anki://models/", ""));
    const models = await ankiRequest<object>("findModelsById", {
      modelIds: [modelId],
    });
    return {
      contents: [
        {
          uri,
          mimeType: "application/json",
          text: JSON.stringify(models),
        },
      ],
    };
  }
  throw new Error("resource not found");
});

const noteParameters = {
  type: "object",
  properties: {
    deckName: {
      type: "string",
      description: "Name of the deck to add note to",
    },
    modelName: {
      type: "string",
      description: "Name of the note model/type to use",
    },
    fields: {
      type: "object",
      description: "Map of fields to the value in the note model being used",
    },
    tags: {
      type: "array",
      items: {
        type: "string",
      },
      description: "Tags to apply to the note",
    },
  },
  required: ["deckName", "modelName", "fields"],
};

/**
 * Handler that lists available tools.
 * Exposes a single "create_note" tool that lets clients create new notes.
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "listDecks",
        description: "Get the names of all decks from Anki",
        inputSchema: { type: "object", properties: {} },
      },
      {
        name: "listModels",
        description: "Get the names of all note models from Anki",
        inputSchema: { type: "object", properties: {} },
      },
      {
        name: "getModel",
        description:
          "Get a model, including field and template definitions, from Anki",
        inputSchema: {
          type: "object",
          properties: {
            modelName: {
              type: "string",
              description: "Name of the model to get",
            },
          },
        },
      },
      {
        name: "addNote",
        description: "Create a single note",
        inputSchema: noteParameters,
      },
      {
        name: "addNotes",
        description: "Create many notes in a deck",
        inputSchema: {
          type: "object",
          properties: {
            notes: {
              type: "array",
              description: "Notes to create",
              items: noteParameters,
            },
          },
        },
      },
    ],
  };
});

/**
 * Handler for the create_note tool.
 * Creates a new note with the provided title and content, and returns success message.
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch (request.params.name) {
    case "listDecks":
      const decks = await ankiRequest<string[]>("deckNames");

      return {
        toolResult: `Here is a list of the decks in the user's Anki collection: ${decks.join(", ")}`,
      };
    case "listModels":
      const models = await ankiRequest<string[]>("modelNames");

      return {
        toolResult: `Here is the list of note models in the user's Anki collection: ${models}`,
      };
    case "getModel":
      if (!request.params.arguments) {
        throw new Error("getModel requires a model name");
      }

      const modelNames = [request.params.arguments.modelName];

      const model = await ankiRequest<string[]>("findModelsByName", {
        modelNames,
      });

      return {
        toolResult: `Here is the ${request.params.arguments.modelName} in the user's Anki collection: ${JSON.stringify(model)}`,
      };
    case "addNotes":
      const createdNoteIds = await ankiRequest<number[]>(
        "addNotes",
        request.params.arguments,
      );
      return {
        toolResult: `Created notes with the following IDs: ${createdNoteIds.join(", ")}`,
      };
    case "addNote":
      const createdNoteId = await ankiRequest<number>(
        "addNote",
        { note: request.params.arguments },
      );
      return {
        toolResult: `Created note with the following ID: ${createdNoteId}`,
      };

    default:
      throw new Error("Unknown tool");
  }
});

/**
 * Start the server using stdio transport.
 * This allows the server to communicate via standard input/output streams.
 */
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
