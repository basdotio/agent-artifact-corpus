import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import { createErrorResponse, createJsonResponse } from '../utils/response.js';
import { HatsSubgraphClient } from '@hatsprotocol/sdk-v1-subgraph';
import type {
  TreePropsConfig,
  HatPropsConfig,
  Hat as SubgraphHat,
  Wearer,
} from '@hatsprotocol/sdk-v1-subgraph';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';

import { getSubgraphClient } from '../utils/subgraph-client.js';

// Define the parameter schema for the operation
export const compareDraftParameters = z.object({
  draftJson: z
    .string()
    .describe('The exported JSON from Anchor containing the proposed changes'),
  chain: z
    .string()
    .describe('The chain name (e.g. "mainnet", "optimism", etc.)'),
  chainId: z
    .number()
    .describe('The chain ID (e.g. 1 for mainnet, 10 for optimism)'),
  treeId: z.number().describe('The ID of the tree to compare against'),
});

// Define interfaces for comparison
interface DraftHat {
  id: string;
  status?: boolean;
  maxSupply?: number;
  eligibility?: string;
  toggle?: string;
  mutable?: boolean;
  imageUri?: string;
  currentSupply?: number;
  wearers?: string[];
  adminId?: string;
  detailsObject?: {
    type: string;
    data: {
      name?: string;
      description?: string;
      responsibilities?: Array<{ link?: string; label?: string }>;
      authorities?: Array<{
        link?: string;
        label?: string;
        description?: string;
        gate?: string;
      }>;
      guilds?: string[];
      spaces?: string[];
      eligibility?: {
        manual: boolean;
        criteria: Array<{ link?: string; label?: string }>;
      };
      toggle?: {
        manual: boolean;
        criteria: Array<{ link?: string; label?: string }>;
      };
    };
  };
}

// Extend the SubgraphHat type to include our additional fields
interface ExtendedSubgraphHat extends SubgraphHat {
  detailsObject?: {
    type: string;
    data: {
      name?: string;
      description?: string;
      responsibilities?: Array<{ link?: string; label?: string }>;
      authorities?: Array<{
        link?: string;
        label?: string;
        description?: string;
        gate?: string;
      }>;
      guilds?: string[];
      spaces?: string[];
      eligibility?: {
        manual: boolean;
        criteria: Array<{ link?: string; label?: string }>;
      };
      toggle?: {
        manual: boolean;
        criteria: Array<{ link?: string; label?: string }>;
      };
    };
  };
}

interface StructuredChange {
  type: 'structural' | 'property' | 'role' | 'wearer';
  hatId: string;
  prettyId?: string;
  changeDescription: string;
  severity: 'high' | 'medium' | 'low';
  validationWarnings?: string[];
  ipfsNote?: string;
}

interface ComparisonResult {
  added: ExtendedSubgraphHat[];
  removed: ExtendedSubgraphHat[];
  modified: {
    hat: ExtendedSubgraphHat;
    changes: {
      field: string;
      oldValue: any;
      newValue: any;
      subField?: string;
    }[];
  }[];
  structuredChanges: StructuredChange[];
  validationIssues: {
    critical: string[];
    warnings: string[];
  };
  summary: {
    totalChanges: number;
    addedCount: number;
    removedCount: number;
    modifiedCount: number;
    changesByType: {
      structural: number;
      property: number;
      role: number;
      wearer: number;
    };
  };
}

function normalizeImageUri(uri: string): string {
  if (!uri) return '';
  // Remove gateway URLs and tokens if present
  if (uri.startsWith('https://')) {
    uri = uri.replace(/https:\/\/.*\/ipfs\//, 'ipfs://');
    uri = uri.replace(/\?.*$/, '');
  }
  return uri;
}

function normalizeValue(value: any): any {
  if (value === null || value === undefined) return value;

  // Convert numeric strings to numbers
  if (typeof value === 'string' && !isNaN(Number(value))) {
    return Number(value);
  }

  // Convert boolean strings to booleans
  if (value === 'true') return true;
  if (value === 'false') return false;

  return value;
}

function compareDetailsObjects(
  existing: any,
  draft: any
): Array<{ field: string; oldValue: any; newValue: any; subField?: string }> {
  const changes: Array<{
    field: string;
    oldValue: any;
    newValue: any;
    subField?: string;
  }> = [];

  if (!existing?.data || !draft?.data) return changes;

  const fields = [
    'name',
    'description',
    'responsibilities',
    'authorities',
    'guilds',
    'spaces',
  ];

  for (const field of fields) {
    const oldValue = existing.data[field];
    const newValue = draft.data[field];

    if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
      changes.push({
        field: 'detailsObject',
        oldValue,
        newValue,
        subField: field,
      });
    }
  }

  // Compare eligibility and toggle settings
  for (const setting of ['eligibility', 'toggle']) {
    if (existing.data[setting]?.manual !== draft.data[setting]?.manual) {
      changes.push({
        field: 'detailsObject',
        oldValue: existing.data[setting]?.manual,
        newValue: draft.data[setting]?.manual,
        subField: `${setting}.manual`,
      });
    }

    if (
      JSON.stringify(existing.data[setting]?.criteria) !==
      JSON.stringify(draft.data[setting]?.criteria)
    ) {
      changes.push({
        field: 'detailsObject',
        oldValue: existing.data[setting]?.criteria,
        newValue: draft.data[setting]?.criteria,
        subField: `${setting}.criteria`,
      });
    }
  }

  return changes;
}

function validateHatChanges(
  existingHat: ExtendedSubgraphHat | undefined,
  draftHat: DraftHat,
  result: ComparisonResult
): string[] {
  const warnings: string[] = [];

  // Validate structural integrity
  if (draftHat.adminId) {
    const adminExists =
      result.added.some((h) => h.id === draftHat.adminId) ||
      existingHat !== undefined;
    if (!adminExists) {
      warnings.push(`Admin hat ${draftHat.adminId} not found in tree`);
    }
  }

  // Validate supply constraints
  if (
    draftHat.maxSupply !== undefined &&
    draftHat.currentSupply !== undefined
  ) {
    if (draftHat.maxSupply < draftHat.currentSupply) {
      warnings.push(
        `maxSupply (${draftHat.maxSupply}) is less than currentSupply (${draftHat.currentSupply})`
      );
    }
  }

  // Validate eligibility/toggle modules
  if (
    draftHat.eligibility &&
    draftHat.eligibility !== '0x0000000000000000000000000000000000000000'
  ) {
    if (
      !draftHat.toggle ||
      draftHat.toggle === '0x0000000000000000000000000000000000000000'
    ) {
      warnings.push('Hat has eligibility module but no toggle module');
    }
  }

  return warnings;
}

function classifyChange(
  field: string,
  oldValue: any,
  newValue: any,
  subField?: string
): StructuredChange['type'] {
  if (field === 'detailsObject') {
    if (subField?.includes('eligibility') || subField?.includes('toggle')) {
      return 'role';
    }
    return 'property';
  }

  switch (field) {
    case 'maxSupply':
    case 'mutable':
    case 'eligibility':
    case 'toggle':
      return 'role';
    case 'status':
      return 'structural';
    case 'wearers':
      return 'wearer';
    default:
      return 'property';
  }
}

function determineSeverity(
  changeType: StructuredChange['type'],
  field: string,
  oldValue: any,
  newValue: any
): StructuredChange['severity'] {
  if (changeType === 'structural') return 'high';
  if (field === 'eligibility' || field === 'toggle') return 'high';
  if (field === 'maxSupply' && newValue < oldValue) return 'high';
  if (changeType === 'role') return 'medium';
  return 'low';
}

async function compareHats(
  existingTree: { hats?: SubgraphHat[] },
  draftHats: DraftHat[]
): Promise<ComparisonResult> {
  console.log('\n=== Starting compareHats ===');
  console.log('Existing tree hats:', existingTree.hats?.length || 0);
  console.log('Draft hats:', draftHats.length);

  const result: ComparisonResult = {
    added: [],
    removed: [],
    modified: [],
    structuredChanges: [],
    validationIssues: {
      critical: [],
      warnings: [],
    },
    summary: {
      totalChanges: 0,
      addedCount: 0,
      removedCount: 0,
      modifiedCount: 0,
      changesByType: {
        structural: 0,
        property: 0,
        role: 0,
        wearer: 0,
      },
    },
  };

  const existingHats = existingTree.hats || [];

  // Find added and modified hats
  for (const draftHat of draftHats) {
    console.log('\nProcessing draft hat:', draftHat.id);
    const existingHat = existingHats.find((h) => h.id === draftHat.id);

    // Validate changes
    const validationWarnings = validateHatChanges(
      existingHat as ExtendedSubgraphHat,
      draftHat,
      result
    );
    if (validationWarnings.length > 0) {
      console.log(
        'Validation warnings for hat:',
        draftHat.id,
        validationWarnings
      );
      result.validationIssues.warnings.push(...validationWarnings);
    }

    if (!existingHat) {
      console.log('New hat found:', draftHat.id);
      result.added.push(draftHat as unknown as ExtendedSubgraphHat);
      result.summary.addedCount++;

      result.structuredChanges.push({
        type: 'structural',
        hatId: draftHat.id,
        prettyId: draftHat.id,
        changeDescription: `Added new hat ${draftHat.id}`,
        severity: 'high',
        validationWarnings,
      });

      result.summary.changesByType.structural++;
      continue;
    }

    console.log('Comparing hat:', draftHat.id);
    const changes = [];
    const structuredChanges: StructuredChange[] = [];

    // Compare properties
    for (const prop of [
      'status',
      'maxSupply',
      'eligibility',
      'toggle',
      'mutable',
      'currentSupply',
      'imageUri',
    ]) {
      const existingValue = normalizeValue((existingHat as any)[prop]);
      const draftValue = normalizeValue((draftHat as any)[prop]);

      if (JSON.stringify(existingValue) !== JSON.stringify(draftValue)) {
        console.log(`Property change detected - ${prop}:`, {
          old: existingValue,
          new: draftValue,
        });

        const changeType = classifyChange(prop, existingValue, draftValue);
        const severity = determineSeverity(
          changeType,
          prop,
          existingValue,
          draftValue
        );

        changes.push({
          field: prop,
          oldValue: existingValue,
          newValue: draftValue,
        });

        structuredChanges.push({
          type: changeType,
          hatId: draftHat.id,
          prettyId: existingHat.prettyId,
          changeDescription: `Changed ${prop} from ${existingValue} to ${draftValue}`,
          severity,
          validationWarnings: validationWarnings.filter((w) =>
            w.includes(prop)
          ),
        });

        result.summary.changesByType[changeType]++;
      }
    }

    // Handle detailsObject changes
    console.log('Comparing detailsObject...');
    const detailsChanges = compareDetailsObjects(
      (existingHat as unknown as ExtendedSubgraphHat).detailsObject,
      draftHat.detailsObject
    );

    if (detailsChanges.length > 0) {
      console.log('DetailsObject changes found:', detailsChanges.length);
    }

    for (const change of detailsChanges) {
      const changeType = classifyChange(
        'detailsObject',
        change.oldValue,
        change.newValue,
        change.subField
      );
      const severity = determineSeverity(
        changeType,
        'detailsObject',
        change.oldValue,
        change.newValue
      );

      changes.push(change);

      if (change.subField?.includes('ipfs')) {
        structuredChanges.push({
          type: changeType,
          hatId: draftHat.id,
          prettyId: existingHat.prettyId,
          changeDescription: `Modified ${change.subField}`,
          severity,
          ipfsNote: 'IPFS content changes require manual verification',
        });
      } else {
        structuredChanges.push({
          type: changeType,
          hatId: draftHat.id,
          prettyId: existingHat.prettyId,
          changeDescription: `Modified ${change.subField || 'details'}`,
          severity,
        });
      }

      result.summary.changesByType[changeType]++;
    }

    if (changes.length > 0) {
      console.log('Total changes for hat:', changes.length);
      result.modified.push({
        hat: existingHat as ExtendedSubgraphHat,
        changes,
      });
      result.structuredChanges.push(...structuredChanges);
      result.summary.modifiedCount++;
    }
  }

  // Find removed hats
  for (const existingHat of existingHats) {
    if (!draftHats.some((d) => d.id === existingHat.id)) {
      result.removed.push(existingHat as ExtendedSubgraphHat);
      result.summary.removedCount++;

      result.structuredChanges.push({
        type: 'structural',
        hatId: existingHat.id,
        prettyId: existingHat.prettyId,
        changeDescription: `Removed hat ${existingHat.id}`,
        severity: 'high',
      });

      result.summary.changesByType.structural++;
    }
  }

  result.summary.totalChanges =
    result.summary.addedCount +
    result.summary.removedCount +
    result.summary.modifiedCount;

  return result;
}

export const compareDraftOperation = {
  name: 'compare_draft',
  description:
    'Compare a draft JSON export from Anchor against the current on-chain tree state.\n\n' +
    '### Important Note on Metadata\n' +
    'The current on-chain state returns IPFS hashes for hat details (metadata) rather than the decoded content. ' +
    'This means that metadata comparisons (names, descriptions, etc.) between the draft and current state ' +
    'will show as changes even when they may be identical, since we are comparing decoded content against IPFS hashes.\n\n' +
    'For accurate metadata comparison:\n' +
    '1. Changes to non-metadata fields (maxSupply, eligibility, etc.) are accurately compared\n' +
    '2. Metadata changes should be verified separately by fetching the IPFS content\n' +
    '3. Focus on structural and permission changes rather than metadata differences\n',
  parameters: compareDraftParameters,

  async execute(args: z.infer<typeof compareDraftParameters>) {
    console.log('\n=== Starting Compare Draft Operation ===');
    console.log('Args:', JSON.stringify(args, null, 2));

    try {
      // Validate chain support
      if (!isChainSupported(args.chain)) {
        const supportedChains = getSupportedChains().join(', ');
        console.log('Chain validation failed:', args.chain);
        return createErrorResponse(
          `Chain "${args.chain}" is not supported. Please use one of the supported chains: ${supportedChains}`
        );
      }
      console.log('Chain validation passed:', args.chain);

      // Parse draft JSON
      let draftHats: DraftHat[];
      try {
        console.log('Attempting to parse draft JSON...');
        draftHats = JSON.parse(args.draftJson);
        console.log(
          'Successfully parsed draft JSON. Hat count:',
          draftHats.length
        );
      } catch (error) {
        console.error('Draft JSON parse error:', error);
        return createErrorResponse('Invalid draft JSON format');
      }

      // Get current tree state with a single query
      console.log('Getting subgraph client...');
      const client = getSubgraphClient();
      const props: TreePropsConfig = {
        hats: {
          props: {
            prettyId: true,
            status: true,
            details: true,
            maxSupply: true,
            eligibility: true,
            toggle: true,
            mutable: true,
            imageUri: true,
            currentSupply: true,
          } as HatPropsConfig,
        },
      };

      console.log('Fetching existing tree data for:', {
        chainId: args.chainId,
        treeId: args.treeId,
      });

      const existingTree = await client.getTree({
        chainId: args.chainId,
        treeId: args.treeId,
        props,
      });

      console.log(
        'Existing tree data fetched. Hat count:',
        existingTree.hats?.length || 0
      );

      // Compare draft against current state
      console.log('Starting hat comparison...');
      const finalResult = await compareHats(existingTree, draftHats);
      console.log('Comparison completed:', {
        totalChanges: finalResult.summary.totalChanges,
        added: finalResult.added.length,
        removed: finalResult.removed.length,
        modified: finalResult.modified.length,
      });

      return createJsonResponse(finalResult);
    } catch (error) {
      console.error('Error in compare draft operation:', error);
      if (error instanceof Error) {
        console.error('Error stack:', error.stack);
      }
      return createErrorResponse(
        `An error occurred while comparing draft: ${
          error instanceof Error ? error.message : 'Unknown error'
        }`
      );
    }
  },
};
