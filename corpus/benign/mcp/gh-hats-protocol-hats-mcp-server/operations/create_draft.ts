import { z } from 'zod';
import {
  createErrorResponse,
  createJsonResponse,
  chunkResponse,
} from '../utils/response.js';
import type {
  TreePropsConfig,
  HatPropsConfig,
  Hat as SubgraphHat,
  Wearer,
  HatsSubgraphClient,
} from '@hatsprotocol/sdk-v1-subgraph';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';
import {
  fetchIpfs,
  pinJson,
  getTemporaryToken,
  ipfsUrl,
} from '../utils/ipfs.js';
import { getSubgraphClient } from '../utils/subgraph-client.js';
import type {
  Tree,
  Hat,
  WearerPropsConfig,
} from '@hatsprotocol/sdk-v1-subgraph';

// Define the base types
interface HatDetails {
  type: string;
  data: {
    name: string;
    description: string;
    responsibilities: any[];
    authorities: any[];
    guilds: any[];
    spaces: any[];
    eligibility: { manual: boolean; criteria: any[] };
    toggle: { manual: boolean; criteria: any[] };
  };
}

interface BaseHat {
  id?: string;
  status?: boolean;
  createdAt?: string | number;
  details?: string;
  maxSupply?: number;
  eligibility?: string;
  toggle?: string;
  imageUri?: string;
  wearers?: string[];
  mutable?: boolean;
  currentSupply?: number;
  detailsObject?: HatDetails;
  [key: string]: unknown;
}

interface HatTreeNode extends BaseHat {
  id?: string;
  status?: boolean;
  createdAt?: number | string;
  maxSupply?: number;
  eligibility?: string;
  toggle?: string;
  mutable?: boolean;
  currentSupply?: number;
  wearers?: string[];
  adminId?: string;
  imageUri?: string;
  details?: string;
  detailsObject?: HatDetails;
  subHats?: HatTreeNode[];
}

// Define the base modification type without recursive subHats
interface BaseHatModification {
  id?: string;
  details?: string;
  maxSupply?: number;
  eligibility?: string;
  toggle?: string;
  imageUri?: string;
  wearers?: string[];
  status?: boolean;
  mutable?: boolean;
}

// Extend the base type to include recursive subHats
interface HatModification {
  id: string;
  details?: string;
  maxSupply?: number;
  eligibility?: string;
  toggle?: string;
  imageUri?: string;
  wearers?: string[];
  status?: boolean;
  mutable?: boolean;
  detailsObject?: {
    type: string;
    data: {
      name: string;
      description: string;
      responsibilities: any[];
      authorities: any[];
      guilds: any[];
      spaces: any[];
      eligibility: {
        manual: boolean;
        criteria: any[];
      };
      toggle: {
        manual: boolean;
        criteria: any[];
      };
    };
  };
  subHats?: HatModification[];
}

// Update the validation schema to use 'id' instead of 'prettyId'
const hatModificationSchema: z.ZodType<HatModification> = z
  .object({
    id: z.string(),
    details: z.string().optional(),
    maxSupply: z.number().optional(),
    eligibility: z.string().optional(),
    toggle: z.string().optional(),
    imageUri: z.string().optional(),
    wearers: z.array(z.string()).optional(),
    status: z.boolean().optional(),
    mutable: z.boolean().optional(),
    detailsObject: z
      .object({
        type: z.string(),
        data: z.object({
          name: z.string(),
          description: z.string(),
          responsibilities: z.array(z.any()),
          authorities: z.array(z.any()),
          guilds: z.array(z.any()),
          spaces: z.array(z.any()),
          eligibility: z.object({
            manual: z.boolean(),
            criteria: z.array(z.any()),
          }),
          toggle: z.object({
            manual: z.boolean(),
            criteria: z.array(z.any()),
          }),
        }),
      })
      .optional(),
    subHats: z.array(z.lazy(() => hatModificationSchema)).optional(),
  })
  .refine(
    (data) => {
      // Ensure at least one field other than id is being modified
      return Object.keys(data).some(
        (key) => key !== 'id' && data[key as keyof typeof data] !== undefined
      );
    },
    {
      message: 'At least one field must be modified besides id',
    }
  );

// Schema for the operation parameters
export const parameters = z.object({
  treeId: z.number(),
  chain: z.string(),
  chainId: z.number(),
  mode: z.enum(['preview', 'apply']).default('preview'),
  modifications: z.array(hatModificationSchema),
  currentTreeJson: z.string(),
});

export const description = `Create a draft JSON export representing proposed modifications to a hat tree.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Preview changes:
  "Show me what changes would happen if I add a new subhat under hat 0x1234 in tree 1 on mainnet"
  {
    "treeId": 1,
    "chain": "mainnet",
    "chainId": 1,
    "mode": "preview",
    "currentTreeJson": "{...}",  // Current tree state as JSON string (required)
    "modifications": [{
      "id": "0x1234.1",
      "details": "New subhat",
      "maxSupply": 10
    }]
  }

- Apply changes after review:
  "Apply the changes we just previewed to tree 2 on optimism"
  {
    "treeId": 2,
    "chain": "optimism",
    "chainId": 10,
    "mode": "apply",
    "currentTreeJson": "{...}",  // Current tree state as JSON string (required)
    "modifications": [{
      "id": "0x5678",
      "details": "Updated role description",
      "subHats": [{
        "details": "New subrole",
        "maxSupply": 5
      }]
    }]
  }

### Interaction Flow
1. First call with mode="preview" to see proposed changes
2. Review the changes in a readable format
3. Make additional modifications if needed
4. Call with mode="apply" to generate the final draft

### Parameters
- treeId: The ID of the tree to modify
- chain: The chain name (e.g. "mainnet", "optimism")
- chainId: The chain ID (e.g. 1 for mainnet, 10 for optimism)
- mode: "preview" or "apply" (defaults to "preview")
- modifications: Array of hat modifications to apply
- currentTreeJson: Current tree state as JSON string (required)

### Response Format
The response will include:
- Summary of changes in human-readable format
- Validation results and potential issues
- Full diff for review (in preview mode)
- Complete draft tree JSON (in apply mode)`;

export const execute = async (args: z.infer<typeof parameters>) => {
  try {
    console.log('=== Starting create_draft execution ===');
    console.log('Arguments:', args);

    // Validate chain support
    if (!isChainSupported(args.chain)) {
      const supportedChains = getSupportedChains().join(', ');
      return createErrorResponse(
        `Chain "${args.chain}" is not supported. Please use one of the supported chains: ${supportedChains}`
      );
    }
    console.log('Chain validation passed');

    let currentTree;

    // Check if currentTreeJson is provided
    if (args.currentTreeJson) {
      try {
        console.log('Using provided tree JSON...');
        currentTree = JSON.parse(args.currentTreeJson);
      } catch (error) {
        return createErrorResponse('Invalid JSON provided for currentTreeJson');
      }
    } else {
      return createErrorResponse(
        'currentTreeJson is required for draft creation'
      );
    }

    // Convert Tree to HatTreeNode format
    console.log('Converting tree to HatTreeNode...');
    const currentHatTree = convertTreeToHatNode(currentTree);
    console.log('Tree converted');

    // Apply modifications to create draft tree
    console.log('Applying modifications...');
    const draftTree = applyModificationsToTree(
      currentHatTree,
      args.modifications
    );
    console.log('Modifications applied');

    // Validate the draft tree
    console.log('Validating draft tree...');
    const validationResults = validateDraftTree(draftTree, args.modifications);
    console.log('Validation results:', validationResults);

    if (!validationResults.isValid) {
      return createErrorResponse(
        `Invalid draft tree: ${validationResults.issues.join(', ')}`
      );
    }

    // Generate diff between current and draft
    console.log('Generating tree diff...');
    const currentTreeArray = Array.isArray(currentHatTree)
      ? currentHatTree
      : [currentHatTree];
    const draftTreeArray = Array.isArray(draftTree) ? draftTree : [draftTree];
    const treeDiff = generateTreeDiff(currentTreeArray, draftTreeArray);
    console.log('Tree diff generated');

    // Create a human-readable summary
    console.log('Creating summary...');
    const summary = generateChangesSummary(treeDiff);
    console.log('Summary created');

    // For preview mode, return the preview data
    if (args.mode === 'preview') {
      console.log('Returning preview response');
      return createJsonResponse({
        status: 'success',
        mode: 'preview',
        data: {
          summary,
          validationResults,
          treeDiff,
        },
      });
    }

    // For apply mode, prepare the data for pinning and pin to IPFS
    console.log('Preparing apply mode data...');
    const flattenedHats = flattenTree(draftTreeArray);

    // Convert to array format matching chain-42161-tree-80.json
    const hatsArray = Array.from(flattenedHats).map((hat) => ({
      id: hat.id,
      status: hat.status,
      createdAt: hat.createdAt,
      maxSupply: hat.maxSupply,
      eligibility: hat.eligibility,
      toggle: hat.toggle,
      mutable: hat.mutable,
      currentSupply: hat.currentSupply,
      wearers: hat.wearers || [],
      adminId: hat.adminId,
      imageUri: hat.imageUri || '',
      detailsObject: {
        type: '1.0',
        data: {
          name: hat.detailsObject?.data?.name || '',
          description: hat.detailsObject?.data?.description || '',
          responsibilities: hat.detailsObject?.data?.responsibilities || [],
          authorities: hat.detailsObject?.data?.authorities || [],
          guilds: hat.detailsObject?.data?.guilds || [],
          spaces: hat.detailsObject?.data?.spaces || [],
          eligibility: {
            manual: hat.detailsObject?.data?.eligibility?.manual || true,
            criteria: hat.detailsObject?.data?.eligibility?.criteria || [],
          },
          toggle: {
            manual: hat.detailsObject?.data?.toggle?.manual || true,
            criteria: hat.detailsObject?.data?.toggle?.criteria || [],
          },
        },
      },
    }));

    // Create metadata object
    const metadata = {
      name: `Tree ${args.treeId} - ${args.chain}`,
      chain: args.chain,
      chainId: args.chainId,
      treeId: args.treeId,
      timestamp: new Date().toISOString(),
    };

    // Create the final output object with hats array and metadata separate
    const outputObject = {
      hats: hatsArray,
      metadata,
    };

    // Create Pinata metadata (required for successful pinning)
    const pinataMetadata = {
      name: `Tree ${args.treeId} Draft - Chain ${args.chainId}`,
      keyvalues: {
        chain: args.chain,
        chainId: args.chainId.toString(),
        treeId: args.treeId.toString(),
        timestamp: new Date().toISOString(),
      },
    };

    // Pin the new JSON to IPFS
    console.log('Pinning new draft JSON to IPFS...');
    const token = await getTemporaryToken();
    if (!token) {
      return createErrorResponse('Failed to get temporary IPFS token');
    }

    // Log the structure to verify format
    console.log('Data structure check:', {
      hatsLength: outputObject.hats.length,
      sampleHat: outputObject.hats[0],
      metadata: outputObject.metadata,
    });

    let ipfsHash: string | null = null;
    try {
      // Pin the object directly with Pinata metadata
      ipfsHash = await pinJson(outputObject, pinataMetadata, token);
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      return createErrorResponse(
        `Failed to pin draft JSON to IPFS: ${errorMsg}`
      );
    }
    const ipfsLink = ipfsHash ? ipfsUrl(ipfsHash) : null;

    // Return the response with both the IPFS link and the clean object
    return createJsonResponse({
      status: 'success',
      mode: 'apply',
      data: {
        ipfsLink,
        ipfsHash,
        draft: outputObject,
        summary,
        validationResults,
        treeDiff,
      },
    });
  } catch (error) {
    console.error('Error in create_draft:', error);
    return createErrorResponse(
      error instanceof Error ? error.message : String(error)
    );
  }
};

// Helper function to convert Tree to HatTreeNode array
function convertTreeToHatNode(tree: Tree): HatTreeNode[] {
  const convertHat = (hat: BaseHat): HatTreeNode => ({
    ...hat,
    subHats: Array.isArray(hat.subHats) ? hat.subHats.map(convertHat) : [],
  });

  // If tree is an array, convert each hat
  if (Array.isArray(tree)) {
    return tree.map((hat) => convertHat(hat as BaseHat));
  }

  // If tree has hats property, convert those
  if ('hats' in tree && Array.isArray(tree.hats)) {
    return tree.hats.map((hat) => convertHat(hat as BaseHat));
  }

  // Single hat case
  return [convertHat(tree as BaseHat)];
}

// Helper function to validate the draft tree
function validateDraftTree(
  tree: HatTreeNode | HatTreeNode[],
  modifications: HatModification[]
) {
  const issues: string[] = [];
  const treeArray = Array.isArray(tree) ? tree : [tree];

  // Find which hats are being modified
  const modifiedHatIds = new Set(modifications.map((mod) => mod.id || ''));

  treeArray.forEach((hat) =>
    validateHatNode(hat, issues, modifiedHatIds.has(hat.id || ''))
  );

  return {
    isValid: issues.length === 0,
    issues,
  };
}

// Helper function to validate a single hat node
function validateHatNode(
  hat: HatTreeNode,
  issues: string[],
  isModification = false
) {
  console.log('Validating hat:', JSON.stringify(hat, null, 2));

  // For existing hats in the tree, we don't need to validate all fields
  if (hat.id && !isModification) {
    return; // Skip validation for existing unmodified hats
  }

  // For modifications or new hats, validate the changed fields
  if (!hat.id) {
    console.log(
      'Missing identification for hat:',
      JSON.stringify(hat, null, 2)
    );
    issues.push(`Missing id for hat`);
    return;
  }

  // Only validate maxSupply if it's being modified and is not zero
  if (hat.maxSupply !== undefined && hat.maxSupply !== 0) {
    if (typeof hat.maxSupply !== 'number' || hat.maxSupply < 0) {
      console.log('Invalid maxSupply for hat:', hat.id, hat.maxSupply);
      issues.push(
        `Invalid maxSupply for hat ${hat.id}: must be non-negative number`
      );
    }
  }

  // Only validate addresses if they're being modified
  if (hat.eligibility && !/^0x[a-fA-F0-9]{40}$/.test(hat.eligibility)) {
    issues.push(`Invalid eligibility address for hat ${hat.id}`);
  }
  if (hat.toggle && !/^0x[a-fA-F0-9]{40}$/.test(hat.toggle)) {
    issues.push(`Invalid toggle address for hat ${hat.id}`);
  }

  // Only validate detailsObject if it's being modified
  if (hat.detailsObject && isModification) {
    if (!hat.detailsObject.type) {
      issues.push(`Missing detailsObject.type for hat ${hat.id}`);
    }
    if (!hat.detailsObject.data) {
      issues.push(`Missing detailsObject.data for hat ${hat.id}`);
    } else {
      const { data } = hat.detailsObject;
      if (!data.name) {
        issues.push(`Missing detailsObject.data.name for hat ${hat.id}`);
      }
      // Only validate eligibility/toggle if they're being modified
      if (data.eligibility === undefined) {
        issues.push(`Missing detailsObject.data.eligibility for hat ${hat.id}`);
      }
      if (data.toggle === undefined) {
        issues.push(`Missing detailsObject.data.toggle for hat ${hat.id}`);
      }
    }
  }

  // Recursively validate subhats if present
  if (hat.subHats && Array.isArray(hat.subHats)) {
    console.log('Validating subhats for:', hat.id);
    hat.subHats.forEach((subHat) =>
      validateHatNode(subHat, issues, isModification)
    );
  }
}

// Helper function: deep clone
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

// Helper function: recursively apply modifications to the tree
function applyModificationsToTree(
  originalTree: HatTreeNode[] | HatTreeNode,
  modifications: HatModification[]
): HatTreeNode[] | HatTreeNode {
  const treeArray = Array.isArray(originalTree)
    ? deepClone(originalTree)
    : [deepClone(originalTree)];

  for (const mod of modifications) {
    // Use 'id' for matching, not 'prettyId'
    const hat = treeArray.find((h) => h.id === mod.id);
    if (hat) {
      Object.entries(mod).forEach(([key, value]) => {
        if (key !== 'id' && value !== undefined) {
          if (key === 'wearers' && Array.isArray(value)) {
            hat.wearers = Array.from(
              new Set([...(hat.wearers || []), ...value])
            );
          } else {
            (hat as any)[key] = value;
          }
        }
      });
    }
    // Do not insert as new if not found
  }

  return Array.isArray(originalTree) ? treeArray : treeArray[0];
}

// Helper function to create a new hat with all required fields
function createNewHat(mod: HatModification): HatTreeNode {
  // Start with a minimal new hat structure
  const hat: HatTreeNode = {
    id: mod.id || '',
  };

  // Only add fields that are explicitly provided in the modification
  Object.keys(mod).forEach((key) => {
    const value = mod[key as keyof HatModification];
    if (value !== undefined) {
      (hat as any)[key] = value;
    }
  });

  return hat;
}

// Helper function to find a hat by id
function findHatById(
  tree: HatTreeNode | HatTreeNode[],
  id: string
): HatTreeNode | null {
  // Ensure we're working with an array
  const treeArray = Array.isArray(tree) ? tree : [tree];

  for (const hat of treeArray) {
    if (hat.id === id) return hat;
    if (hat.subHats && Array.isArray(hat.subHats)) {
      const found = findHatById(hat.subHats, id);
      if (found) return found;
    }
  }
  return null;
}

// Update generateTreeDiff to show clearer changes
function generateTreeDiff(
  currentTree: HatTreeNode[],
  draftTree: HatTreeNode[]
): TreeDiff {
  const diff: TreeDiff = {
    modified: [],
  };

  // Helper to get hat name
  const getHatName = (hat: HatTreeNode) =>
    hat.detailsObject?.data?.name || 'Unnamed Hat';

  // Compare nodes recursively
  function compareNodes(current: HatTreeNode[], draft: HatTreeNode[]) {
    for (const draftHat of draft) {
      const currentHat = current.find((h) => h.id === draftHat.id);
      if (currentHat) {
        const changes: Record<string, Change> = {};

        // Check each field for changes
        Object.entries(draftHat).forEach(([key, value]) => {
          if (
            key !== 'subHats' &&
            JSON.stringify(currentHat[key]) !== JSON.stringify(value)
          ) {
            changes[key] = {
              from: currentHat[key],
              to: value,
              description: getChangeDescription(key, currentHat[key], value),
            };
          }
        });

        if (Object.keys(changes).length > 0) {
          diff.modified.push({
            id: draftHat.id || '',
            name: getHatName(draftHat),
            changes,
          });
        }

        // Recurse into subHats
        if (draftHat.subHats && currentHat.subHats) {
          compareNodes(currentHat.subHats, draftHat.subHats);
        }
      }
    }
  }

  compareNodes(currentTree, draftTree);
  return diff;
}

// Helper to generate human-readable change descriptions
function getChangeDescription(field: string, from: any, to: any): string {
  switch (field) {
    case 'maxSupply':
      return `Maximum supply changed from ${from || 'unlimited'} to ${
        to || 'unlimited'
      }`;
    case 'wearers':
      const fromArray = Array.isArray(from) ? from : [];
      const toArray = Array.isArray(to) ? to : [];
      const added = toArray.filter((w) => !fromArray.includes(w));
      const removed = fromArray.filter((w) => !toArray.includes(w));
      const changes = [];
      if (added.length)
        changes.push(
          `Added wearer${added.length > 1 ? 's' : ''}: ${added.join(', ')}`
        );
      if (removed.length)
        changes.push(
          `Removed wearer${removed.length > 1 ? 's' : ''}: ${removed.join(
            ', '
          )}`
        );
      return changes.join('\n  - ');
    case 'eligibility':
      return `Eligibility module changed from ${from || 'none'} to ${
        to || 'none'
      }`;
    case 'toggle':
      return `Toggle module changed from ${from || 'none'} to ${to || 'none'}`;
    case 'status':
      return `Hat ${to ? 'activated' : 'deactivated'}`;
    case 'mutable':
      return `Hat mutability ${to ? 'enabled' : 'disabled'}`;
    case 'imageUri':
      return `Image URI ${from ? 'updated' : 'set'} to ${to || 'none'}`;
    case 'detailsObject':
      const fromName = from?.data?.name || 'unnamed';
      const toName = to?.data?.name || 'unnamed';
      if (fromName !== toName) {
        return `Name changed from "${fromName}" to "${toName}"`;
      }
      return 'Metadata updated';
    default:
      if (typeof from === 'object' || typeof to === 'object') {
        return `${field} updated`;
      }
      return `${field} changed from ${from || 'none'} to ${to || 'none'}`;
  }
}

// Helper function to flatten the tree
function flattenTree(tree: HatTreeNode[]): HatTreeNode[] {
  const flattened: HatTreeNode[] = [];

  function traverse(node: HatTreeNode) {
    flattened.push(node);
    if (node.subHats && Array.isArray(node.subHats)) {
      node.subHats.forEach(traverse);
    }
  }

  tree.forEach(traverse);
  return flattened;
}

// Add these interfaces near the top with other interfaces
interface Change {
  from: unknown;
  to: unknown;
  description: string;
}

interface ModifiedHat {
  id: string;
  name: string;
  changes: Record<string, Change>;
}

interface TreeDiff {
  modified: ModifiedHat[];
}

// Update the generateChangesSummary function
function generateChangesSummary(diff: TreeDiff) {
  const { modified } = diff;
  if (!modified || modified.length === 0) {
    return 'No changes detected';
  }

  const summaryParts = modified.map(({ id, name, changes }) => {
    const changeDescriptions = Object.entries(changes)
      .map(([field, { description }]) => `  - ${description}`)
      .join('\n');

    return `Changes to ${name} (${id}):\n${changeDescriptions}`;
  });

  return summaryParts.join('\n\n');
}
