import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';

const MAX_CHUNK_SIZE = 100000; // Base chunk size for responses

interface ChunkMetadata {
  totalChunks: number;
  currentChunk: number;
  hasMore: boolean;
  totalSize?: number;
  chunkType?: 'data' | 'collection';
  collectionInfo?: {
    totalItems: number;
    itemsInChunk: number;
    startIndex: number;
    endIndex: number;
  };
}

interface Wearer {
  currentHats?: Array<any>;
  [key: string]: any;
}

/**
 * Creates a standardized MCP response for successful operations
 * @param data The data to be included in the response
 * @returns A properly formatted MCP CallToolResult
 */
export function createSuccessResponse(data: unknown): CallToolResult {
  return {
    _meta: {},
    content: [
      {
        type: 'text',
        text: JSON.stringify(data, null, 2),
      },
    ],
  };
}

/**
 * Creates a standardized MCP response for error cases
 * @param error The error message or Error object
 * @returns A properly formatted MCP CallToolResult
 */
export function createErrorResponse(error: Error | string): CallToolResult {
  const errorMessage = error instanceof Error ? error.message : error;
  return {
    _meta: {},
    content: [
      {
        type: 'text',
        text: `Error: ${errorMessage}`,
      },
    ],
  };
}

/**
 * Creates a standardized MCP response for JSON data
 * @param data The data to be included in the response
 * @param uri Optional URI for the resource
 * @returns A properly formatted MCP CallToolResult
 */
export function createJsonResponse(
  data: unknown,
  uri?: string
): CallToolResult {
  const startTime = Date.now();
  console.log('Creating JSON response...');

  // If the data is too large, use chunked response
  const stringified = JSON.stringify(data, null, 2);
  console.log(`Response stringification took ${Date.now() - startTime}ms`);

  if (stringified.length > MAX_CHUNK_SIZE) {
    console.log(
      `Response size ${stringified.length} exceeds chunk size ${MAX_CHUNK_SIZE}, using chunked response`
    );
    return createChunkedResponse(data);
  }

  const response: CallToolResult = {
    _meta: {},
    content: [
      {
        type: 'resource' as const,
        resource: {
          uri: uri || 'data',
          text: stringified,
          mimeType: 'application/json',
        },
      },
    ],
  };

  console.log(`JSON response created in ${Date.now() - startTime}ms`);
  return response;
}

/**
 * Optimizes response data by selectively trimming and structuring content
 */
export function optimizeResponse(data: any): any {
  if (!data) return data;

  const optimizedData = { ...data };

  // Handle arrays more efficiently
  if (Array.isArray(optimizedData)) {
    return optimizedData.map((item) => optimizeItem(item));
  }

  // Handle objects
  return optimizeItem(optimizedData);
}

/**
 * Optimizes individual items in the response
 */
function optimizeItem(item: any): any {
  if (!item || typeof item !== 'object') return item;

  const optimized: Record<string, any> = {};

  // Handle wearers array
  if (Array.isArray(item.wearers)) {
    optimized.wearers = {
      total: item.wearers.length,
      items: item.wearers.slice(0, 10).map((wearer: Wearer) => ({
        id: wearer.id,
        currentHats: wearer.currentHats?.slice(0, 10) || [],
        _totalHats: wearer.currentHats?.length || 0,
      })),
    };
  }

  // Handle subHats array
  if (Array.isArray(item.subHats)) {
    optimized.subHats = {
      total: item.subHats.length,
      items: item.subHats.map((subHat: any) => ({
        id: subHat.id,
        prettyId: subHat.prettyId,
        status: subHat.status,
        maxSupply: subHat.maxSupply,
        currentSupply: subHat.currentSupply,
      })),
    };
  }

  // Handle detailsDecoded more efficiently
  if (item.detailsDecoded) {
    optimized.detailsDecoded = processDetailsDecoded(item.detailsDecoded);
  }

  // Copy other properties
  for (const [key, value] of Object.entries(item)) {
    if (key !== 'wearers' && key !== 'subHats' && key !== 'detailsDecoded') {
      optimized[key] = value;
    }
  }

  return optimized;
}

/**
 * Processes detailsDecoded content efficiently
 */
function processDetailsDecoded(
  details: Record<string, any>
): Record<string, any> {
  const processed: Record<string, any> = {};

  for (const [key, value] of Object.entries(details)) {
    if (Array.isArray(value)) {
      processed[key] = value.map((item) => {
        if (typeof item === 'string' && item.length > 1000) {
          return item.substring(0, 1000) + '...';
        }
        if (typeof item === 'object' && item !== null) {
          return Object.fromEntries(
            Object.entries(item).map(([k, v]) => [
              k,
              typeof v === 'string' && v.length > 1000
                ? v.substring(0, 1000) + '...'
                : v,
            ])
          );
        }
        return item;
      });
    } else if (typeof value === 'string' && value.length > 1000) {
      processed[key] = value.substring(0, 1000) + '...';
    } else {
      processed[key] = value;
    }
  }

  return processed;
}

/**
 * Creates a chunked response for large datasets
 */
function createChunkedResponse(data: any): CallToolResult {
  const optimizedData = optimizeResponse(data);

  // Handle array data differently than object data
  if (Array.isArray(optimizedData)) {
    return createArrayChunkedResponse(optimizedData);
  }

  // Handle large object data
  return createObjectChunkedResponse(optimizedData);
}

/**
 * Creates a chunked response specifically for arrays
 */
function createArrayChunkedResponse(data: any[]): CallToolResult {
  const ITEMS_PER_CHUNK = 50; // Adjust based on average item size
  const totalItems = data.length;
  const chunks: any[][] = [];

  // Split array into chunks
  for (let i = 0; i < data.length; i += ITEMS_PER_CHUNK) {
    chunks.push(data.slice(i, i + ITEMS_PER_CHUNK));
  }

  // Return first chunk with metadata
  const firstChunk = chunks[0];
  return {
    _meta: {
      totalChunks: chunks.length,
      currentChunk: 1,
      hasMore: chunks.length > 1,
      chunkType: 'collection',
      collectionInfo: {
        totalItems,
        itemsInChunk: firstChunk.length,
        startIndex: 0,
        endIndex: firstChunk.length - 1,
      },
    },
    content: [
      {
        type: 'text',
        text: JSON.stringify(firstChunk, null, 2),
      },
    ],
  };
}

/**
 * Creates a chunked response for large objects
 */
function createObjectChunkedResponse(data: any): CallToolResult {
  const stringified = JSON.stringify(data, null, 2);
  const chunks = [];

  // Split into size-based chunks
  for (let i = 0; i < stringified.length; i += MAX_CHUNK_SIZE) {
    chunks.push(stringified.slice(i, i + MAX_CHUNK_SIZE));
  }

  // Return first chunk with metadata
  return {
    _meta: {
      totalChunks: chunks.length,
      currentChunk: 1,
      hasMore: chunks.length > 1,
      chunkType: 'data',
      totalSize: stringified.length,
    },
    content: [
      {
        type: 'text',
        text: chunks[0],
      },
    ],
  };
}

/**
 * Main response chunking function
 */
export function chunkResponse(data: any): CallToolResult {
  const startTime = Date.now();
  console.log('Creating chunked response...');

  // For small responses, return directly
  const stringified = JSON.stringify(optimizeResponse(data), null, 2);
  console.log(`Chunked response preparation took ${Date.now() - startTime}ms`);

  if (stringified.length <= MAX_CHUNK_SIZE) {
    console.log('Response small enough for direct return');
    return createSuccessResponse(data);
  }

  // For large responses, use chunked response
  console.log(`Creating chunked response for size ${stringified.length}`);
  const response = createChunkedResponse(data);
  console.log(`Chunked response created in ${Date.now() - startTime}ms`);
  return response;
}
