/**
 * @file server-info
 * @description MCP server identity constants (name and version).
 *
 * Responsibilities:
 * - Define the server name and version in one place, shared by the entry layer (index) and
 *   the tool layer (tools)
 * - Avoid hard-coding the same strings in multiple places, preventing drift during version bumps
 */

// Server identity constants. version must stay in sync with package.json's version field.

/** Public identity name of the MCP server. */
export const SERVER_NAME = 'cn-websearch-mcp';

/** Server version, kept in sync with package.json's version field. */
export const SERVER_VERSION = '0.2.0';
