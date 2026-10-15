#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import axios, { AxiosResponse } from 'axios';
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Configuration
const ITOP_BASE_URL = process.env.ITOP_BASE_URL || '';
const ITOP_USER = process.env.ITOP_USER || '';
const ITOP_PASSWORD = process.env.ITOP_PASSWORD || '';
const ITOP_VERSION = process.env.ITOP_VERSION || '1.4';

// Support ticket field configuration
const SUPPORT_TICKET_FIELDS = {
  UserRequest: {
    defaultFields: 'ref,title,status,start_date,close_date,sla_tto_passed,sla_ttr_passed',
    priorityFields: ['ref', 'title', 'status', 'org_name', 'caller_name', 'agent_name'],
    slaFields: ['sla_tto_passed', 'sla_ttr_passed', 'sla_tto_deadline', 'sla_ttr_deadline'],
    timeFields: ['start_date', 'close_date', 'last_update', 'creation_date'],
  },
  Incident: {
    defaultFields: 'ref,title,status,start_date,close_date,sla_tto_passed,sla_ttr_passed,priority,impact,urgency',
    priorityFields: ['ref', 'title', 'status', 'priority', 'impact', 'urgency'],
    slaFields: ['sla_tto_passed', 'sla_ttr_passed', 'sla_tto_deadline', 'sla_ttr_deadline'],
    timeFields: ['start_date', 'close_date', 'last_update', 'creation_date'],
  },
};

interface ITopResponse {
  code: number;
  message?: string;
  objects?: Record<string, any>;
  operations?: Array<{ verb: string; description: string }>;
}

interface ITopClient {
  makeRequest(operationData: Record<string, any>): Promise<ITopResponse>;
}

class ITopClientImpl implements ITopClient {
  private baseUrl: string;
  private username: string;
  private password: string;
  private version: string;
  private restUrl: string;

  constructor(baseUrl: string, username: string, password: string, version: string = '1.4') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.username = username;
    this.password = password;
    this.version = version;
    this.restUrl = `${this.baseUrl}/webservices/rest.php`;
  }

  async makeRequest(operationData: Record<string, any>): Promise<ITopResponse> {
    const data = new URLSearchParams({
      version: this.version,
      auth_user: this.username,
      auth_pwd: this.password,
      json_data: JSON.stringify(operationData),
    });

    try {
      const response: AxiosResponse = await axios.post(this.restUrl, data, {
        headers: {
          'User-Agent': 'iTop-MCP-Server-NodeJS/1.0',
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        timeout: 30000,
      });

      return response.data as ITopResponse;
    } catch (error: any) {
      if (error.response) {
        throw new Error(`HTTP error ${error.response.status}: ${error.response.data}`);
      } else if (error.request) {
        throw new Error(`Request failed: ${error.message}`);
      } else {
        throw new Error(`Request setup failed: ${error.message}`);
      }
    }
  }
}

function getITopClient(): ITopClient {
  if (!ITOP_BASE_URL || !ITOP_USER || !ITOP_PASSWORD) {
    throw new Error('Missing required environment variables: ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD');
  }
  return new ITopClientImpl(ITOP_BASE_URL, ITOP_USER, ITOP_PASSWORD, ITOP_VERSION);
}

function formatSupportTicketsOutput(
  objects: Record<string, any>,
  ticketType: string,
  formatType: string,
  includeSla: boolean
): string {
  const header = `Found ${Object.keys(objects).length} ${ticketType} tickets:\n\n`;

  if (formatType === 'table') {
    let output = header;
    
    // Collect all tickets with their fields
    const validTickets: Array<[string, Record<string, any>]> = [];
    for (const [objKey, objData] of Object.entries(objects)) {
      if (objData.code === 0) {
        validTickets.push([objKey, objData.fields || {}]);
      }
    }

    if (validTickets.length === 0) {
      return header + 'No valid tickets found.';
    }

    // Define columns and widths
    const columns = ['Ref', 'Title', 'Status', 'SLA TTO', 'SLA TTR', 'Start Date', 'Close Date'];
    const colWidths = { Ref: 12, Title: 40, Status: 12, 'SLA TTO': 8, 'SLA TTR': 8, 'Start Date': 12, 'Close Date': 12 };

    // Header row
    const headerRow = columns.map(col => col.padEnd(colWidths[col as keyof typeof colWidths])).join(' | ');
    output += headerRow + '\n';
    output += '-'.repeat(headerRow.length) + '\n';

    // Data rows
    for (const [objKey, fields] of validTickets) {
      const ref = (fields.ref || objKey).substring(0, 12);
      const title = (fields.title || '').substring(0, 40);
      const status = (fields.status || '').substring(0, 12);
      const slaTto = fields.sla_tto_passed === '1' ? '✓' : fields.sla_tto_passed === '0' ? '✗' : '-';
      const slaTtr = fields.sla_ttr_passed === '1' ? '✓' : fields.sla_ttr_passed === '0' ? '✗' : '-';
      const startDate = (fields.start_date || '').substring(0, 12);
      const closeDate = (fields.close_date || '').substring(0, 12);

      const rowData = [ref, title, status, slaTto, slaTtr, startDate, closeDate];
      const row = rowData.map((data, i) => data.padEnd(colWidths[columns[i] as keyof typeof colWidths])).join(' | ');
      output += row + '\n';
    }

    return output;
  } else if (formatType === 'summary') {
    let output = header;
    
    const statusCounts: Record<string, number> = {};
    let slaBreached = 0;
    let totalTickets = 0;

    for (const [objKey, objData] of Object.entries(objects)) {
      if (objData.code === 0) {
        const fields = objData.fields || {};
        totalTickets++;

        const status = fields.status || 'unknown';
        statusCounts[status] = (statusCounts[status] || 0) + 1;

        // Check SLA breaches
        if (fields.sla_tto_passed === '0' || fields.sla_ttr_passed === '0') {
          slaBreached++;
        }
      }
    }

    output += `📊 **Summary**:\n`;
    output += `   Total tickets: ${totalTickets}\n`;
    output += `   SLA breached: ${slaBreached}\n`;
    output += `   Status breakdown:\n`;

    for (const [status, count] of Object.entries(statusCounts).sort()) {
      output += `     • ${status}: ${count}\n`;
    }

    return output;
  } else {
    // detailed format
    let output = header;

    for (const [objKey, objData] of Object.entries(objects)) {
      if (objData.code === 0) {
        const fields = objData.fields || {};

        // SLA status indicators
        const slaTtoStatus = fields.sla_tto_passed === '1' ? '✓ On Time' : 
                           fields.sla_tto_passed === '0' ? '✗ Breached' : '- N/A';
        const slaTtrStatus = fields.sla_ttr_passed === '1' ? '✓ On Time' : 
                           fields.sla_ttr_passed === '0' ? '✗ Breached' : '- N/A';

        output += `🎫 **${fields.ref || objKey}**\n`;
        output += `   Title: ${fields.title || 'N/A'}\n`;
        output += `   Status: ${fields.status || 'N/A'}\n`;
        output += `   SLA TTO: ${slaTtoStatus}\n`;
        output += `   SLA TTR: ${slaTtrStatus}\n`;
        output += `   Start Date: ${fields.start_date || 'N/A'}\n`;
        output += `   Close Date: ${fields.close_date || 'N/A'}\n`;

        // Show additional fields if available
        if (fields.caller_name) {
          output += `   Caller: ${fields.caller_name}\n`;
        }
        if (fields.agent_name) {
          output += `   Agent: ${fields.agent_name}\n`;
        }
        if (fields.org_name) {
          output += `   Organization: ${fields.org_name}\n`;
        }

        output += '\n';
      }
    }

    return output;
  }
}

// Create the server
const server = new Server(
  {
    name: 'itop-mcp-nodejs',
    version: '1.1.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define tools
const tools: Tool[] = [
  {
    name: 'list_operations',
    description: 'List all available operations in the iTop REST API.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_support_tickets',
    description: 'Get support tickets with optimized field selection for ticket management.',
    inputSchema: {
      type: 'object',
      properties: {
        ticketType: {
          type: 'string',
          description: 'Type of ticket (UserRequest, Incident, Problem, Change)',
          default: 'UserRequest',
        },
        statusFilter: {
          type: 'string',
          description: 'Filter by status (e.g., "new", "assigned", "resolved")',
        },
        includeSla: {
          type: 'boolean',
          description: 'Include SLA fields in output',
          default: true,
        },
        limit: {
          type: 'number',
          description: 'Maximum number of tickets to return',
          default: 50,
        },
        formatOutput: {
          type: 'string',
          description: 'Output format ("detailed", "summary", "table")',
          default: 'detailed',
        },
      },
    },
  },
  {
    name: 'get_objects',
    description: 'Get objects from iTop with flexible output formatting.',
    inputSchema: {
      type: 'object',
      properties: {
        className: {
          type: 'string',
          description: 'The iTop class name (e.g., UserRequest, Person, Organization)',
        },
        key: {
          type: 'string',
          description: 'Optional search criteria. Can be an ID, OQL query, or JSON search criteria',
        },
        outputFields: {
          type: 'string',
          description: 'Comma-separated list of fields to return, or "*" for all fields',
          default: '*',
        },
        limit: {
          type: 'number',
          description: 'Maximum number of objects to return (default: 20, max: 100)',
          default: 20,
        },
        formatOutput: {
          type: 'string',
          description: 'Output format - "detailed", "summary", "table", or "json"',
          default: 'detailed',
        },
      },
      required: ['className'],
    },
  },
  {
    name: 'check_credentials',
    description: 'Check if the configured iTop credentials are valid.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_pc_count',
    description: 'Get count of PCs/computers in iTop.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_pc_status_stats',
    description: 'Get status-based statistics for PCs.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_active_tickets_by_pc',
    description: 'Get active tickets generated by PCs.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_tickets_with_null_service',
    description: 'Get user requests with null/empty service and service subcategory fields.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_change_requests_completion_stats',
    description: 'Get completion statistics for change requests (completed vs not completed on time).',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_change_management_completion_stats',
    description: 'Get completion statistics for ChangeManagement class.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'get_tickets_sla_closure_stats',
    description: 'Get tickets closed vs not closed on time based on SLA.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
];

// Handle list tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const client = getITopClient();

    switch (name) {
      case 'list_operations': {
        const operationData = { operation: 'list_operations' };
        const result = await client.makeRequest(operationData);

        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }

        const operations = result.operations || [];
        let output = 'Available iTop REST API operations:\n\n';

        for (const op of operations) {
          output += `• ${op.verb || 'Unknown'}: ${op.description || 'No description'}\n`;
        }

        return {
          content: [{ type: 'text', text: output }],
        };
      }

      case 'get_support_tickets': {
        const ticketType = (args as any)?.ticketType || 'UserRequest';
        const statusFilter = (args as any)?.statusFilter;
        const includeSla = (args as any)?.includeSla !== false;
        const limit = (args as any)?.limit || 50;
        const formatOutput = (args as any)?.formatOutput || 'detailed';

        // Get ticket configuration
        const ticketConfig = SUPPORT_TICKET_FIELDS[ticketType as keyof typeof SUPPORT_TICKET_FIELDS] || 
                           SUPPORT_TICKET_FIELDS.UserRequest;

        // Build output fields
        let outputFields = ticketConfig.defaultFields;
        if (includeSla) {
          const slaFields = ticketConfig.slaFields.join(',');
          outputFields += `,${slaFields}`;
        }

        // Build query
        const baseQuery = `SELECT ${ticketType}`;
        const conditions: string[] = [];

        if (statusFilter) {
          conditions.push(`status = '${statusFilter}'`);
        }

        const query = conditions.length > 0 ? `${baseQuery} WHERE ${conditions.join(' AND ')}` : baseQuery;

        const operationData = {
          operation: 'core/get',
          class: ticketType,
          key: query,
          output_fields: outputFields,
          limit: limit,
        };

        const result = await client.makeRequest(operationData);

        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }

        const objects = result.objects;
        if (!objects || Object.keys(objects).length === 0) {
          const filterInfo = statusFilter ? ` with status '${statusFilter}'` : '';
          return {
            content: [{ type: 'text', text: `No ${ticketType} tickets found${filterInfo}.` }],
          };
        }

        // Format output with SLA emphasis
        const output = formatSupportTicketsOutput(objects, ticketType, formatOutput, includeSla);

        return {
          content: [{ type: 'text', text: output }],
        };
      }

      case 'get_objects': {
        const className = (args as any)?.className;
        const key = (args as any)?.key;
        const outputFields = (args as any)?.outputFields || '*';
        const limit = Math.min((args as any)?.limit || 20, 100);
        const formatOutput = (args as any)?.formatOutput || 'detailed';

        if (!className) {
          return {
            content: [{ type: 'text', text: 'Error: className is required' }],
          };
        }

        const operationData: Record<string, any> = {
          operation: 'core/get',
          class: className,
          output_fields: outputFields,
          limit: limit,
        };

        // Handle key parameter
        if (key) {
          const trimmedKey = key.trim();
          if (trimmedKey.toUpperCase().startsWith('SELECT')) {
            operationData['key'] = trimmedKey;
          } else if (/^\d+$/.test(trimmedKey)) {
            operationData['key'] = parseInt(trimmedKey, 10);
          } else if (trimmedKey.startsWith('{') && trimmedKey.endsWith('}')) {
            try {
              operationData['key'] = JSON.parse(trimmedKey);
            } catch (e) {
              return {
                content: [{ type: 'text', text: `Error: Invalid JSON in key parameter: ${e}` }],
              };
            }
          } else {
            operationData['key'] = trimmedKey;
          }
        } else {
          operationData['key'] = `SELECT ${className}`;
        }

        const result = await client.makeRequest(operationData);

        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }

        const objects = result.objects;
        if (!objects || Object.keys(objects).length === 0) {
          const searchInfo = key ? ` matching criteria '${key}'` : '';
          return {
            content: [{ type: 'text', text: `No ${className} objects found${searchInfo}.` }],
          };
        }

        // Simple formatting for now
        let output = `Found ${Object.keys(objects).length} ${className} object(s):\n\n`;

        for (const [objKey, objData] of Object.entries(objects)) {
          if (objData.code === 0) {
            const fields = objData.fields || {};
            output += `🔹 **${objKey}**\n`;

            for (const [fieldName, fieldValue] of Object.entries(fields)) {
              if (fieldValue) {
                output += `   ${fieldName}: ${fieldValue}\n`;
              }
            }
            output += '\n';
          }
        }

        return {
          content: [{ type: 'text', text: output }],
        };
      }

      case 'check_credentials': {
        const operationData = { operation: 'list_operations' };
        const result = await client.makeRequest(operationData);

        if (result.code === 0) {
          return {
            content: [{ type: 'text', text: '✅ iTop credentials are valid and working.' }],
          };
        } else {
          return {
            content: [{ type: 'text', text: `❌ iTop credentials check failed: ${result.message || 'Unknown error'}` }],
          };
        }
      }

      case 'get_pc_count': {
        // Try different PC class names
        const pcClasses = ['PC', 'Computer', 'PersonalComputer', 'Workstation'];
        
        for (const className of pcClasses) {
          const operationData = {
            operation: 'core/get',
            class: className,
            key: `SELECT ${className}`,
            output_fields: 'id',
            limit: 1,
          };
          
          try {
            const result = await client.makeRequest(operationData);
            
            if (result.code === 0) {
              // Extract count from message or objects
              const message = result.message || '';
              const count = extractCountFromMessage(message) || Object.keys(result.objects || {}).length;
              
              return {
                content: [{ type: 'text', text: `📱 **PC Count**: ${count} ${className} objects found in iTop` }],
              };
            }
          } catch (e) {
            // Continue to next class
          }
        }
        
        return {
          content: [{ type: 'text', text: '❌ No PC/Computer class found in iTop instance' }],
        };
      }

      case 'get_pc_status_stats': {
        const pcClasses = ['PC', 'Computer', 'PersonalComputer', 'Workstation'];
        
        for (const className of pcClasses) {
          const operationData = {
            operation: 'core/get',
            class: className,
            key: `SELECT ${className}`,
            output_fields: 'status,name,org_name',
            limit: 1000,
          };
          
          try {
            const result = await client.makeRequest(operationData);
            
            if (result.code === 0 && result.objects && Object.keys(result.objects).length > 0) {
              const objects = result.objects;
              const statusCounts: Record<string, number> = {};
              let totalPcs = 0;
              
              for (const [objKey, objData] of Object.entries(objects)) {
                if (objData.code === 0) {
                  const fields = objData.fields || {};
                  const status = fields.status || 'unknown';
                  statusCounts[status] = (statusCounts[status] || 0) + 1;
                  totalPcs++;
                }
              }
              
              let output = `📊 **PC Status Statistics** (${className})\n\n`;
              output += `Total PCs: ${totalPcs}\n\n`;
              output += 'Status breakdown:\n';
              
              const sortedStatuses = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]);
              for (const [status, count] of sortedStatuses) {
                const percentage = totalPcs > 0 ? (count / totalPcs * 100) : 0;
                output += `  • ${status}: ${count} (${percentage.toFixed(1)}%)\n`;
              }
              
              return {
                content: [{ type: 'text', text: output }],
              };
            }
          } catch (e) {
            // Continue to next class
          }
        }
        
        return {
          content: [{ type: 'text', text: '❌ No PC/Computer objects found or class doesn\'t exist' }],
        };
      }

      case 'get_active_tickets_by_pc': {
        const operationData = {
          operation: 'core/get',
          class: 'UserRequest',
          key: "SELECT UserRequest WHERE status IN ('new', 'assigned', 'pending')",
          output_fields: 'ref,title,status,caller_name,org_name,functionalci_name,creation_date',
          limit: 500,
        };
        
        const result = await client.makeRequest(operationData);
        
        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }
        
        const objects = result.objects || {};
        if (Object.keys(objects).length === 0) {
          return {
            content: [{ type: 'text', text: 'No active tickets found' }],
          };
        }
        
        const pcTickets: Record<string, any[]> = {};
        const noCiTickets: any[] = [];
        
        for (const [objKey, objData] of Object.entries(objects)) {
          if (objData.code === 0) {
            const fields = objData.fields || {};
            const ciName = fields.functionalci_name || '';
            
            if (ciName && (ciName.toLowerCase().includes('pc') || 
                          ciName.toLowerCase().includes('computer') || 
                          ciName.toLowerCase().includes('workstation'))) {
              if (!pcTickets[ciName]) {
                pcTickets[ciName] = [];
              }
              pcTickets[ciName].push(fields);
            } else if (!ciName) {
              noCiTickets.push(fields);
            }
          }
        }
        
        const totalPcTickets = Object.values(pcTickets).reduce((sum, tickets) => sum + tickets.length, 0);
        
        let output = '🎫 **Active Tickets by PC**\n\n';
        output += `Found ${Object.keys(objects).length} total active tickets\n`;
        output += `PC-related tickets: ${totalPcTickets}\n`;
        output += `Tickets without CI: ${noCiTickets.length}\n\n`;
        
        if (Object.keys(pcTickets).length > 0) {
          output += '**PC-Related Tickets:**\n';
          const sortedPcs = Object.entries(pcTickets).sort((a, b) => a[0].localeCompare(b[0]));
          
          for (const [pcName, tickets] of sortedPcs) {
            output += `\n🖥️  **${pcName}** (${tickets.length} tickets):\n`;
            const ticketsToShow = tickets.slice(0, 3);
            for (const ticket of ticketsToShow) {
              output += `   • ${ticket.ref || 'N/A'}: ${ticket.title || 'N/A'} [${ticket.status || 'N/A'}]\n`;
            }
            if (tickets.length > 3) {
              output += `   ... and ${tickets.length - 3} more tickets\n`;
            }
          }
        }
        
        return {
          content: [{ type: 'text', text: output }],
        };
      }

      case 'get_tickets_with_null_service': {
        const operationData = {
          operation: 'core/get',
          class: 'UserRequest',
          key: 'SELECT UserRequest WHERE service_id = 0 OR servicesubcategory_id = 0',
          output_fields: 'ref,title,status,caller_name,org_name,service_name,servicesubcategory_name,creation_date',
          limit: 200,
        };
        
        const result = await client.makeRequest(operationData);
        
        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }
        
        const objects = result.objects || {};
        if (Object.keys(objects).length === 0) {
          return {
            content: [{ type: 'text', text: 'No user requests found with null service fields' }],
          };
        }
        
        const nullService: any[] = [];
        const nullSubcategory: any[] = [];
        const bothNull: any[] = [];
        
        for (const [objKey, objData] of Object.entries(objects)) {
          if (objData.code === 0) {
            const fields = objData.fields || {};
            const service = fields.service_name || '';
            const subcategory = fields.servicesubcategory_name || '';
            
            if (!service && !subcategory) {
              bothNull.push(fields);
            } else if (!service) {
              nullService.push(fields);
            } else if (!subcategory) {
              nullSubcategory.push(fields);
            }
          }
        }
        
        let output = '🔍 **User Requests with Null Service Fields**\n\n';
        output += `Total tickets found: ${Object.keys(objects).length}\n`;
        output += `• Both service & subcategory null: ${bothNull.length}\n`;
        output += `• Service null only: ${nullService.length}\n`;
        output += `• Subcategory null only: ${nullSubcategory.length}\n\n`;
        
        const categories = [
          ['Both Null', bothNull],
          ['Service Null', nullService],
          ['Subcategory Null', nullSubcategory],
        ] as const;
        
        for (const [categoryName, tickets] of categories) {
          if (tickets.length > 0) {
            output += `**${categoryName}** (${tickets.length} tickets):\n`;
            const ticketsToShow = tickets.slice(0, 5);
            for (const ticket of ticketsToShow) {
              const title = (ticket.title || 'N/A').substring(0, 50);
              output += `  • ${ticket.ref || 'N/A'}: ${title}... [${ticket.status || 'N/A'}]\n`;
            }
            if (tickets.length > 5) {
              output += `  ... and ${tickets.length - 5} more tickets\n`;
            }
            output += '\n';
          }
        }
        
        return {
          content: [{ type: 'text', text: output }],
        };
      }

      case 'get_change_requests_completion_stats': {
        const changeClasses = ['Change', 'ChangeRequest', 'NormalChange', 'RoutineChange'];
        
        for (const className of changeClasses) {
          const operationData = {
            operation: 'core/get',
            class: className,
            key: `SELECT ${className}`,
            output_fields: 'ref,title,status,start_date,end_date,planned_end_date,creation_date',
            limit: 500,
          };
          
          try {
            const result = await client.makeRequest(operationData);
            
            if (result.code === 0 && result.objects && Object.keys(result.objects).length > 0) {
              const objects = result.objects;
              
              let completedOnTime = 0;
              let completedLate = 0;
              let notCompleted = 0;
              let noPlannedDate = 0;
              const statusCounts: Record<string, number> = {};
              
              for (const [objKey, objData] of Object.entries(objects)) {
                if (objData.code === 0) {
                  const fields = objData.fields || {};
                  const status = fields.status || 'unknown';
                  const endDate = fields.end_date || '';
                  const plannedEndDate = fields.planned_end_date || '';
                  
                  statusCounts[status] = (statusCounts[status] || 0) + 1;
                  
                  const isCompleted = ['completed', 'closed', 'implemented', 'resolved'].includes(status.toLowerCase());
                  
                  if (isCompleted) {
                    if (plannedEndDate && endDate) {
                      try {
                        if (endDate <= plannedEndDate) {
                          completedOnTime++;
                        } else {
                          completedLate++;
                        }
                      } catch (e) {
                        noPlannedDate++;
                      }
                    } else {
                      noPlannedDate++;
                    }
                  } else {
                    notCompleted++;
                  }
                }
              }
              
              const totalChanges = Object.keys(objects).length;
              const completedTotal = completedOnTime + completedLate;
              
              let output = `📊 **Change Requests Completion Statistics** (${className})\n\n`;
              output += `Total Changes: ${totalChanges}\n\n`;
              output += '**Completion Analysis:**\n';
              output += `  ✅ Completed on time: ${completedOnTime}\n`;
              output += `  ⏰ Completed late: ${completedLate}\n`;
              output += `  🔄 Not completed: ${notCompleted}\n`;
              output += `  ❓ No planned date: ${noPlannedDate}\n\n`;
              
              if (completedTotal > 0) {
                const onTimePercentage = (completedOnTime / completedTotal * 100);
                output += `**On-time Completion Rate**: ${onTimePercentage.toFixed(1)}%\n\n`;
              }
              
              output += '**Status Breakdown:**\n';
              const sortedStatuses = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]);
              for (const [status, count] of sortedStatuses) {
                const percentage = totalChanges > 0 ? (count / totalChanges * 100) : 0;
                output += `  • ${status}: ${count} (${percentage.toFixed(1)}%)\n`;
              }
              
              return {
                content: [{ type: 'text', text: output }],
              };
            }
          } catch (e) {
            // Continue to next class
          }
        }
        
        return {
          content: [{ type: 'text', text: '❌ No Change Request objects found or class doesn\'t exist' }],
        };
      }

      case 'get_change_management_completion_stats': {
        const operationData = {
          operation: 'core/get',
          class: 'ChangeManagement',
          key: 'SELECT ChangeManagement',
          output_fields: 'ref,title,status,start_date,end_date,planned_end_date,creation_date,category',
          limit: 500,
        };
        
        const result = await client.makeRequest(operationData);
        
        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }
        
        const objects = result.objects || {};
        if (Object.keys(objects).length === 0) {
          return {
            content: [{ type: 'text', text: 'No ChangeManagement objects found' }],
          };
        }
        
        let completedOnTime = 0;
        let completedLate = 0;
        let notCompleted = 0;
        let noPlannedDate = 0;
        const statusCounts: Record<string, number> = {};
        const categoryCounts: Record<string, number> = {};
        
        for (const [objKey, objData] of Object.entries(objects)) {
          if (objData.code === 0) {
            const fields = objData.fields || {};
            const status = fields.status || 'unknown';
            const endDate = fields.end_date || '';
            const plannedEndDate = fields.planned_end_date || '';
            const category = fields.category || 'unknown';
            
            statusCounts[status] = (statusCounts[status] || 0) + 1;
            categoryCounts[category] = (categoryCounts[category] || 0) + 1;
            
            const isCompleted = ['completed', 'closed', 'implemented', 'resolved'].includes(status.toLowerCase());
            
            if (isCompleted) {
              if (plannedEndDate && endDate) {
                try {
                  if (endDate <= plannedEndDate) {
                    completedOnTime++;
                  } else {
                    completedLate++;
                  }
                } catch (e) {
                  noPlannedDate++;
                }
              } else {
                noPlannedDate++;
              }
            } else {
              notCompleted++;
            }
          }
        }
        
        const totalChanges = Object.keys(objects).length;
        const completedTotal = completedOnTime + completedLate;
        
        let output = '📊 **ChangeManagement Completion Statistics**\n\n';
        output += `Total Changes: ${totalChanges}\n\n`;
        output += '**Completion Analysis:**\n';
        output += `  ✅ Completed on time: ${completedOnTime}\n`;
        output += `  ⏰ Completed late: ${completedLate}\n`;
        output += `  🔄 Not completed: ${notCompleted}\n`;
        output += `  ❓ No planned date: ${noPlannedDate}\n\n`;
        
        if (completedTotal > 0) {
          const onTimePercentage = (completedOnTime / completedTotal * 100);
          output += `**On-time Completion Rate**: ${onTimePercentage.toFixed(1)}%\n\n`;
        }
        
        output += '**Status Breakdown:**\n';
        const sortedStatuses = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]);
        for (const [status, count] of sortedStatuses) {
          const percentage = totalChanges > 0 ? (count / totalChanges * 100) : 0;
          output += `  • ${status}: ${count} (${percentage.toFixed(1)}%)\n`;
        }
        
        if (Object.keys(categoryCounts).length > 0) {
          output += '\n**Category Breakdown:**\n';
          const sortedCategories = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
          for (const [category, count] of sortedCategories) {
            const percentage = totalChanges > 0 ? (count / totalChanges * 100) : 0;
            output += `  • ${category}: ${count} (${percentage.toFixed(1)}%)\n`;
          }
        }
        
        return {
          content: [{ type: 'text', text: output }],
        };
      }

      case 'get_tickets_sla_closure_stats': {
        const operationData = {
          operation: 'core/get',
          class: 'UserRequest',
          key: 'SELECT UserRequest',
          output_fields: 'ref,title,status,sla_tto_passed,sla_ttr_passed,start_date,close_date,creation_date',
          limit: 1000,
        };
        
        const result = await client.makeRequest(operationData);
        
        if (result.code !== 0) {
          return {
            content: [{ type: 'text', text: `Error: ${result.message || 'Unknown error'}` }],
          };
        }
        
        const objects = result.objects || {};
        if (Object.keys(objects).length === 0) {
          return {
            content: [{ type: 'text', text: 'No tickets found' }],
          };
        }
        
        let closedOnTime = 0;
        let closedLate = 0;
        let openOnTime = 0;
        let openBreached = 0;
        let noSlaData = 0;
        const statusCounts: Record<string, number> = {};
        
        for (const [objKey, objData] of Object.entries(objects)) {
          if (objData.code === 0) {
            const fields = objData.fields || {};
            const status = fields.status || 'unknown';
            const slaTtrPassed = fields.sla_ttr_passed || '';
            
            statusCounts[status] = (statusCounts[status] || 0) + 1;
            
            const isClosed = ['closed', 'resolved', 'completed'].includes(status.toLowerCase());
            
            if (['0', '1'].includes(slaTtrPassed)) {
              if (isClosed) {
                if (slaTtrPassed === '1') {
                  closedOnTime++;
                } else {
                  closedLate++;
                }
              } else {
                if (slaTtrPassed === '1') {
                  openOnTime++;
                } else {
                  openBreached++;
                }
              }
            } else {
              noSlaData++;
            }
          }
        }
        
        const totalTickets = Object.keys(objects).length;
        const closedTotal = closedOnTime + closedLate;
        const slaTracked = totalTickets - noSlaData;
        
        let output = '📊 **Ticket SLA Closure Statistics**\n\n';
        output += `Total Tickets: ${totalTickets}\n`;
        output += `Tickets with SLA data: ${slaTracked}\n`;
        output += `Tickets without SLA data: ${noSlaData}\n\n`;
        output += '**SLA Closure Analysis:**\n';
        output += `  ✅ Closed on time: ${closedOnTime}\n`;
        output += `  ⏰ Closed late (SLA breached): ${closedLate}\n`;
        output += `  🔄 Open and on time: ${openOnTime}\n`;
        output += `  🚨 Open and SLA breached: ${openBreached}\n\n`;
        
        if (closedTotal > 0) {
          const onTimeClosureRate = (closedOnTime / closedTotal * 100);
          output += `**On-time Closure Rate**: ${onTimeClosureRate.toFixed(1)}%\n`;
        }
        
        if (slaTracked > 0) {
          const slaComplianceRate = ((closedOnTime + openOnTime) / slaTracked * 100);
          output += `**Overall SLA Compliance Rate**: ${slaComplianceRate.toFixed(1)}%\n\n`;
        }
        
        output += '**Status Breakdown:**\n';
        const sortedStatuses = Object.entries(statusCounts).sort((a, b) => b[1] - a[1]);
        for (const [status, count] of sortedStatuses) {
          const percentage = totalTickets > 0 ? (count / totalTickets * 100) : 0;
          output += `  • ${status}: ${count} (${percentage.toFixed(1)}%)\n`;
        }
        
        return {
          content: [{ type: 'text', text: output }],
        };
      }
    }
  } catch (error: any) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message || 'Unknown error'}` }],
    };
  }
});

// Initialize and start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('iTop MCP server (Node.js) running on stdio');
}

// Export for testing
export { getITopClient, formatSupportTicketsOutput, extractCountFromMessage };

// Run the server if this file is executed directly
if (require.main === module) {
  main().catch(console.error);
}

// Extract count information from iTop API response messages
function extractCountFromMessage(message: string): number {
  try {
    if (!message) {
      return 0;
    }
    
    const messageLower = message.toLowerCase();
    
    // Try multiple flexible patterns in order of preference
    const patterns = [
      // iTop common formats
      /found[\s:]*(\d+)/,                    // "Found: 92", "Found 92", "found:92"
      /(\d+)\s*found/,                       // "92 found", "92found"
      /(\d+)\s*objects?\s*found/,            // "92 objects found", "1 object found"
      /found\s*(\d+)\s*objects?/,            // "found 92 objects", "found 1 object"
      /(\d+)\s*objects?\s*returned/,         // "92 objects returned"
      /returned\s*(\d+)\s*objects?/,         // "returned 92 objects"
      /(\d+)\s*results?/,                    // "92 results", "1 result"
      /results?[\s:]*(\d+)/,                 // "results: 92", "results 92"
      /total[\s:]*(\d+)/,                    // "total: 92", "total 92"
      /count[\s:]*(\d+)/,                    // "count: 92", "count 92"
      /(\d+)\s*records?/,                    // "92 records", "1 record"
      /records?[\s:]*(\d+)/,                 // "records: 92"
      /(\d+)\s*entries/,                     // "92 entries"
      /entries[\s:]*(\d+)/,                  // "entries: 92"
      // Generic number extraction as last resort
      /(\d+)/                                // Any number in the message
    ];
    
    for (const pattern of patterns) {
      const match = messageLower.match(pattern);
      if (match && match[1]) {
        const count = parseInt(match[1], 10);
        // Sanity check: reasonable count range
        if (count >= 0 && count <= 1000000) {  // Up to 1M records seems reasonable
          return count;
        }
      }
    }
    
    return 0;
  } catch (error) {
    return 0;
  }
}
