"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getListServicesTool = getListServicesTool;
const services_1 = require("../services");
function getListServicesTool() {
    const tool = async (_args) => {
        return {
            content: [
                {
                    type: 'text',
                    text: services_1.SERVICES.join('\n'),
                },
            ],
        };
    };
    return [
        'listServices',
        {
            description: 'List all HCC services that have Kessel (RBAC v2) permission schemas. ' +
                'Use the returned service names with getServicePermissions or getKesselPermission.',
            inputSchema: {},
        },
        tool,
    ];
}
