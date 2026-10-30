import { ServicePermissions } from '../types';
import { Service } from '../services';
export interface ServiceResult {
    service: Service;
    permissions: ServicePermissions;
}
/**
 * Fetches and parses all service KSL schemas in parallel.
 * Services that fail to fetch are silently skipped (e.g. network errors, 404s).
 */
export declare function fetchAllServiceMappings(): Promise<ServiceResult[]>;
//# sourceMappingURL=fetchAllServiceMappings.d.ts.map