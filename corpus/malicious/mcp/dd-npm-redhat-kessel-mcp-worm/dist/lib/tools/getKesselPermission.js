"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getKesselPermissionTool = getKesselPermissionTool;
const zod_1 = require("zod");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const fetchAllServiceMappings_1 = require("../utils/fetchAllServiceMappings");
function segmentMatches(pattern, value) {
    return pattern === '*' || pattern === value;
}
function matchesWildcard(pattern, v1Permission) {
    const [pApp, pResource, pVerb] = pattern.split(':');
    const [vApp, vResource, vVerb] = v1Permission.split(':');
    return (segmentMatches(pApp, vApp) &&
        segmentMatches(pResource, vResource) &&
        segmentMatches(pVerb, vVerb));
}
function isWildcard(v1Permission) {
    return v1Permission.includes('*');
}
function formatSingleMapping(mapping, service) {
    const lines = [
        `v1 permission : ${mapping.v1Permission}`,
        `v2 relation   : ${mapping.v2Relation}`,
        `service       : ${service}`,
        `host-centric  : ${mapping.hostCentric}`,
        `unified       : ${mapping.unified}`,
    ];
    if (mapping.hostCentric) {
        lines.push('', 'Note: This is a host-centric permission. The user must also have inventory_host_view ' +
            '(inventory:hosts:read) for this permission to be effective. The workspace-level check ' +
            `uses the _assigned variant: ${mapping.v2Relation}_assigned.`);
    }
    if (mapping.unified) {
        lines.push('', 'Note: This is a unified permission — the v1 and v2 names are the same semantic concept. ' +
            'The v2 relation name is simply the v1 permission with colons replaced by underscores.');
    }
    return lines;
}
function getKesselPermissionTool() {
    const tool = async (args) => {
        const { v1Permission } = args;
        const allServices = await (0, fetchAllServiceMappings_1.fetchAllServiceMappings)();
        if (isWildcard(v1Permission)) {
            const matches = allServices.flatMap(({ service, permissions }) => permissions.mappings
                .filter((m) => matchesWildcard(v1Permission, m.v1Permission))
                .map((mapping) => ({ mapping, service })));
            if (matches.length === 0) {
                throw new types_js_1.McpError(types_js_1.ErrorCode.InvalidParams, `No permissions matched the wildcard pattern "${v1Permission}".`);
            }
            const lines = [
                `Wildcard "${v1Permission}" expands to ${matches.length} v2 relation(s):`,
                '',
                ...matches.map(({ mapping, service }) => `  ${mapping.v1Permission} → ${mapping.v2Relation}  [${service}${mapping.hostCentric ? ', host-centric' : ''}${mapping.unified ? ', unified' : ''}]`),
                '',
                'In v2 there is no wildcard — use an OR of all the relations above.',
            ];
            return { content: [{ type: 'text', text: lines.join('\n') }] };
        }
        // Exact match
        for (const { service, permissions } of allServices) {
            const mapping = permissions.mappings.find((m) => m.v1Permission === v1Permission);
            if (mapping) {
                return { content: [{ type: 'text', text: formatSingleMapping(mapping, service).join('\n') }] };
            }
            if (permissions.deprecatedV1Only.includes(v1Permission.replace(/:/g, '_'))) {
                return {
                    content: [
                        {
                            type: 'text',
                            text: `v1 permission "${v1Permission}" is v1-only and has no Kessel v2 equivalent. ` +
                                `It has been deprecated and should not be used in new code.`,
                        },
                    ],
                };
            }
        }
        throw new types_js_1.McpError(types_js_1.ErrorCode.InvalidParams, `Permission "${v1Permission}" was not found in any service schema. ` +
            'Check the permission name and use listServices to see available services.');
    };
    return [
        'getKesselPermission',
        {
            description: 'Look up the Kessel v2 relation name for a given RBAC v1 permission string ' +
                '(e.g. "notifications:events:read"). Supports wildcards (e.g. "notifications:*:*") which ' +
                'expand to all matching v2 relations — since v2 has no wildcard equivalent. ' +
                'Searches all service schemas automatically.',
            inputSchema: {
                v1Permission: zod_1.z
                    .string()
                    .describe('The RBAC v1 permission in app:resource:verb format. Supports * wildcards, ' +
                    'e.g. "notifications:events:read", "notifications:*:*", "advisor:*:read".'),
            },
        },
        tool,
    ];
}
