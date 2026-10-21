import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type {
  WearerPropsConfig,
  Wearer,
  Hat,
  HatsEvent,
  HatsSubgraphClient,
} from '@hatsprotocol/sdk-v1-subgraph';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';
import { chunkResponse } from '../utils/response.js';
import { resolveAddressOrEns } from '../utils/viem.js';
import { getSubgraphClient } from '../utils/subgraph-client.js';

// Define the parameters schema
const parameters = z.object({
  wearerAddress: z.string(),
  chain: z.string(),
  chainId: z.number(),
});

// Use the SDK's types directly
interface EnrichedWearer {
  id: string;
  currentHats: Hat[];
  mintEvent: HatsEvent[];
  _totalHats: number;
}

async function smartWearerLookup(
  args: z.infer<typeof parameters>,
  client: HatsSubgraphClient
): Promise<CallToolResult> {
  console.log('\n=== Starting Smart Wearer Lookup ===');

  // Resolve ENS name if provided
  const resolvedAddress = await resolveAddressOrEns(args.wearerAddress);
  console.log('Resolved address:', resolvedAddress);

  const wearerProps: WearerPropsConfig = {
    currentHats: {
      props: {
        prettyId: true,
        status: true,
        details: true,
        maxSupply: true,
        currentSupply: true,
      },
    },
    mintEvent: {
      props: {
        blockNumber: true,
        timestamp: true,
      },
      filters: {
        first: 10,
      },
    },
  };

  try {
    const wearer = await client.getWearer({
      chainId: args.chainId,
      wearerAddress: resolvedAddress as `0x${string}`,
      props: wearerProps,
    });

    if (!wearer) {
      return {
        _meta: {},
        content: [
          {
            type: 'text',
            text: `No wearer found at address ${resolvedAddress}${
              args.wearerAddress !== resolvedAddress
                ? ` (resolved from ${args.wearerAddress})`
                : ''
            } on chain ${args.chain}`,
          },
        ],
      };
    }

    const enrichedWearer: EnrichedWearer = {
      id: wearer.id,
      currentHats: wearer.currentHats || [],
      mintEvent: wearer.mintEvent || [],
      _totalHats: wearer.currentHats?.length || 0,
    };

    return chunkResponse(enrichedWearer);
  } catch (error) {
    console.error('Smart Wearer Lookup Error:', error);
    return {
      _meta: {},
      content: [
        {
          type: 'text',
          text: `Error during wearer lookup: ${
            error instanceof Error ? error.message : 'Unknown error'
          }`,
        },
      ],
    };
  }
}

// Define the operation interface
interface GetWearerOperation {
  name: string;
  description: string;
  parameters: typeof parameters;
  execute: (args: z.infer<typeof parameters>) => Promise<CallToolResult>;
}

export const getWearerOperation: GetWearerOperation = {
  name: 'get_wearer',
  description: `Get detailed information about a specific wearer's Hats, including their current hats and minting history.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic wearer info:
  "Show me the hats for address 0x1234 on mainnet"
  {"wearerAddress": "0x1234", "chain": "mainnet", "chainId": 1}

### Response Format
The response will include:
- Wearer's address
- Current hats being worn
- Hat minting history
- Total number of hats currently worn

### Available Properties
The following properties are included for each hat:
- prettyId: Human readable hat ID
- status: Active/inactive status
- details: Hat metadata and description
- maxSupply: Maximum number of wearers
- currentSupply: Current number of wearers
- mintEvents: History of hat minting events
`,
  parameters,
  async execute(args) {
    console.log('\n=== Starting Get Wearer Operation ===');
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
      return await smartWearerLookup(args, client);
    } catch (error) {
      console.error('Error in get wearer operation:', error);
      return {
        _meta: {},
        content: [
          {
            type: 'text',
            text: `An error occurred while fetching wearer information: ${
              error instanceof Error ? error.message : 'Unknown error'
            }`,
          },
        ],
      };
    }
  },
};
