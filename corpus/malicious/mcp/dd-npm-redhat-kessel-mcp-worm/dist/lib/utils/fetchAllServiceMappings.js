"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.fetchAllServiceMappings = fetchAllServiceMappings;
const services_1 = require("../services");
const cachedFetch_1 = require("../cachedFetch");
const kslParser_1 = require("../kslParser");
/**
 * Fetches and parses all service KSL schemas in parallel.
 * Services that fail to fetch are silently skipped (e.g. network errors, 404s).
 */
async function fetchAllServiceMappings() {
    const results = await Promise.allSettled(services_1.SERVICES.map(async (service) => {
        const kslContent = await (0, cachedFetch_1.cachedFetch)((0, services_1.getKslUrl)(service));
        return { service, permissions: (0, kslParser_1.parseKsl)(kslContent, service) };
    }));
    return results
        .filter((r) => r.status === 'fulfilled')
        .map((r) => r.value);
}
