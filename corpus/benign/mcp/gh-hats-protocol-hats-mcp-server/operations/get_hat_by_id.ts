import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type {
  HatsSubgraphClient,
  HatPropsConfig,
} from '@hatsprotocol/sdk-v1-subgraph';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';
import { fetchIpfs } from '../utils/ipfs.js';
import {
  getModuleInfo,
  getEligibilityRules,
  checkHatEligibility,
} from '../utils/modules.js';
import { normalizeHatId } from '../utils/hat-utils.js';
import type { Address } from 'viem';
import { chunkResponse } from '../utils/response.js';
import { getSubgraphClient } from '../utils/subgraph-client.js';

interface HatDetailsContent {
  name?: string;
  description?: string;
  guilds?: string[];
  spaces?: string[];
  responsibilities?: Array<{
    link?: string;
    label?: string;
  }>;
  authorities?: Array<{
    link?: string;
    label?: string;
    description?: string;
    gate?: string;
  }>;
  eligibility?: {
    manual: boolean;
    criteria: Array<{ link?: string; label?: string }>;
  };
  toggle?: {
    manual: boolean;
    criteria: Array<{ link?: string; label?: string }>;
  };
}

interface ModuleDetails {
  details?: {
    name?: string;
    id?: string;
    version?: string;
  };
  parameters?: Array<{
    label: string;
    value: unknown;
    solidityType: string;
    displayType: string;
  }>;
  rules?: unknown;
}

interface EnrichedHat {
  id: string;
  name: string;
  prettyId: string;
  status: boolean;
  details: string;
  maxSupply: string;
  eligibility: string | null;
  toggle: string | null;
  mutable: boolean;
  imageUri: string;
  levelAtLocalTree: number;
  currentSupply: string;
  detailsDecoded: HatDetailsContent;
  moduleInfo: {
    eligibility?: ModuleDetails;
    toggle?: ModuleDetails;
  };
  subHats: Array<{
    id: string;
    prettyId: string;
    status: boolean;
  }>;
  wearers: Array<{
    id: string;
    currentHats: Array<{
      id: string;
      prettyId: string;
      status: boolean;
    }>;
    _totalHats: number;
  }>;
}

interface SubgraphHat {
  id: string | bigint;
  prettyId: string;
  status: boolean;
  details: string;
  maxSupply: string | bigint;
  eligibility: string | null;
  toggle: string | null;
  mutable: boolean;
  imageUri: string;
  levelAtLocalTree: number;
  currentSupply: string | bigint;
  subHats?: Array<{
    id: string | bigint;
    prettyId: string;
    status: boolean;
  }>;
  wearers?: Array<{
    id: string;
    currentHats?: Array<{
      id: string | bigint;
      prettyId: string;
      status: boolean;
    }>;
  }>;
}

// Add this utility function near the top with other interfaces
function serializeBigInts(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (typeof obj === 'bigint') {
    return obj.toString();
  }

  if (Array.isArray(obj)) {
    return obj.map(serializeBigInts);
  }

  if (typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj).map(([key, value]) => [key, serializeBigInts(value)])
    );
  }

  return obj;
}

async function smartHatLookup(
  args: z.infer<typeof parameters>,
  client: HatsSubgraphClient
): Promise<CallToolResult> {
  console.log('\n=== Starting Smart Hat Lookup ===');

  // Use the improved normalizeHatId function from hat-utils
  const normalizedHatId = normalizeHatId(args.hatId);
  console.log(`Normalized hat ID from ${args.hatId} to ${normalizedHatId}`);

  const hatProps: HatPropsConfig = {
    prettyId: true,
    status: true,
    details: true,
    maxSupply: true,
    eligibility: true,
    toggle: true,
    mutable: true,
    imageUri: true,
    levelAtLocalTree: true,
    currentSupply: true,
    subHats: {
      props: {
        prettyId: true,
        status: true,
      },
    },
    wearers: {
      props: {
        currentHats: {
          props: {
            prettyId: true,
            status: true,
          },
        },
      },
    },
  };

  try {
    const hat = await client.getHat({
      chainId: args.chainId,
      hatId: BigInt(normalizedHatId),
      props: hatProps,
    });

    if (!hat) {
      return {
        _meta: {},
        content: [
          {
            type: 'text',
            text: `No hat found with ID ${normalizedHatId} on chain ${args.chain}`,
          },
        ],
      };
    }

    // Initialize content objects
    let detailsContent: HatDetailsContent = {};
    let imageContent = '';

    if (hat.details) {
      const ipfsResult = await fetchIpfs(hat.details);
      if (ipfsResult?.data) {
        try {
          // Handle both string and object responses
          const resolvedDetails =
            typeof ipfsResult.data === 'string'
              ? JSON.parse(ipfsResult.data)
              : ipfsResult.data;

          // Safely assign values with fallbacks
          detailsContent.name =
            resolvedDetails.name || resolvedDetails.data?.name || '';
          detailsContent.description =
            resolvedDetails.description ||
            resolvedDetails.data?.description ||
            '';
          detailsContent.guilds =
            resolvedDetails.guilds || resolvedDetails.data?.guilds || [];
          detailsContent.spaces =
            resolvedDetails.spaces || resolvedDetails.data?.spaces || [];
          detailsContent.responsibilities =
            resolvedDetails.responsibilities ||
            resolvedDetails.data?.responsibilities ||
            [];
          detailsContent.authorities =
            resolvedDetails.authorities ||
            resolvedDetails.data?.authorities ||
            [];

          // Handle eligibility and toggle with proper structure
          detailsContent.eligibility = {
            manual:
              resolvedDetails.eligibility?.manual ||
              resolvedDetails.data?.eligibility?.manual ||
              false,
            criteria:
              resolvedDetails.eligibility?.criteria ||
              resolvedDetails.data?.eligibility?.criteria ||
              [],
          };

          detailsContent.toggle = {
            manual:
              resolvedDetails.toggle?.manual ||
              resolvedDetails.data?.toggle?.manual ||
              false,
            criteria:
              resolvedDetails.toggle?.criteria ||
              resolvedDetails.data?.toggle?.criteria ||
              [],
          };
        } catch (error) {
          console.error('Error parsing IPFS data:', error);
        }
      }
    }

    if (hat.imageUri) {
      const ipfsResult = await fetchIpfs(hat.imageUri);
      imageContent = ipfsResult?.data?.toString() || '';
    }

    // Get module information if available
    const moduleInfo: {
      eligibility?: ModuleDetails;
      toggle?: ModuleDetails;
    } = {};

    if (hat.eligibility) {
      const eligibilityRules = await getEligibilityRules({
        address: hat.eligibility as Address,
        chainId: args.chainId,
      });

      moduleInfo.eligibility = {
        rules: eligibilityRules,
      };
    }

    if (hat.toggle) {
      moduleInfo.toggle = await getModuleInfo(hat.toggle as Address);
    }

    const enrichedHat = {
      id:
        typeof (hat as SubgraphHat).id === 'bigint'
          ? (hat as SubgraphHat).id.toString()
          : (hat as SubgraphHat).id,
      name: detailsContent.name,
      prettyId: hat.prettyId,
      status: hat.status,
      details: hat.details,
      maxSupply:
        typeof (hat as SubgraphHat).maxSupply === 'bigint'
          ? (hat as SubgraphHat).maxSupply.toString()
          : (hat as SubgraphHat).maxSupply,
      eligibility: hat.eligibility,
      toggle: hat.toggle,
      mutable: hat.mutable,
      imageUri: hat.imageUri,
      levelAtLocalTree: hat.levelAtLocalTree,
      currentSupply:
        typeof (hat as SubgraphHat).currentSupply === 'bigint'
          ? (hat as SubgraphHat).currentSupply.toString()
          : (hat as SubgraphHat).currentSupply,
      detailsDecoded: detailsContent,
      moduleInfo,
      subHats: ((hat as SubgraphHat).subHats || []).map((subHat) => ({
        id: typeof subHat.id === 'bigint' ? subHat.id.toString() : subHat.id,
        prettyId: subHat.prettyId,
        status: subHat.status,
      })),
      wearers: ((hat as SubgraphHat).wearers || []).map((wearer) => ({
        id: wearer.id,
        currentHats: (wearer.currentHats || []).map((hat) => ({
          id: typeof hat.id === 'bigint' ? hat.id.toString() : hat.id,
          prettyId: hat.prettyId,
          status: hat.status,
        })),
        _totalHats: wearer.currentHats?.length || 0,
      })),
    };

    // Ensure all BigInts are serialized before passing to chunkResponse
    return chunkResponse(serializeBigInts(enrichedHat));
  } catch (error) {
    console.error('Smart Hat Lookup Error:', error);
    return {
      _meta: {},
      content: [
        {
          type: 'text',
          text: `Error during hat lookup: ${
            error instanceof Error ? error.message : 'Unknown error'
          }`,
        },
      ],
    };
  }
}

// Define the parameters schema
const parameters = z.object({
  hatId: z.string(), // Hat ID in hex or human-readable format
  chain: z.string(),
  chainId: z.number(),
});

// Define the operation interface
interface GetHatByIdOperation {
  name: string;
  description: string;
  parameters: typeof parameters;
  execute: (args: z.infer<typeof parameters>) => Promise<CallToolResult>;
}

export const getHatByIdOperation: GetHatByIdOperation = {
  name: 'get_hat_by_id',
  description: `Get detailed information about a specific Hat (by hatId).

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic hat info:
  "Show me hat 0x1234 on mainnet"
  {"hatId": "0x1234", "chain": "mainnet", "chainId": 1}

### Response Format
The response will include:
- Basic hat properties (id, details, maxSupply, etc.)
- Current status and eligibility modules
- Chain-specific context
- Current wearers
- If detailsDecoded are provided include all of them in the response

### Available Properties
The following properties are included:
- name: The hat's name
- prettyId: Human readable hat ID
- status: Active/inactive status
- details: Hat metadata and description
- maxSupply: Maximum number of wearers
- currentSupply: Current number of wearers
- eligibility: Eligibility module details
- toggle: Toggle module details
- mutable: Whether hat properties can be changed
- imageUri: Hat image URI
- admin: Admin hat information
- wearers: Current hat wearers
- chainContext: Chain-specific information
`,
  parameters,
  async execute(args) {
    console.log('\n=== Starting Get Hat Operation ===');
    console.log('Args:', args);

    try {
      // Validate chain support
      if (!isChainSupported(args.chain)) {
        const supportedChains = getSupportedChains().join(', ');
        return {
          _meta: {},
          content: [
            {
              type: 'text',
              text: `Chain "${args.chain}" is not supported. Please use one of the supported chains: ${supportedChains}`,
            },
          ],
        };
      }

      // Get the proper chain ID from the chain name if provided
      const chainId = args.chain ? getChainId(args.chain) : args.chainId;
      args.chainId = chainId; // Ensure chainId is set in args

      console.log('\n=== Getting Subgraph Client ===');
      const client = getSubgraphClient();

      // Return the result directly without rewrapping
      return await smartHatLookup(args, client);
    } catch (error) {
      console.error('Error in get hat operation:', error);
      return {
        _meta: {},
        content: [
          {
            type: 'text',
            text: `An error occurred while fetching hat information: ${
              error instanceof Error ? error.message : 'Unknown error'
            }`,
          },
        ],
      };
    }
  },
};
