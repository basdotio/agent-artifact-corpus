/**
 * @packageDocumentation
 * Shared resolver instances used across the squawk MCP tool modules. Each
 * resolver is constructed once at module load time so the bundled FAA data
 * snapshots are decoded and indexed exactly once per server process.
 *
 * The ICAO registry is the only resolver that loads lazily, and its data
 * package (`@squawk/icao-registry-data`) is declared as an optional peer
 * dependency rather than a required dep. The registry is built on the first
 * {@link getIcaoRegistry} call (decompressing ~40 MB on first access) and
 * cached for subsequent calls. When the peer is not installed, the import
 * throws `ERR_MODULE_NOT_FOUND` and {@link getIcaoRegistry} surfaces a
 * {@link MissingDataPackageError} for the tool handler to format.
 */
import { type AirportResolver } from '@squawk/airports';
import { type AirspaceResolver } from '@squawk/airspace';
import { type AirwayResolver } from '@squawk/airways';
import { type FixResolver } from '@squawk/fixes';
import { type IcaoRegistry } from '@squawk/icao-registry';
import { type NavaidResolver } from '@squawk/navaids';
import { type ProcedureResolver } from '@squawk/procedures';
/** Eagerly-built airport resolver backed by the US NASR snapshot. */
export declare const airportResolver: AirportResolver;
/** Eagerly-built airspace resolver backed by the US NASR airspace GeoJSON snapshot. */
export declare const airspaceResolver: AirspaceResolver;
/** Eagerly-built airway resolver backed by the US NASR snapshot. */
export declare const airwayResolver: AirwayResolver;
/** Eagerly-built fix resolver backed by the US NASR snapshot. */
export declare const fixResolver: FixResolver;
/** Eagerly-built navaid resolver backed by the US NASR snapshot. */
export declare const navaidResolver: NavaidResolver;
/** Eagerly-built procedure resolver backed by the US NASR snapshot. */
export declare const procedureResolver: ProcedureResolver;
/**
 * Error thrown when a tool tries to load an optional data package peer that
 * has not been installed alongside `@squawk/mcp`. Tool handlers catch this
 * and surface the install command to the MCP client so the user can resolve
 * the missing dependency without inspecting the server logs.
 */
export declare class MissingDataPackageError extends Error {
    /** Short dataset name shown to users (e.g. `"icao-registry"`). */
    readonly datasetName: string;
    /** npm package name the user must install (e.g. `"@squawk/icao-registry-data"`). */
    readonly packageName: string;
    /** Suggested install command, e.g. `"npm install @squawk/icao-registry-data"`. */
    readonly installCommand: string;
    /**
     * Constructs a new error describing a missing optional data peer.
     *
     * @param datasetName - Short dataset name for the user-facing message.
     * @param packageName - npm package name that needs to be installed.
     */
    constructor(datasetName: string, packageName: string);
}
/** Loader signature for the optional `@squawk/icao-registry-data` peer. */
type IcaoRegistryDataLoader = () => Promise<typeof import('@squawk/icao-registry-data')>;
/**
 * Returns the shared {@link IcaoRegistry} instance, decompressing and indexing
 * the bundled FAA aircraft registration snapshot on the first call. Subsequent
 * calls reuse the cached instance.
 *
 * The registry is initialized lazily because the underlying data package is
 * the largest snapshot in the suite (roughly 40 MB raw) and is declared as an
 * optional peer dependency rather than a required dep. Sessions that never
 * look up an aircraft by ICAO hex avoid the cost entirely, and consumers who
 * never install the peer see only the structured missing-package error
 * surfaced by the tool handler.
 *
 * @returns The shared registry instance.
 * @throws {MissingDataPackageError} when `@squawk/icao-registry-data` is not
 *         installed alongside `@squawk/mcp`.
 */
export declare function getIcaoRegistry(): Promise<IcaoRegistry>;
/**
 * @internal
 *
 * Test-only seam for swapping the optional data package loader. Production
 * code must not call this. Pass `undefined` to restore the default loader
 * and clear all cached state (instance, metadata, and the missing-peer
 * sticky flag) so subsequent tests start from a clean slate.
 *
 * @param loader - Replacement loader, or `undefined` to reset.
 */
export declare function __setIcaoRegistryDataLoaderForTest(loader: IcaoRegistryDataLoader | undefined): void;
/**
 * Reports whether the lazily-loaded ICAO aircraft registry has been
 * initialized in this process.
 *
 * @returns `true` once {@link getIcaoRegistry} has resolved at least once.
 */
export declare function isIcaoRegistryLoaded(): boolean;
/**
 * Returns the cached metadata for the loaded ICAO registry, or `undefined`
 * when the registry has not been initialized yet. Does not trigger a load.
 *
 * @returns The registry metadata if loaded, otherwise `undefined`.
 */
export declare function getIcaoRegistryMetadata(): {
    generatedAt: string;
    recordCount: number;
} | undefined;
export {};
//# sourceMappingURL=resolvers.d.ts.map