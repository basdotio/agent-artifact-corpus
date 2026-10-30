"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getMigrationExampleTool = getMigrationExampleTool;
const zod_1 = require("zod");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const fetchAllServiceMappings_1 = require("../utils/fetchAllServiceMappings");
function buildExample(v1Permission, mapping) {
    const hostNote = mapping.hostCentric
        ? `\n// Note: "${v1Permission}" is host-centric — the user also needs inventory:hosts:read\n// (inventory_host_view) for this to be effective. The backend enforces the host-level check.\n`
        : '';
    return `// Migration: "${v1Permission}" → Kessel v2
//
// 1. Fetch the default workspace ID once (e.g. in a context provider or at app init):
import { useDefaultWorkspace } from '@project-kessel/react-kessel-access-check';

const { workspaceId: defaultWorkspaceId } = useDefaultWorkspace();

// 2. Replace your v1 permission check with useSelfAccessCheck:
import { useSelfAccessCheck } from '@project-kessel/react-kessel-access-check';
${hostNote}
const { result } = useSelfAccessCheck({
  relation: '${mapping.v2Relation}',
  resource: {
    id: defaultWorkspaceId,
    type: 'workspace',
    reporter: { type: 'rbac' },
  },
});

// result.permitted === true when the user has this permission
`;
}
function getMigrationExampleTool() {
    const tool = async (args) => {
        const { v1Permission } = args;
        const allServices = await (0, fetchAllServiceMappings_1.fetchAllServiceMappings)();
        for (const { permissions } of allServices) {
            const mapping = permissions.mappings.find((m) => m.v1Permission === v1Permission);
            if (mapping) {
                return {
                    content: [{ type: 'text', text: buildExample(v1Permission, mapping) }],
                };
            }
        }
        throw new types_js_1.McpError(types_js_1.ErrorCode.InvalidParams, `Permission "${v1Permission}" was not found in any service schema. ` +
            'Use getKesselPermission to verify the permission name.');
    };
    return [
        'getMigrationExample',
        {
            description: 'Generate a ready-to-use TypeScript code snippet that migrates a RBAC v1 permission check ' +
                'to the Kessel v2 useSelfAccessCheck hook. Provide the v1 permission in app:resource:verb format ' +
                '(e.g. "notifications:events:read") and receive copy-pasteable React code.',
            inputSchema: {
                v1Permission: zod_1.z
                    .string()
                    .describe('The RBAC v1 permission to generate migration code for, e.g. "notifications:events:read".'),
            },
        },
        tool,
    ];
}
