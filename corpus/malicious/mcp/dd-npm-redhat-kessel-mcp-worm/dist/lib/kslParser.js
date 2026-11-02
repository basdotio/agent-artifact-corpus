"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseKsl = parseKsl;
// Matches: @rbac.add_v1_based_permission(app:'x', resource:'y', verb:'z', v2_perm:'w')
// Also handles the no-namespace form used inside rbac.ksl itself: @add_v1_based_permission(...)
const V1_PERM_RE = /add_v1_based_permission\(app:'([^']+)',\s*resource:'([^']+)',\s*verb:'([^']+)',\s*v2_perm:'([^']+)'\)/g;
// Matches: @rbac.add_contingent_permission(first: 'x', second: 'y', contingent: 'z')
const CONTINGENT_RE = /add_contingent_permission\(first:\s*'([^']+)',\s*second:\s*'([^']+)',\s*contingent:\s*'([^']+)'\)/g;
// Matches: @rbac.add_v1only_permission(perm:'x')
const V1_ONLY_RE = /add_v1only_permission\(perm:'([^']+)'\)/g;
// The relation that gates host-centric permissions — must be present alongside the _assigned variant
const HOST_CENTRIC_RELATION = 'inventory_host_view';
// Matches: @add_unified_permission(app:'x', resource:'y', verb:'z')
// Used for RBAC's own permissions where v1 and v2 share the same name (colons → underscores)
const UNIFIED_RE = /add_unified_permission\(app:'([^']+)',\s*resource:'([^']+)',\s*verb:'([^']+)'\)/g;
/**
 * Parses a KSL file and extracts all RBAC v1 → Kessel v2 permission mappings.
 *
 * Host-centric permissions are identified by the pattern:
 *   add_v1_based_permission(..., v2_perm: 'foo_assigned')
 *   add_contingent_permission(first: 'inventory_host_view', second: 'foo_assigned', contingent: 'foo')
 * In this case the practical v2 relation to use in the UI is 'foo' (not 'foo_assigned').
 */
function parseKsl(kslContent, service) {
    // Step 1: extract raw v1-based permission entries
    const rawMappings = [];
    let match;
    const v1Re = new RegExp(V1_PERM_RE.source, 'g');
    while ((match = v1Re.exec(kslContent)) !== null) {
        const [, app, resource, verb, v2Perm] = match;
        rawMappings.push({ v1: `${app}:${resource}:${verb}`, v2: v2Perm });
    }
    // Step 2: build a map of assigned_perm → contingent_perm for host-centric resolution
    // key: second (the _assigned variant), value: { first, contingent }
    const contingentMap = new Map();
    const contingentRe = new RegExp(CONTINGENT_RE.source, 'g');
    while ((match = contingentRe.exec(kslContent)) !== null) {
        const [, first, second, contingent] = match;
        contingentMap.set(second, { first, contingent });
    }
    // Step 3: extract v1-only deprecated permissions
    const deprecatedV1Only = [];
    const v1OnlyRe = new RegExp(V1_ONLY_RE.source, 'g');
    while ((match = v1OnlyRe.exec(kslContent)) !== null) {
        deprecatedV1Only.push(match[1]);
    }
    // Step 4: extract unified permissions (v1 and v2 share the same name, colons → underscores)
    const unifiedRe = new RegExp(UNIFIED_RE.source, 'g');
    while ((match = unifiedRe.exec(kslContent)) !== null) {
        const [, app, resource, verb] = match;
        rawMappings.push({ v1: `${app}:${resource}:${verb}`, v2: `${app}_${resource}_${verb}`, unified: true });
    }
    // Step 5: resolve host-centric permissions — if the v2_perm from step 1 appears as the
    // `second` in a contingent where `first` is inventory_host_view, replace with the
    // `contingent` value and flag as host-centric.
    const mappings = rawMappings.map(({ v1, v2, unified }) => {
        if (unified) {
            return { v1Permission: v1, v2Relation: v2, hostCentric: false, unified: true };
        }
        const contingent = contingentMap.get(v2);
        if (contingent && contingent.first === HOST_CENTRIC_RELATION) {
            return { v1Permission: v1, v2Relation: contingent.contingent, hostCentric: true, unified: false };
        }
        return { v1Permission: v1, v2Relation: v2, hostCentric: false, unified: false };
    });
    return { service, mappings, deprecatedV1Only };
}
