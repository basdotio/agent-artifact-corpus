"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SERVICES = void 0;
exports.getKslUrl = getKslUrl;
exports.SERVICES = [
    'advisor',
    'compliance',
    'config-manager',
    'content-sources',
    'hbi',
    'malware',
    'notifications',
    'patch',
    'playbook-dispatcher',
    'rbac',
    'remediations',
    'ros',
    'tasks',
    'vulnerability',
];
const KSL_BASE_URL = 'https://raw.githubusercontent.com/RedHatInsights/rbac-config/master/configs/prod/schemas/src';
function getKslUrl(service) {
    return `${KSL_BASE_URL}/${service}.ksl`;
}
