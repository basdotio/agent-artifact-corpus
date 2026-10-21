import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type {
  TreePropsConfig,
  HatPropsConfig,
} from '@hatsprotocol/sdk-v1-subgraph';
import { getChainId, isChainSupported } from '../utils/chains.js';
import {
  createErrorResponse,
  createJsonResponse,
  chunkResponse,
} from '../utils/response.js';
import { fetchIpfs } from '../utils/ipfs.js';
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

// Define the parameters schema
const parameters = z.object({
  treeId: z.number(),
  chain: z.string(),
  chainId: z.number(),
  first: z.number().optional(), // Optional parameter for limiting number of hats
  skip: z.number().optional(), // Optional parameter for pagination offset
  topHatOnly: z.boolean().optional(), // Optional parameter to fetch only top hat
});

// Define the operation interface
interface GetTreeOperation {
  name: string;
  description: string;
  parameters: typeof parameters;
  execute: (args: z.infer<typeof parameters>) => Promise<CallToolResult>;
}

export const getTreeOperation: GetTreeOperation = {
  name: 'get_tree',
  description: `Get the tree structure for a given Hat on a specific chain.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic tree fetch:
  "Show me the tree for hat 0x1234 on mainnet"
  {"treeId": 1, "chain": "mainnet", "chainId": 1}

- Top hat only:
  "show me just the top hat for tree 1 on optimism"
  {"treeId": 1, "chain": "optimism", "chainId": 10, "topHatOnly": true}

- Limited hat fetch:
  "show me the first 200 hats in tree 2 on optimism"
  {"treeId": 2, "chain": "optimism", "chainId": 10, "first": 200}

### Response Format
The response will include:
- Complete tree structure with parent-child relationships
- Hat details and metadata for each hat in the tree
- Current status and properties of each hat
- Tree structure with as much hat details as possible given the response information. Do not make up details or make assumptions
- Analysis of the tree structure in accordance with the llms-full.txt file

Note: This operation focuses on tree structure and hat properties. For information about current hat wearers or specific wearer details, please use dedicated wearer-focused operations like get_wearers or get_hat_wearers.

### Available Properties
The following properties can be fetched for each hat:
- prettyId: Human readable hat ID
- status: Active/inactive status
- createdAt: Creation timestamp
- details: Hat metadata and description
- maxSupply: Maximum number of wearers
- eligibility: Eligibility module address
- toggle: Toggle module address
- mutable: Whether hat properties can be changed
- imageUri: Hat image URI
- levelAtLocalTree: Hat's level in the tree
- currentSupply: Current number of wearers
- subHats: Child hats in the tree
- wearers: Current hat wearers
`,
  parameters,
  async execute(args) {
    console.log('\n=== Starting Get Tree Operation ===');
    console.log('Args:', args);

    try {
      // Validate chain support
      if (!isChainSupported(args.chain)) {
        return createErrorResponse(
          `Chain "${args.chain}" is not supported. Please use one of the supported chains.`
        );
      }

      // Get the proper chain ID from the chain name if provided
      const chainId = args.chain ? getChainId(args.chain) : args.chainId;

      console.log('\n=== Getting Subgraph Client ===');
      const client = getSubgraphClient();

      // Prepare query props based on arguments
      const hatProps: HatPropsConfig = {
        prettyId: true,
        status: true,
        createdAt: true,
        details: true,
        maxSupply: true,
        eligibility: true,
        toggle: true,
        mutable: true,
        imageUri: true,
        levelAtLocalTree: true,
        currentSupply: true,
        wearers: {
          props: {}, // Only include wearer id without nested currentHats
        },
      };

      // Add subHats if not topHatOnly
      if (!args.topHatOnly) {
        hatProps.subHats = {
          props: {
            prettyId: true,
            status: true,
            maxSupply: true,
            currentSupply: true,
            details: true,
          },
        };
      }

      // Create the final TreePropsConfig with pagination
      const props: TreePropsConfig = {
        hats: {
          props: hatProps,
          filters: {
            ...(args.first ? { first: args.first } : {}),
            ...(args.skip ? { skip: args.skip } : {}),
          },
        },
      };

      try {
        console.log('\n=== Querying Tree Data ===');
        const tree = await client.getTree({
          chainId,
          treeId: args.treeId,
          props,
        });

        if (!tree) {
          return createErrorResponse(
            `No tree found for chain ${args.chain} (chainId: ${chainId}) and treeId ${args.treeId}`
          );
        }

        // Process and return the tree data
        return chunkResponse(tree);
      } catch (queryError) {
        console.error('GraphQL Query Error:', queryError);
        return createErrorResponse(
          queryError instanceof Error
            ? queryError.message
            : 'Unknown GraphQL error'
        );
      }
    } catch (error) {
      console.error('Error in get tree operation:', error);
      return createErrorResponse(
        error instanceof Error
          ? error.message
          : 'Unknown error during tree fetch'
      );
    }
  },
};
