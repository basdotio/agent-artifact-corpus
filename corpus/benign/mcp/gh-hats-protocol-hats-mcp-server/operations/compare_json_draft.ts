import { z } from 'zod';
import {
  createErrorResponse,
  createJsonResponse,
  chunkResponse,
} from '../utils/response.js';

// Define size limits
const MAX_JSON_SIZE = 10 * 1024 * 1024; // 10MB limit for input JSONs

// Define the parameter schema for the operation
export const compareJsonDraftParameters = z.object({
  currentDraftJson: z
    .string()
    .max(MAX_JSON_SIZE)
    .describe('The current JSON draft to compare against'),
  newDraftJson: z
    .string()
    .max(MAX_JSON_SIZE)
    .describe('The new JSON draft containing the proposed changes'),
  chain: z
    .string()
    .describe('The chain name (e.g. "mainnet", "optimism", etc.)'),
  chainId: z
    .number()
    .describe('The chain ID (e.g. 1 for mainnet, 10 for optimism)'),
  treeId: z.number().describe('The ID of the tree to compare against'),
});

interface JsonDiff {
  type: 'added' | 'removed' | 'modified';
  path: string[]; // JSON path to the change
  oldValue?: any;
  newValue?: any;
}

function formatDiffDescription(diff: JsonDiff): string {
  const location = diff.path.join('.');
  switch (diff.type) {
    case 'added':
      return `Added ${location}: ${JSON.stringify(diff.newValue)}`;
    case 'removed':
      return `Removed ${location}: ${JSON.stringify(diff.oldValue)}`;
    case 'modified':
      return `Modified ${location} from ${JSON.stringify(
        diff.oldValue
      )} to ${JSON.stringify(diff.newValue)}`;
    default:
      return 'Unknown change type';
  }
}

function compareJson(
  oldJson: any,
  newJson: any,
  path: string[] = []
): JsonDiff[] {
  const diffs: JsonDiff[] = [];

  // Handle different types
  if (typeof oldJson !== typeof newJson) {
    return [
      {
        type: 'modified',
        path,
        oldValue: oldJson,
        newValue: newJson,
      },
    ];
  }

  // Handle arrays
  if (Array.isArray(oldJson) && Array.isArray(newJson)) {
    // Use array indices as identifiers
    const maxLength = Math.max(oldJson.length, newJson.length);
    for (let i = 0; i < maxLength; i++) {
      if (i >= oldJson.length) {
        diffs.push({
          type: 'added',
          path: [...path, i.toString()],
          newValue: newJson[i],
        });
      } else if (i >= newJson.length) {
        diffs.push({
          type: 'removed',
          path: [...path, i.toString()],
          oldValue: oldJson[i],
        });
      } else {
        diffs.push(
          ...compareJson(oldJson[i], newJson[i], [...path, i.toString()])
        );
      }
    }
    return diffs;
  }

  // Handle objects
  if (
    oldJson &&
    newJson &&
    typeof oldJson === 'object' &&
    typeof newJson === 'object'
  ) {
    const allKeys = new Set([...Object.keys(oldJson), ...Object.keys(newJson)]);

    for (const key of allKeys) {
      if (!(key in oldJson)) {
        diffs.push({
          type: 'added',
          path: [...path, key],
          newValue: newJson[key],
        });
      } else if (!(key in newJson)) {
        diffs.push({
          type: 'removed',
          path: [...path, key],
          oldValue: oldJson[key],
        });
      } else {
        diffs.push(...compareJson(oldJson[key], newJson[key], [...path, key]));
      }
    }
    return diffs;
  }

  // Handle primitives
  if (oldJson !== newJson) {
    return [
      {
        type: 'modified',
        path,
        oldValue: oldJson,
        newValue: newJson,
      },
    ];
  }

  return diffs;
}

export const compareJsonDraftOperation = {
  name: 'compare_json_draft',
  description:
    'Compare two JSON drafts to identify changes in any JSON structure. ' +
    'Note: When comparing large JSON files (>100KB), the operation may take several seconds to process ' +
    'due to the detailed analysis of nested structures and arrays. ' +
    'The processing time scales with the size and complexity of the JSON structures being compared.\n\n' +
    '### Examples\n' +
    'Examples of cases when to use the tool and how to format the JSON:\n\n' +
    '1. Basic comparison:\n' +
    '   "Compare these two JSON drafts for tree 1 on mainnet"\n' +
    '   ```\n' +
    '   currentDraftJson: \'[{"id": "1", "details": "Original", "value": 5}]\'\n' +
    '   newDraftJson: \'[{"id": "1", "details": "Updated", "value": 10}]\'\n' +
    '   chain: "mainnet"\n' +
    '   chainId: 1\n' +
    '   treeId: 1\n' +
    '   ```\n\n' +
    '2. Complex structure comparison:\n' +
    '   "Compare these draft changes for my optimism tree"\n' +
    '   ```\n' +
    '   currentDraftJson: \'[{"id": "1", "nested": {"key": "old"}}\'\n' +
    '   newDraftJson: \'[{"id": "1", "nested": {"key": "new"}}\'\n' +
    '   chain: "optimism"\n' +
    '   chainId: 10\n' +
    '   treeId: 2\n' +
    '   ```\n\n' +
    '### Response Format\n' +
    'The response will include:\n' +
    '- Summary of total changes\n' +
    '- Counts of added, removed, and modified elements\n' +
    '- Detailed changes with exact paths and values\n' +
    '- Human-readable descriptions of all changes',
  parameters: compareJsonDraftParameters,

  async execute(args: z.infer<typeof compareJsonDraftParameters>) {
    console.log('\n=== Starting Compare Draft Operation ===');

    try {
      // Parse both JSON drafts with immediate size validation
      if (
        args.currentDraftJson.length > MAX_JSON_SIZE ||
        args.newDraftJson.length > MAX_JSON_SIZE
      ) {
        return createErrorResponse(
          'JSON input size exceeds maximum limit of 10MB'
        );
      }

      let currentJson: any;
      let newJson: any;

      try {
        currentJson = JSON.parse(args.currentDraftJson);
        newJson = JSON.parse(args.newDraftJson);
      } catch (error) {
        console.error('JSON parsing error:', error);
        return createErrorResponse(
          `Invalid JSON format: ${
            error instanceof Error ? error.message : 'unknown error'
          }`
        );
      }

      // Compare the JSON structures
      const diffs = compareJson(currentJson, newJson);

      // Generate summary and formatted results
      const summary = {
        totalChanges: diffs.length,
        added: diffs.filter((d) => d.type === 'added').length,
        removed: diffs.filter((d) => d.type === 'removed').length,
        modified: diffs.filter((d) => d.type === 'modified').length,
      };

      const formattedDiffs = diffs.map((diff) => ({
        type: diff.type,
        location: diff.path.join('.'),
        oldValue: diff.oldValue,
        newValue: diff.newValue,
        description: formatDiffDescription(diff),
      }));

      const result = {
        status: 'success',
        summary,
        changes: formattedDiffs,
      };

      // Handle large responses
      const resultSize = JSON.stringify(result).length;
      if (resultSize > 100000) {
        try {
          return chunkResponse(result);
        } catch (error) {
          console.error('Chunking error:', error);
          // Fall back to summary only
          return createJsonResponse({
            status: 'success',
            summary,
            note: 'Full changes omitted due to size - showing summary only',
          });
        }
      }

      return createJsonResponse(result);
    } catch (error) {
      console.error('Comparison error:', error);
      return createErrorResponse(
        `An error occurred while comparing drafts: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`
      );
    }
  },
};
