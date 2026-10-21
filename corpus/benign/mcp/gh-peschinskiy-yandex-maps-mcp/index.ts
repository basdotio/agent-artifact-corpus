#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";
import fetch from "node-fetch";
import { createServer, IncomingMessage, ServerResponse } from "http";

// Response interfaces
interface YandexMapsResponse {
  status: string;
  error_message?: string;
}

interface GeocodeResponse extends YandexMapsResponse {
  response: {
    GeoObjectCollection: {
      metaDataProperty: {
        GeocoderResponseMetaData: {
          request: string;
          results: string;
          found: string;
        };
      };
      featureMember: Array<{
        GeoObject: {
          metaDataProperty: {
            GeocoderMetaData: {
              precision: string;
              text: string;
              kind: string;
              Address: {
                country_code: string;
                formatted: string;
                Components: Array<{
                  kind: string;
                  name: string;
                }>;
              };
              AddressDetails: {
                Country: {
                  AddressLine: string;
                  CountryNameCode: string;
                  CountryName: string;
                  AdministrativeArea?: {
                    AdministrativeAreaName: string;
                    Locality?: {
                      LocalityName: string;
                      Thoroughfare?: {
                        ThoroughfareName: string;
                        Premise?: {
                          PremiseNumber: string;
                        };
                      };
                    };
                  };
                };
              };
            };
          };
          description: string;
          name: string;
          boundedBy: {
            Envelope: {
              lowerCorner: string;
              upperCorner: string;
            };
          };
          Point: {
            pos: string;
          };
        };
      }>;
    };
  };
}

function getApiKey(): string {
    const apiKey = process.env.YANDEX_MAPS_API_KEY;
    if (!apiKey) {
      console.error("YANDEX_MAPS_API_KEY environment variable is not set");
      process.exit(1);
    }
    return apiKey;
}

function getStaticApiKey(): string {
  const apiKey = process.env.YANDEX_MAPS_STATIC_API_KEY;
  if (!apiKey) {
    console.error("YANDEX_MAPS_STATIC_API_KEY environment variable is not set");
    process.exit(1);
  }
  return apiKey;
}

const YANDEX_MAPS_API_KEY = getApiKey();
const YANDEX_MAPS_STATIC_API_KEY = getStaticApiKey();

// Tool definitions
const GEOCODE_TOOL: Tool = {
  name: "maps_geocode",
  description: "Convert an address into geographic coordinates using individual address components",
  inputSchema: {
    type: "object",
    properties: {
      country: {
        type: "string",
        description: "The country name"
      },
      state: {
        type: "string",
        description: "The state, region or province name"
      },
      city: {
        type: "string",
        description: "The city or locality name"
      },
      district: {
        type: "string",
        description: "The district or neighborhood within the city"
      },
      street: {
        type: "string",
        description: "The street name"
      },
      house_number: {
        type: "string",
        description: "The house or building number"
      },
      lang: {
        type: "string",
        description: "Language code, e.g. 'ru_RU', 'en_US'"
      }
    },
    required: ["country", "lang"]
  }
};

const REVERSE_GEOCODE_TOOL: Tool = {
  name: "maps_reverse_geocode",
  description: "Convert coordinates into an address",
  inputSchema: {
    type: "object",
    properties: {
      latitude: {
        type: "number",
        description: "Latitude coordinate"
      },
      longitude: {
        type: "number",
        description: "Longitude coordinate"
      },
      lang: {
        type: "string",
        description: "Language code, e.g. 'ru_RU', 'en_US'"
      }
    },
    required: ["latitude", "longitude", "lang"]
  }
};

const RENDER_MAP_TOOL: Tool = {
  name: "maps_render",
  description: "Render a map as a png image",
  inputSchema: {
    type: "object",
    properties: {
      latitude: {
        type: "number",
        description: "Latitude coordinate of map center"
      },
      longitude: {
        type: "number",
        description: "Longitude coordinate of map center"
      },
      latitude_span: {
        type: "number",
        description: "Height of map image in degrees"
      },
      longitude_span: {
        type: "number",
        description: "Width of map image in degrees"
      },
      lang: {
        type: "string",
        description: "Language code, e.g. 'ru_RU', 'en_US'"
      },
      placemarks: {
        type: "array",
        description: "Array of placemarks to display on the map",
        items: {
          type: "object",
          properties: {
            latitude: {
              type: "number",
              description: "Latitude coordinate of the placemark"
            },
            longitude: {
              type: "number",
              description: "Longitude coordinate of the placemark"
            }
          },
          required: ["latitude", "longitude"]
        }
      }
    },
    required: ["latitude", "longitude", "latitude_span", "longitude_span", "lang"]
  }
}

const MAPS_TOOLS = [
  GEOCODE_TOOL,
  REVERSE_GEOCODE_TOOL,
  RENDER_MAP_TOOL,
] as const;

const YANDEX_MAPS_GEOCODER_BASE_URL = "https://geocode-maps.yandex.ru/1.x/";
const YANDEX_MAPS_STATIC_BASE_URL = "https://static-maps.yandex.ru/v1";

// API handlers
async function handleGeocode(country: string, lang: string, state?: string, city?: string, district?: string, street?: string, house_number?: string) {
  // Combine the address components into a single string, filtering out undefined values
  const addressParts = [
    house_number,
    street,
    district,
    city,
    state,
    country
  ].filter(part => part !== undefined && part !== '');
  
  const address = addressParts.join(', ');

  const url = new URL(YANDEX_MAPS_GEOCODER_BASE_URL);
  url.searchParams.append("geocode", address);
  url.searchParams.append("format", "json");
  url.searchParams.append("results", "1");
  url.searchParams.append("lang", lang);
  url.searchParams.append("apikey", YANDEX_MAPS_API_KEY);

  const response = await fetch(url.toString());
  const data = await response.json() as GeocodeResponse;

  // Check for API errors
  if ('error' in data) {
    return {
      content: [{
        type: "text",
        text: `Geocoding failed: ${(data as any).message || 'Unknown error'}`
      }],
      isError: true
    };
  }

  if (!data.response || data.response.GeoObjectCollection.featureMember.length === 0) {
    return {
      content: [{
        type: "text",
        text: `Geocoding failed: No results found`
      }],
      isError: true
    };
  }

  const geoObject = data.response.GeoObjectCollection.featureMember[0].GeoObject;
  const point = geoObject.Point?.pos.split(' ').map(Number); // Format: "longitude latitude"
  
  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        location: point ? { lng: point[0], lat: point[1] } : null,
        formatted_address: geoObject.metaDataProperty.GeocoderMetaData.text,
        address_components: geoObject.metaDataProperty.GeocoderMetaData.Address.Components
      }, null, 2)
    }],
    isError: false
  };
}

async function handleReverseGeocode(latitude: number, longitude: number, lang: string) {
  const url = new URL(YANDEX_MAPS_GEOCODER_BASE_URL);
  url.searchParams.append("geocode", `${longitude},${latitude}`);
  url.searchParams.append("format", "json");
  url.searchParams.append("results", "1");
  url.searchParams.append("lang", lang);
  url.searchParams.append("apikey", YANDEX_MAPS_API_KEY);

  const response = await fetch(url.toString());
  const data = await response.json() as GeocodeResponse;

  // Check for API errors
  if ('error' in data) {
    return {
      content: [{
        type: "text",
        text: `Reverse geocoding failed: ${(data as any).message || 'Unknown error'}`
      }],
      isError: true
    };
  }

  if (!data.response || data.response.GeoObjectCollection.featureMember.length === 0) {
    return {
      content: [{
        type: "text",
        text: `Reverse geocoding failed: No results found`
      }],
      isError: true
    };
  }

  const geoObject = data.response.GeoObjectCollection.featureMember[0].GeoObject;
  const point = geoObject.Point?.pos.split(' ').map(Number); // Format: "longitude latitude"
  
  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        location: point ? { lng: point[0], lat: point[1] } : null,
        formatted_address: geoObject.metaDataProperty.GeocoderMetaData.text,
        address_components: geoObject.metaDataProperty.GeocoderMetaData.Address.Components
      }, null, 2)
    }],
    isError: false
  };
}

async function handleRenderMap(
  latitude: number,
  longitude: number,
  latitude_span: number,
  longitude_span: number,
  lang: string,
  placemarks?: Array<{ latitude: number, longitude: number }>
) {
  // Calculate bounds based on center and span
  const ll = `${longitude},${latitude}`; // Center point (lon,lat)
  const spn = `${longitude_span},${latitude_span}`; // Span (lon_span,lat_span)

  const url = new URL(YANDEX_MAPS_STATIC_BASE_URL);
  url.searchParams.append("ll", ll);
  url.searchParams.append("spn", spn);
  url.searchParams.append("l", "map"); // Default layer type
  url.searchParams.append("lang", lang);
  url.searchParams.append("apikey", YANDEX_MAPS_STATIC_API_KEY);
  
  // Add placemarks if provided
  if (placemarks && placemarks.length > 0) {
    // Format: pt=lon1,lat1,pm2rdm~lon2,lat2,pm2rdm~...
    const placemarksParam = placemarks
      .map(mark => `${mark.longitude},${mark.latitude},pm2rdm`)
      .join('~');
    
    url.searchParams.append("pt", placemarksParam);
  }

  try {
    // Fetch the actual image data
    const response = await fetch(url.toString());
    
    if (!response.ok) {
      const errorText = await response.text();
      return {
        content: [{
          type: "text",
          text: `Failed to fetch map image: ${response.status} ${response.statusText}\n${errorText}`
        }],
        isError: true
      };
    }
    
    // Get the image as buffer
    const arrayBuffer = await response.arrayBuffer();
    const imageBuffer = Buffer.from(arrayBuffer);
    
    // Convert to base64 for transmission
    const base64Data = imageBuffer.toString('base64');
    const contentType = response.headers.get('content-type') || 'image/png';
    
    // Return as proper MCP image content
    return {
      content: [{
        type: "image",
        data: base64Data,
        mimeType: contentType
      }],
      isError: false
    };
  } catch (error) {
    return {
      content: [{
        type: "text",
        text: `Error rendering map: ${error instanceof Error ? error.message : String(error)}`
      }],
      isError: true
    };
  }
}

// Server setup
function createMCPServer() {
  const server = new Server(
    {
      name: "mcp-server/yandex-maps",
      version: "0.1.0",
    },
    {
      capabilities: {
        tools: {},
      },
    },
  );

  // Set up request handlers
  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: MAPS_TOOLS,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    try {
      switch (request.params.name) {
        case "maps_geocode": {
          const { country, lang, state, city, district, street, house_number } = request.params.arguments as {
            country: string;
            lang: string;
            state?: string;
            city?: string;
            district?: string;
            street?: string;
            house_number?: string;
          };
          return await handleGeocode(country, lang, state, city, district, street, house_number);
        }

        case "maps_reverse_geocode": {
          const { latitude, longitude, lang } = request.params.arguments as {
            latitude: number;
            longitude: number;
            lang: string;
          };
          return await handleReverseGeocode(latitude, longitude, lang);
        }

        case "maps_render": {
          const { latitude, longitude, latitude_span, longitude_span, lang, placemarks } = request.params.arguments as {
            latitude: number;
            longitude: number;
            latitude_span: number;
            longitude_span: number;
            lang: string;
            placemarks?: Array<{ latitude: number, longitude: number }>;
          };
          return await handleRenderMap(latitude, longitude, latitude_span, longitude_span, lang, placemarks);
        }

        default:
          return {
            content: [{
              type: "text",
              text: `Unknown tool: ${request.params.name}`
            }],
            isError: true
          };
      }
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  });

  return server;
}

// Authentication helper for HTTP mode
function authenticateRequest(req: IncomingMessage): boolean {
  const authToken = process.env.MCP_AUTH_TOKEN;

  // If no auth token is configured, allow all requests
  if (!authToken) {
    return true;
  }

  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return false;
  }

  // Support Bearer token format
  const token = authHeader.startsWith('Bearer ')
    ? authHeader.slice(7)
    : authHeader;

  return token === authToken;
}

// HTTP request handler
async function handleHTTPRequest(req: IncomingMessage, res: ServerResponse) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    res.writeHead(405, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      jsonrpc: '2.0',
      error: {
        code: -32000,
        message: 'Method not allowed. Use POST.'
      },
      id: null
    }));
    return;
  }

  // Authenticate request
  if (!authenticateRequest(req)) {
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      jsonrpc: '2.0',
      error: {
        code: -32000,
        message: 'Unauthorized. Valid Bearer token required.'
      },
      id: null
    }));
    return;
  }

  // Read request body
  let body = '';
  req.on('data', chunk => {
    body += chunk.toString();
  });

  req.on('end', async () => {
    try {
      const parsedBody = JSON.parse(body);

      // Create fresh server and transport instances for stateless operation
      const server = createMCPServer();
      const transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: undefined, // Stateless mode
      });

      await server.connect(transport);
      await transport.handleRequest(req, res, parsedBody);

      // Clean up on request close
      res.on('close', () => {
        transport.close();
        server.close();
      });
    } catch (error) {
      console.error('Error handling MCP request:', error);
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          jsonrpc: '2.0',
          error: {
            code: -32603,
            message: 'Internal server error'
          },
          id: null
        }));
      }
    }
  });
}

// Run HTTP server
async function runHTTPServer() {
  const port = parseInt(process.env.MCP_PORT || '3000', 10);
  const server = createServer(handleHTTPRequest);

  server.listen(port, () => {
    console.error(`Yandex Maps MCP Server running on HTTP port ${port}`);
    if (process.env.MCP_AUTH_TOKEN) {
      console.error('Authentication enabled');
    } else {
      console.error('WARNING: No authentication token set. Set MCP_AUTH_TOKEN for production use.');
    }
  });

  // Handle graceful shutdown
  process.on('SIGINT', async () => {
    console.error('Shutting down HTTP server...');
    server.close();
    process.exit(0);
  });
}

// Run stdio server
async function runStdioServer() {
  const server = createMCPServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Yandex Maps MCP Server running on stdio");
}

// Main entry point
async function main() {
  const transportMode = process.env.MCP_TRANSPORT || 'stdio';

  if (transportMode === 'http') {
    await runHTTPServer();
  } else if (transportMode === 'stdio') {
    await runStdioServer();
  } else {
    console.error(`Unknown transport mode: ${transportMode}. Use 'stdio' or 'http'.`);
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});