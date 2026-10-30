"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getServicePermissionsTool = getServicePermissionsTool;
const zod_1 = require("zod");
const types_js_1 = require("@modelcontextprotocol/sdk/types.js");
const services_1 = require("../services");
const cachedFetch_1 = require("../cachedFetch");
const kslParser_1 = require("../kslParser");
function formatMapping(m) {
    const hostNote = m.hostCentric ? ' [host-centric: also requires inventory_host_view]' : '';
    return `${m.v1Permission} → ${m.v2Relation}${hostNote}`;
}
function getServicePermissionsTool() {
    const tool = async (args) => {
        const { service } = args;
        const kslContent = await (0, cachedFetch_1.cachedFetch)((0, services_1.getKslUrl)(service)).catch((err) => {
            throw new types_js_1.McpError(types_js_1.ErrorCode.InternalError, `Failed to fetch KSL schema for service "${service}": ${err.message}`);
        });
        const { mappings, deprecatedV1Only } = (0, kslParser_1.parseKsl)(kslContent, service);
        const lines = [
            `# Kessel permission mappings for: ${service}`,
            '',
            '## v1 → v2 mappings',
            ...mappings.map(formatMapping),
        ];
        if (deprecatedV1Only.length > 0) {
            lines.push('', '## v1-only (deprecated, no v2 equivalent)', ...deprecatedV1Only);
        }
        return {
            content: [{ type: 'text', text: lines.join('\n') }],
        };
    };
    return [
        'getServicePermissions',
        {
            description: 'Get all RBAC v1 → Kessel v2 permission mappings for a given HCC service. ' +
                'Returns the v2 relation name for each v1 permission, with notes on host-centric ' +
                'permissions (which also require inventory_host_view) and deprecated v1-only entries.',
            inputSchema: {
                service: zod_1.z
                    .enum(services_1.SERVICES)
                    .describe('The HCC service to look up permission mappings for (e.g. "notifications", "advisor").'),
            },
        },
        tool,
    ];
}
