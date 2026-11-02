import { ServicePermissions } from './types';
/**
 * Parses a KSL file and extracts all RBAC v1 → Kessel v2 permission mappings.
 *
 * Host-centric permissions are identified by the pattern:
 *   add_v1_based_permission(..., v2_perm: 'foo_assigned')
 *   add_contingent_permission(first: 'inventory_host_view', second: 'foo_assigned', contingent: 'foo')
 * In this case the practical v2 relation to use in the UI is 'foo' (not 'foo_assigned').
 */
export declare function parseKsl(kslContent: string, service: string): ServicePermissions;
//# sourceMappingURL=kslParser.d.ts.map