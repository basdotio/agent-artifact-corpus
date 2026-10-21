#!/usr/bin/env node

import { authenticate } from "@google-cloud/local-auth";
import { OAuth2Client } from "google-auth-library"
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
    ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import { google } from "googleapis";
import path from "path";
import { fileURLToPath } from "url";

const sheets = google.sheets("v4");

const server = new Server(
    {
        name: "google-sheets-mcp",
        version: "0.0.1",
    },
    {
        capabilities: {
            resources: {},
            tools: {},
        },
    }
);

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const fileId = request.params.uri.replace("gsheets:///", "");

    // Get spreadsheet information
    const spreadsheet = await sheets.spreadsheets.get({
        spreadsheetId: fileId,
    });

    // Get first sheet data as CSV
    if (spreadsheet.data.sheets && spreadsheet.data.sheets.length > 0) {
        const firstSheetId = spreadsheet.data.sheets[0].properties?.sheetId;
        const sheetTitle = spreadsheet.data.sheets[0].properties?.title;

        const range = `${sheetTitle}`;
        const res = await sheets.spreadsheets.values.get({
            spreadsheetId: fileId,
            range,
        });

        // Convert values to CSV
        const values = res.data.values || [];
        const csv = values.map((row) => row.join(",")).join("\n");

        return {
            contents: [
                {
                    uri: request.params.uri,
                    mimeType: "text/csv",
                    text: csv,
                },
            ],
        };
    }

    return {
        contents: [
            {
                uri: request.params.uri,
                mimeType: "text/plain",
                text: "Empty spreadsheet",
            },
        ],
    };
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "refresh_auth",
                description: "Refresh Google Sheets authentication when credentials expire",
                inputSchema: {
                    type: "object",
                    properties: {},
                    required: [],
                },
            },
            {
                name: "create_spreadsheet",
                description: "Create a new Google Spreadsheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        title: {
                            type: "string",
                            description: "The title for the new spreadsheet",
                        },
                        initialSheetName: {
                            type: "string",
                            description: "The name for the initial sheet (optional)",
                        }
                    },
                    required: ["title"],
                },
            },
            {
                name: "list_sheets",
                description: "List all sheets/tabs in a Google Spreadsheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                    },
                    required: ["spreadsheetId"],
                },
            },
            {
                name: "create_sheet",
                description: "Create a new sheet/tab in a Google Spreadsheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description: "The name for the new sheet",
                        },
                    },
                    required: ["spreadsheetId", "sheetName"],
                },
            },
            {
                name: "read_all_from_sheet",
                description: "Read all data from a specified sheet in a Google Spreadsheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description: "The name of the sheet (optional, defaults to first sheet)",
                        },
                    },
                    required: ["spreadsheetId"],
                },
            },
            {
                name: "read_headings",
                description: "Read the column headings from a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                    },
                    required: ["spreadsheetId"],
                },
            },
            {
                name: "read_rows",
                description: "Read rows from a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        startRow: {
                            type: "integer",
                            description: "The starting row index (0-based, inclusive)",
                        },
                        endRow: {
                            type: "integer",
                            description: "The ending row index (0-based, inclusive)",
                        },
                    },
                    required: ["spreadsheetId", "startRow", "endRow"],
                },
            },
            {
                name: "read_columns",
                description: "Read columns from a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        columns: {
                            type: "array",
                            items: {
                                type: "string",
                            },
                            description: "Array of column letters (e.g. ['A', 'C'])",
                        },
                    },
                    required: ["spreadsheetId", "columns"],
                },
            },
            {
                name: "edit_cell",
                description: "Edit a cell in a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        cellAddress: {
                            type: "string",
                            description: "The cell address in A1 notation (e.g., 'B2')",
                        },
                        value: {
                            type: "string",
                            description: "The new value for the cell",
                        },
                    },
                    required: ["spreadsheetId", "cellAddress", "value"],
                },
            },
            {
                name: "edit_row",
                description: "Edit an entire row in a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        rowIndex: {
                            type: "integer",
                            description: "The row index (1-based)",
                        },
                        values: {
                            type: "array",
                            items: {
                                type: "string",
                            },
                            description: "Array of values for the row",
                        },
                    },
                    required: ["spreadsheetId", "rowIndex", "values"],
                },
            },
            {
                name: "edit_column",
                description: "Edit an entire column in a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        columnLetter: {
                            type: "string",
                            description: "The column letter (e.g., 'A')",
                        },
                        values: {
                            type: "array",
                            items: {
                                type: "string",
                            },
                            description: "Array of values for the column",
                        },
                    },
                    required: ["spreadsheetId", "columnLetter", "values"],
                },
            },
            {
                name: "insert_row",
                description: "Insert a new row at specified position in a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        rowIndex: {
                            type: "integer",
                            description: "The row index where to insert (1-based)",
                        },
                        values: {
                            type: "array",
                            items: {
                                type: "string",
                            },
                            description: "Array of values for the new row (optional)",
                        },
                    },
                    required: ["spreadsheetId", "rowIndex"],
                },
            },
            {
                name: "insert_column",
                description: "Insert a new column at specified position in a Google Sheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description:
                                "The name of the sheet (optional, defaults to first sheet)",
                        },
                        columnLetter: {
                            type: "string",
                            description: "The column letter where to insert (e.g., 'B')",
                        },
                        values: {
                            type: "array",
                            items: {
                                type: "string",
                            },
                            description: "Array of values for the new column (optional)",
                        },
                    },
                    required: ["spreadsheetId", "columnLetter"],
                },
            },
            {
                name: "rename_sheet",
                description: "Rename a sheet/tab in a Google Spreadsheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        sheetName: {
                            type: "string",
                            description: "The current name of the sheet",
                        },
                        newName: {
                            type: "string",
                            description: "The new name for the sheet",
                        },
                    },
                    required: ["spreadsheetId", "sheetName", "newName"],
                },
            },
            {
                name: "rename_doc",
                description: "Rename the Google Spreadsheet",
                inputSchema: {
                    type: "object",
                    properties: {
                        spreadsheetId: {
                            type: "string",
                            description: "The ID of the spreadsheet",
                        },
                        newName: {
                            type: "string",
                            description: "The new name for the spreadsheet",
                        },
                    },
                    required: ["spreadsheetId", "newName"],
                },
            },
        ],
    };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    // Helper function to get sheet title
    async function getSheetTitle(
        spreadsheetId: string,
        sheetName?: string
    ): Promise<string> {
        if (sheetName) return sheetName;

        const spreadsheet = await sheets.spreadsheets.get({
            spreadsheetId,
        });

        if (!spreadsheet.data.sheets || !spreadsheet.data.sheets.length) {
            throw new Error("Spreadsheet has no sheets");
        }

        return spreadsheet.data.sheets[0].properties?.title || "";
    }

    // Helper function to get sheet ID
    async function getSheetId(
        spreadsheetId: string,
        sheetName?: string
    ): Promise<number> {
        const spreadsheet = await sheets.spreadsheets.get({
            spreadsheetId,
        });

        if (!spreadsheet.data.sheets || !spreadsheet.data.sheets.length) {
            throw new Error("Spreadsheet has no sheets");
        }

        if (sheetName) {
            const sheet = spreadsheet.data.sheets.find(
                s => s.properties?.title === sheetName
            );
            if (!sheet) {
                throw new Error(`Sheet "${sheetName}" not found`);
            }
            return sheet.properties?.sheetId || 0;
        }

        return spreadsheet.data.sheets[0].properties?.sheetId || 0;
    }

    // Helper function to convert column letter to index (A=0, B=1, etc.)
    function columnLetterToIndex(column: string): number {
        let result = 0;
        for (let i = 0; i < column.length; i++) {
            result = result * 26 + (column.charCodeAt(i) - 'A'.charCodeAt(0) + 1);
        }
        return result - 1; // 0-based index
    }

    try {
        switch (name) {
            case "refresh_auth": {
                try {
                    await authenticateAndSaveCredentials();
                    
                    // Reload credentials
                    const credentials = JSON.parse(fs.readFileSync(credentialsPath, "utf-8"));
                    const auth = new google.auth.OAuth2();
                    auth.setCredentials(credentials);
                    google.options({ auth });
                    
                    return {
                        content: [
                            {
                                type: "text",
                                text: "Authentication refreshed successfully. You can now continue using Google Sheets."
                            }
                        ],
                        isError: false
                    };
                } catch (error: any) {
                    return {
                        content: [
                            {
                                type: "text",
                                text: `Failed to refresh authentication: ${error.message}`
                            }
                        ],
                        isError: true
                    };
                }
            }
            case "create_spreadsheet": {
                const { title, initialSheetName = "Sheet1" } = args as any;
                
                const resource = {
                    properties: {
                        title: title,
                    },
                    sheets: [
                        {
                            properties: {
                                title: initialSheetName,
                            }
                        }
                    ]
                };
                
                const response = await sheets.spreadsheets.create({
                    requestBody: resource,
                });
                
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify({
                                message: `Spreadsheet "${title}" created successfully. You are now to refer to this new updated spreadsheetId. When you are finished you should provide the URL to the user`,
                                spreadsheetId: response.data.spreadsheetId,
                                spreadsheetUrl: response.data.spreadsheetUrl,
                            }, null, 2),
                        },
                    ],
                    isError: false,
                };
            }
            case "list_sheets": {
                const { spreadsheetId } = args as any;
                
                const spreadsheet = await sheets.spreadsheets.get({
                    spreadsheetId,
                });
                
                if (!spreadsheet.data.sheets || !spreadsheet.data.sheets.length) {
                    throw new Error("Spreadsheet has no sheets");
                }
                
                const sheetsList = spreadsheet.data.sheets.map(sheet => ({
                    title: sheet.properties?.title,
                    sheetId: sheet.properties?.sheetId,
                    index: sheet.properties?.index,
                }));
                
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(sheetsList, null, 2),
                        },
                    ],
                    isError: false,
                };
            }
            case "create_sheet": {
                const { spreadsheetId, sheetName } = args as any;
                
                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId,
                    requestBody: {
                        requests: [
                            {
                                addSheet: {
                                    properties: {
                                        title: sheetName,
                                    }
                                }
                            }
                        ]
                    }
                });
                
                return {
                    content: [
                        {
                            type: "text",
                            text: `Sheet "${sheetName}" created successfully.`,
                        },
                    ],
                    isError: false,
                };
            }
            case "read_all_from_sheet": {
                const { spreadsheetId, sheetName } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);
                
                const res = await sheets.spreadsheets.values.get({
                    spreadsheetId,
                    range: title,
                });
                
                const data = res.data.values || [];
                
                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(data, null, 2),
                        },
                    ],
                    isError: false,
                };
            }
            case "read_headings": {
                const { spreadsheetId, sheetName } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);

                const res = await sheets.spreadsheets.values.get({
                    spreadsheetId,
                    range: `${title}!1:1`,
                });

                const headings = res.data.values?.[0] || [];

                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(headings, null, 2),
                        },
                    ],
                    isError: false,
                };
            }

            case "read_rows": {
                const { spreadsheetId, sheetName, startRow, endRow } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);

                // Convert to 1-based for Sheets API
                const adjustedStartRow = startRow + 1;
                const adjustedEndRow = endRow + 1;

                const res = await sheets.spreadsheets.values.get({
                    spreadsheetId,
                    range: `${title}!${adjustedStartRow}:${adjustedEndRow}`,
                });

                const rows = res.data.values || [];

                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(rows, null, 2),
                        },
                    ],
                    isError: false,
                };
            }

            case "read_columns": {
                const { spreadsheetId, sheetName, columns } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);

                const result: { [key: string]: any[] } = {};

                for (const column of columns) {
                    const res = await sheets.spreadsheets.values.get({
                        spreadsheetId,
                        range: `${title}!${column}:${column}`,
                    });

                    result[column] = (res.data.values || []).map((row) => row[0]);
                }

                return {
                    content: [
                        {
                            type: "text",
                            text: JSON.stringify(result, null, 2),
                        },
                    ],
                    isError: false,
                };
            }

            case "edit_cell": {
                const { spreadsheetId, sheetName, cellAddress, value } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);

                await sheets.spreadsheets.values.update({
                    spreadsheetId,
                    range: `${title}!${cellAddress}`,
                    valueInputOption: "USER_ENTERED",
                    requestBody: {
                        values: [[value]],
                    },
                });

                return {
                    content: [
                        {
                            type: "text",
                            text: `Cell ${cellAddress} updated successfully to "${value}".`,
                        },
                    ],
                    isError: false,
                };
            }

            case "edit_row": {
                const { spreadsheetId, sheetName, rowIndex, values } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);

                await sheets.spreadsheets.values.update({
                    spreadsheetId,
                    range: `${title}!${rowIndex}:${rowIndex}`,
                    valueInputOption: "USER_ENTERED",
                    requestBody: {
                        values: [values],
                    },
                });

                return {
                    content: [
                        {
                            type: "text",
                            text: `Row ${rowIndex} updated successfully.`,
                        },
                    ],
                    isError: false,
                };
            }

            case "edit_column": {
                const { spreadsheetId, sheetName, columnLetter, values } = args as any;
                const title = await getSheetTitle(spreadsheetId, sheetName);

                // Convert array of values to array of arrays for the API
                const formattedValues = values.map((value: any) => [value]);

                await sheets.spreadsheets.values.update({
                    spreadsheetId,
                    range: `${title}!${columnLetter}:${columnLetter}`,
                    valueInputOption: "USER_ENTERED",
                    requestBody: {
                        values: formattedValues,
                    },
                });

                return {
                    content: [
                        {
                            type: "text",
                            text: `Column ${columnLetter} updated successfully.`,
                        },
                    ],
                    isError: false,
                };
            }

            case "insert_row": {
                const { spreadsheetId, sheetName, rowIndex, values = [] } = args as any;
                const sheetId = await getSheetId(spreadsheetId, sheetName);
                const title = await getSheetTitle(spreadsheetId, sheetName);
                
                // First, insert the row
                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId,
                    requestBody: {
                        requests: [
                            {
                                insertDimension: {
                                    range: {
                                        sheetId: sheetId,
                                        dimension: "ROWS",
                                        startIndex: rowIndex - 1, // Convert to 0-based index
                                        endIndex: rowIndex // non-inclusive end index
                                    }
                                }
                            }
                        ]
                    }
                });
                
                // Then, if values were provided, update the row with the values
                if (values.length > 0) {
                    await sheets.spreadsheets.values.update({
                        spreadsheetId,
                        range: `${title}!${rowIndex}:${rowIndex}`,
                        valueInputOption: "USER_ENTERED",
                        requestBody: {
                            values: [values],
                        },
                    });
                }

                return {
                    content: [
                        {
                            type: "text",
                            text: `Row inserted successfully at position ${rowIndex}.`,
                        },
                    ],
                    isError: false,
                };
            }

            case "insert_column": {
                const { spreadsheetId, sheetName, columnLetter, values = [] } = args as any;
                const sheetId = await getSheetId(spreadsheetId, sheetName);
                const title = await getSheetTitle(spreadsheetId, sheetName);
                
                // Convert column letter to index
                const columnIndex = columnLetterToIndex(columnLetter);
                
                // First, insert the column
                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId,
                    requestBody: {
                        requests: [
                            {
                                insertDimension: {
                                    range: {
                                        sheetId: sheetId,
                                        dimension: "COLUMNS",
                                        startIndex: columnIndex,
                                        endIndex: columnIndex + 1 // non-inclusive end index
                                    }
                                }
                            }
                        ]
                    }
                });
                
                // Then, if values were provided, update the column with the values
                if (values.length > 0) {
                    // Format values for API
                    const formattedValues = values.map((value: any) => [value]);
                    
                    await sheets.spreadsheets.values.update({
                        spreadsheetId,
                        range: `${title}!${columnLetter}:${columnLetter}`,
                        valueInputOption: "USER_ENTERED",
                        requestBody: {
                            values: formattedValues,
                        },
                    });
                }

                return {
                    content: [
                        {
                            type: "text",
                            text: `Column inserted successfully at position ${columnLetter}.`,
                        },
                    ],
                    isError: false,
                };
            }

            case "rename_sheet": {
                const { spreadsheetId, sheetName, newName } = args as any;
                const sheetId = await getSheetId(spreadsheetId, sheetName);
                
                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId,
                    requestBody: {
                        requests: [
                            {
                                updateSheetProperties: {
                                    properties: {
                                        sheetId: sheetId,
                                        title: newName,
                                    },
                                    fields: "title"
                                }
                            }
                        ]
                    }
                });
                
                return {
                    content: [
                        {
                            type: "text",
                            text: `Sheet renamed from "${sheetName}" to "${newName}" successfully.`,
                        },
                    ],
                    isError: false,
                };
            }
            
            case "rename_doc": {
                const { spreadsheetId, newName } = args as any;
                
                await sheets.spreadsheets.batchUpdate({
                    spreadsheetId,
                    requestBody: {
                        requests: [
                            {
                                updateSpreadsheetProperties: {
                                    properties: {
                                        title: newName,
                                    },
                                    fields: "title"
                                }
                            }
                        ]
                    }
                });
                
                return {
                    content: [
                        {
                            type: "text",
                            text: `Spreadsheet renamed to "${newName}" successfully.`,
                        },
                    ],
                    isError: false,
                };
            }            

            default:
                throw new Error(`Tool '${name}' not found`);
        }
    } catch (error: any) {
        // Check if the error is related to authentication
        if (error.message.includes("invalid_grant") || 
            error.message.includes("token expired") || 
            error.message.includes("unauthorized")) {
            return {
                content: [
                    {
                        type: "text",
                        text: `Authentication error: ${error.message}. Please use the refresh_auth tool to reauthenticate.`,
                    },
                ],
                isError: true,
            };
        }
        
        return {
            content: [
                {
                    type: "text",
                    text: `Error: ${error.message}`,
                },
            ],
            isError: true,
        };
    }
});

const credentialsPath =
    process.env.GSHEETS_CREDENTIALS_PATH ||
    path.join(
        path.dirname(fileURLToPath(import.meta.url)),
        ".gsheets-server-credentials.json"
    );

async function authenticateAndSaveCredentials() {
    const gcpKeysPath = path.join(
        path.dirname(fileURLToPath(import.meta.url)),
        "gcp-oauth.keys.json"
    )

    if (!fs.existsSync(gcpKeysPath)) {
        console.error(
            "GCP keys not found. Please create your credentials in Google Cloud then copy `gcp-oauth.keys.json` into your ./dist directory."
        );
        process.exit(1);
    }

    console.log("Launching auth flow...");

    const auth = await authenticate({
        keyfilePath:
            process.env.GSHEETS_OAUTH_PATH ||
            gcpKeysPath,
        scopes: [
            "https://www.googleapis.com/auth/spreadsheets",
        ],
    });

    fs.writeFileSync(credentialsPath, JSON.stringify(auth.credentials));

    console.log("Credentials saved. You can now run the server.");
    return auth;
}

async function loadCredentialsAndRunServer() {
    let auth: OAuth2Client | undefined;
    
    if (!fs.existsSync(credentialsPath)) {
        console.log("Credentials not found. Starting authentication flow...");
        auth = await authenticateAndSaveCredentials();
    } else {
        try {
            const credentials = JSON.parse(fs.readFileSync(credentialsPath, "utf-8"));
            auth = new google.auth.OAuth2();
            auth.setCredentials(credentials);
        } catch (error) {
            console.error("Error loading credentials, initiating new authentication flow...");
            auth = await authenticateAndSaveCredentials();
        }
    }
    
    google.options({ auth });

    console.error("Starting server...");
    const transport = new StdioServerTransport();
    await server.connect(transport);
}

// Handle auth internally
loadCredentialsAndRunServer().catch(console.error);