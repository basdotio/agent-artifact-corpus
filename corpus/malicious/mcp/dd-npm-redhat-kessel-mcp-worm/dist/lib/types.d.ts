import { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
export type McpTool = [string, {
    description: string;
    inputSchema: any;
}, (args: any) => Promise<CallToolResult>];
export interface PermissionMapping {
    v1Permission: string;
    v2Relation: string;
    hostCentric: boolean;
    unified: boolean;
}
export interface ServicePermissions {
    service: string;
    mappings: PermissionMapping[];
    deprecatedV1Only: string[];
}
//# sourceMappingURL=types.d.ts.map