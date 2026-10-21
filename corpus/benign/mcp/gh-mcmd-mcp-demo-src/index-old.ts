import { createServer, IncomingMessage, ServerResponse } from 'http';
//import { sendAnalyticsPing } from './analytics';

// MCP Tool Definition
interface Tool {
  name: string;
  description: string;
  inputSchema: any; // Using 'any' for simplicity, should be a JSON Schema object
  run: (args: any) => Promise<any>;
}

// Our list of available tools
const tools: Tool[] = [
  {
    name: 'getCurrentWeather',
    description: 'Get the current weather for a given city.',
    inputSchema: {
      type: 'object',
      properties: {
        city: {
          type: 'string',
          description: 'The city to get the current weather for.',
        },
      },
      required: ['city'],
    },
    run: async (args: { city: string }) => {
      // Placeholder for actual weather data retrieval logic
      console.log(`Fetching current weather for ${args.city}...`);
      return {
        content: [
          {
            type: 'text',
            text: `Current weather in ${args.city}: 25°C, Sunny`,
          },
        ],
      };
    },
  },
  {
    name: 'get7DayForecast',
    description: 'Get the 7-day weather forecast for a given city.',
    inputSchema: {
        type: 'object',
        properties: {
            city: {
                type: 'string',
                description: 'The city to get the 7-day forecast for.',
            },
        },
        required: ['city'],
    },
    run: async (args: { city: string }) => {
      // Placeholder for actual forecast data retrieval logic
      console.log(`Fetching 7-day forecast for ${args.city}...`);
      return {
        content: [
            {
                type: 'text',
                text: '7-day forecast for ' + args.city + ': ...'
            }
        ]
      }
    },
  },
];

// JSON-RPC 2.0 Request Body
interface JsonRpcRequest {
    jsonrpc: string;
    id: number | string | null;
    method: string;
    params?: any;
}

const handleJsonRpcRequest = async (req: IncomingMessage, res: ServerResponse, body: string) => {
    try {
        const jsonRpcRequest: JsonRpcRequest = JSON.parse(body);
        const { id, method, params } = jsonRpcRequest;

        let result: any;
        let error: any;

        switch (method) {
            case 'initialize':
                result = {
                    protocolVersion: '2025-06-18',
                    capabilities: {
                        tools: {},
                    },
                    serverInfo: {
                        name: 'mcp-weather-server',
                        version: '1.0.0',
                    },
                };
                break;

            case 'tools/list':
                result = {
                    tools: tools.map(({ name, description, inputSchema }) => ({
                        name,
                        description,
                        inputSchema,
                    })),
                };
                break;

            case 'tools/call':
                const tool = tools.find(t => t.name === params.name);
                if (tool) {
                    //sendAnalyticsPing(tool.name);
                    result = await tool.run(params.arguments);
                } else {
                    error = { code: -32601, message: 'Method not found' };
                }
                break;

            default:
                error = { code: -32601, message: 'Method not found' };
        }

        const jsonRpcResponse = {
            jsonrpc: '2.0',
            id,
            result,
            error
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(jsonRpcResponse));

    } catch (e) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            jsonrpc: '2.0',
            id: null,
            error: { code: -32700, message: 'Parse error' }
        }));
    }
}

const server = createServer((req, res) => {
    if (req.method === 'POST') {
        let body = '';
        req.on('data', chunk => {
            body += chunk.toString();
        });
        req.on('end', () => {
            handleJsonRpcRequest(req, res, body);
        });
    } else {
        res.writeHead(405, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Method Not Allowed' }));
    }
});

const port = 3000;
server.listen(port, () => {
  console.log(`MCP server listening on port ${port}`);
});
