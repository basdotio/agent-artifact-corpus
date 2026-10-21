import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
  type CallToolRequest,
} from '@modelcontextprotocol/sdk/types.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { createLightdashClient } from 'lightdash-client-typescript-fetch';
import { zodToJsonSchema } from 'zod-to-json-schema';
import {
  ListProjectsRequestSchema,
  GetProjectRequestSchema,
  ListSpacesRequestSchema,
  ListChartsRequestSchema,
  ListDashboardsRequestSchema,
  GetCustomMetricsRequestSchema,
  GetCatalogRequestSchema,
  GetMetricsCatalogRequestSchema,
  GetChartsAsCodeRequestSchema,
  GetDashboardsAsCodeRequestSchema,
  GetMetadataRequestSchema,
  GetAnalyticsRequestSchema,
  GetUserAttributesRequestSchema,
} from './schemas.js';

const lightdashClient = createLightdashClient(
  process.env.LIGHTDASH_API_URL || 'https://app.lightdash.cloud',
  {
    headers: {
      Authorization: `ApiKey ${process.env.LIGHTDASH_API_KEY}`,
    },
  }
);

export const server = new Server(
  {
    name: 'lightdash-mcp-server',
    version: '0.0.1',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'lightdash_list_projects',
        description: 'List all projects in the Lightdash organization',
        inputSchema: zodToJsonSchema(ListProjectsRequestSchema),
      },
      {
        name: 'lightdash_get_project',
        description: 'Get details of a specific project',
        inputSchema: zodToJsonSchema(GetProjectRequestSchema),
      },
      {
        name: 'lightdash_list_spaces',
        description: 'List all spaces in a project',
        inputSchema: zodToJsonSchema(ListSpacesRequestSchema),
      },
      {
        name: 'lightdash_list_charts',
        description: 'List all charts in a project',
        inputSchema: zodToJsonSchema(ListChartsRequestSchema),
      },
      {
        name: 'lightdash_list_dashboards',
        description: 'List all dashboards in a project',
        inputSchema: zodToJsonSchema(ListDashboardsRequestSchema),
      },
      {
        name: 'lightdash_get_custom_metrics',
        description: 'Get custom metrics for a project',
        inputSchema: zodToJsonSchema(GetCustomMetricsRequestSchema),
      },
      {
        name: 'lightdash_get_catalog',
        description: 'Get catalog for a project',
        inputSchema: zodToJsonSchema(GetCatalogRequestSchema),
      },
      {
        name: 'lightdash_get_metrics_catalog',
        description: 'Get metrics catalog for a project',
        inputSchema: zodToJsonSchema(GetMetricsCatalogRequestSchema),
      },
      {
        name: 'lightdash_get_charts_as_code',
        description: 'Get charts as code for a project',
        inputSchema: zodToJsonSchema(GetChartsAsCodeRequestSchema),
      },
      {
        name: 'lightdash_get_dashboards_as_code',
        description: 'Get dashboards as code for a project',
        inputSchema: zodToJsonSchema(GetDashboardsAsCodeRequestSchema),
      },
      {
        name: 'lightdash_get_metadata',
        description: 'Get metadata for a specific table in the data catalog',
        inputSchema: zodToJsonSchema(GetMetadataRequestSchema),
      },
      {
        name: 'lightdash_get_analytics',
        description: 'Get analytics for a specific table in the data catalog',
        inputSchema: zodToJsonSchema(GetAnalyticsRequestSchema),
      },
      {
        name: 'lightdash_get_user_attributes',
        description: 'Get organization user attributes',
        inputSchema: zodToJsonSchema(GetUserAttributesRequestSchema),
      },
    ],
  };
});

server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest) => {
    try {
      if (!request.params) {
        throw new Error('Params are required');
      }

      switch (request.params.name) {
        case 'lightdash_list_projects': {
          const { data, error } = await lightdashClient.GET(
            '/api/v1/org/projects',
            {}
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_project': {
          const args = GetProjectRequestSchema.parse(request.params.arguments);
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_list_spaces': {
          const args = ListSpacesRequestSchema.parse(request.params.arguments);
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/spaces',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_list_charts': {
          const args = ListChartsRequestSchema.parse(request.params.arguments);
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/charts',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_list_dashboards': {
          const args = ListDashboardsRequestSchema.parse(
            request.params.arguments
          );
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/dashboards',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_custom_metrics': {
          const args = GetCustomMetricsRequestSchema.parse(
            request.params.arguments
          );
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/custom-metrics',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_catalog': {
          const args = GetCatalogRequestSchema.parse(request.params.arguments);
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/dataCatalog',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_metrics_catalog': {
          const args = GetMetricsCatalogRequestSchema.parse(
            request.params.arguments
          );
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/dataCatalog/metrics',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_charts_as_code': {
          const args = GetChartsAsCodeRequestSchema.parse(
            request.params.arguments
          );
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/charts/code',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_dashboards_as_code': {
          const args = GetDashboardsAsCodeRequestSchema.parse(
            request.params.arguments
          );
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/dashboards/code',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_metadata': {
          const args = GetMetadataRequestSchema.parse(request.params.arguments);
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/dataCatalog/{table}/metadata',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                  table: args.table,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_analytics': {
          const args = GetAnalyticsRequestSchema.parse(
            request.params.arguments
          );
          const { data, error } = await lightdashClient.GET(
            '/api/v1/projects/{projectUuid}/dataCatalog/{table}/analytics',
            {
              params: {
                path: {
                  projectUuid: args.projectUuid,
                  table: args.table,
                },
              },
            }
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        case 'lightdash_get_user_attributes': {
          const { data, error } = await lightdashClient.GET(
            '/api/v1/org/attributes',
            {}
          );
          if (error) {
            throw new Error(
              `Lightdash API error: ${error.error.name}, ${
                error.error.message ?? 'no message'
              }`
            );
          }
          return {
            content: [
              {
                type: 'text',
                text: JSON.stringify(data.results, null, 2),
              },
            ],
          };
        }
        default:
          throw new Error(`Unknown tool: ${request.params.name}`);
      }
    } catch (error) {
      console.error('Error handling request:', error);
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error occurred';
      throw new Error(errorMessage);
    }
  }
);
