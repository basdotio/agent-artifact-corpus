import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { any, z } from "zod";
import * as YAML from "yaml";
import { getAuth } from "firebase-admin/auth";

import {
  PortalService,
  type Error,
  type ApiHubApi,
  type ApiHubApiVersion,
  type ApiHubApiVersionSpecContents,
} from "apigee-portal-module";

export class McpUserService {
  portalService: PortalService;
  dataCache: {
    apis: ApiHubApi[];
    versions: { [key: string]: ApiHubApiVersion };
    deployments: any;
    specs: any;
  } = {
    apis: [],
    versions: {},
    deployments: {},
    specs: {},
  };

  constructor(service: PortalService) {
    this.portalService = service;
  }

  // Map to store transports by session ID
  public transports: { [sessionId: string]: StreamableHTTPServerTransport } =
    {};

  public updateCache(newCache: {
    apis: ApiHubApi[];
    versions: { [key: string]: ApiHubApiVersion };
    deployments: any;
    specs: any;
  }) {
    this.dataCache = newCache;
  }

  public handleSessionRequest = async (
    req: express.Request,
    res: express.Response,
  ) => {
    const sessionId = req.headers["mcp-session-id"] as string | undefined;
    if (!sessionId || !this.transports[sessionId]) {
      res.status(400).send("Invalid or missing session ID");
      return;
    }

    const transport = this.transports[sessionId];
    await transport.handleRequest(req, res);
  };

  public mcppost = async (req: express.Request, res: express.Response) => {
    // Check for existing session ID
    const sessionId = req.headers["mcp-session-id"] as string | undefined;

    let transport: StreamableHTTPServerTransport;

    if (sessionId && this.transports[sessionId]) {
      // Reuse existing transport
      transport = this.transports[sessionId];
    } else if (!sessionId && isInitializeRequest(req.body)) {
      // New initialization request
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        onsessioninitialized: (sessionId) => {
          // Store the transport by session ID
          this.transports[sessionId] = transport;
        },
        // DNS rebinding protection is disabled by default for backwards compatibility. If you are running this server
        // locally, make sure to set:
        enableDnsRebindingProtection: false,
        allowedHosts: ["127.0.0.1", "localhost:8080", "*"],
      });

      // Clean up transport when closed
      transport.onclose = () => {
        if (transport.sessionId) {
          delete this.transports[transport.sessionId];
        }
      };
      const server = new McpServer({
        name: "apigee-user",
        version: "3.0.5",
      });

      // appsList
      server.registerTool(
        "appsList",
        {
          title: "App Subscriptions List Tool",
          description: "Lists all subscriptions to API products.",
          inputSchema: {
            email: z.string().describe("The email address of the user."),
          },
        },
        async ({ email }) => {
          let userEmail = email;
          // try {
          //   const userInfo = await getAuth().verifyIdToken(token);
          //   console.log(userInfo);
          //   if (userInfo) userEmail = userInfo.email ?? "";
          // } catch (e) {
          //   console.error("Could not verify user id token.");
          //   return {
          //     content: [
          //       {
          //         type: "text",
          //         text: `Could not verify the user.`,
          //       },
          //     ],
          //   };
          // }
          if (!userEmail) {
            console.error("User email could not be found.");
            return {
              content: [
                {
                  type: "text",
                  text: `Could not find the user.`,
                },
              ],
            };
          } else {
            let appsResponse = await this.portalService.getApps(userEmail);
            if (appsResponse && appsResponse.data) {
              return {
                content: [
                  {
                    type: "text",
                    text: `${JSON.stringify(appsResponse.data)}`,
                  },
                ],
              };
            } else {
              return {
                content: [
                  {
                    type: "text",
                    text: `No apps found.`,
                  },
                ],
              };
            }
          }
        },
      );

      // Connect to the MCP server
      await server.connect(transport);
    } else {
      // Invalid request
      res.status(400).json({
        jsonrpc: "2.0",
        error: {
          code: -32000,
          message: "Bad Request: No valid session ID provided",
        },
        id: null,
      });

      return;
    }

    // Handle the request
    await transport.handleRequest(req, res, req.body);
  };
}
