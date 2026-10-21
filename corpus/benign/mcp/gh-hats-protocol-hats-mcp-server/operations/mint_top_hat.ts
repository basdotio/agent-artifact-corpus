import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';
import { createHatsClient } from '../utils/hats-client.js';
import { HATS_CONTRACT_ADDRESSES } from '../utils/constants.js';
import { calculateAndPinJson } from '../utils/ipfs.js';

// Define the parameters schema for the operation
const parameters = z.object({
  chain: z
    .string()
    .describe('The blockchain network to use (e.g., "sepolia", "mainnet")'),
  target: z
    .string()
    .regex(/^0x[a-fA-F0-9]{40}$/, 'Must be a valid Ethereum address')
    .transform((val): `0x${string}` => val as `0x${string}`)
    .describe('The Ethereum address that will wear the top hat'),
  name: z.string().describe('The name of the top hat'),
  description: z
    .string()
    .describe('A description of the top hat and its purpose'),
  imageUri: z
    .string()
    .optional()
    .describe('Optional: An IPFS URI for the hat image'),
});

async function generateMintTopHatCalldata(
  args: z.infer<typeof parameters>
): Promise<CallToolResult> {
  // Validate chain
  if (!isChainSupported(args.chain)) {
    const supportedChains = getSupportedChains();
    throw new Error(
      `Chain ${
        args.chain
      } is not supported. Supported chains are: ${supportedChains.join(', ')}`
    );
  }

  // Get the Hats client instance with the correct chain ID
  const chainId = getChainId(args.chain);
  const hatsClient = await createHatsClient(chainId);

  if (!hatsClient) {
    throw new Error(`Failed to create Hats client for chain ${args.chain}`);
  }

  // Create and pin the details to IPFS
  const detailsObject = {
    name: args.name,
    description: args.description,
  };

  // Pin the details to IPFS and get the CID
  const detailsCid = await calculateAndPinJson(detailsObject, {
    name: `Top Hat Details - ${args.name}`,
  });

  // Generate the mint top hat calldata
  const { callData, functionName } = await hatsClient.mintTopHatCallData({
    target: args.target,
    details: detailsCid,
    imageURI: args.imageUri,
  });

  // Get contract address for the chain
  const contractAddress = HATS_CONTRACT_ADDRESSES[chainId];
  if (!contractAddress) {
    throw new Error(`No contract address found for chain ${args.chain}`);
  }

  // Structure the response with clear transaction data
  const transactionData = {
    contractAddress,
    callData,
    chainId,
    chainName: args.chain,
    functionName,
    target: args.target,
    details: detailsCid,
    imageUri: args.imageUri,
  };

  // Return with critical transaction data first, followed by additional details
  return {
    content: [
      {
        type: 'text',
        text: `Contract Address: ${transactionData.contractAddress}

Calldata:
${callData}

Chain: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})

=== ADDITIONAL TRANSACTION DETAILS ===
FUNCTION: ${transactionData.functionName}
TARGET ADDRESS: ${transactionData.target}
HAT NAME: ${args.name}
DESCRIPTION: ${args.description}
IPFS CID: ${transactionData.details}
${transactionData.imageUri ? `IMAGE URI: ${transactionData.imageUri}` : ''}`,
      },
    ],
    transaction: {
      to: contractAddress,
      data: callData,
      chain: {
        name: args.chain,
        id: chainId,
      },
      value: '0',
    },
    metadata: {
      function: {
        name: functionName,
        signature: 'mintTopHat(address,string,string)',
      },
      contractAddress,
      callData,
      target: args.target,
      details: detailsCid,
      imageUri: args.imageUri,
    },
  };
}

// Export the operation interface
export const operation = {
  name: 'mint_top_hat',
  description: `Generate calldata for minting a new top hat, which creates a new hat tree.

### Important Note
This operation will create a new top hat and mint it to the specified target address.
The name and description will be stored on IPFS and linked to the hat.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic top hat creation:
  "Create a new top hat named 'DAO Governance' for address 0x123... on mainnet with description 'Main governance hat for the DAO'"
  {
    "chain": "mainnet",
    "target": "0x123...",
    "name": "DAO Governance",
    "description": "Main governance hat for the DAO"
  }

- Top hat with image:
  "Mint top hat 'Treasury Management' to 0x456... on sepolia with image ipfs://Qm..."
  {
    "chain": "sepolia",
    "target": "0x456...",
    "name": "Treasury Management",
    "description": "Treasury management hat",
    "imageUri": "ipfs://Qm..."
  }

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Transaction details
   - Chain information
   - Target address
   - IPFS CID for details
   - Image URI (if provided)

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- target: The Ethereum address that will wear the top hat
- name: The name of the top hat
- description: A description of the top hat and its purpose
Optional parameters:
- imageUri: An IPFS URI for the hat image

### Notes
- The name and description are stored on IPFS and the resulting CID is used as the hat's details
- The target address will be the initial wearer of the top hat
- The top hat will be the root of a new hat tree
- Additional hats can be created under this top hat once it is minted`,
  parameters,
  execute: generateMintTopHatCalldata,
} as const;

export type MintTopHatOperation = typeof operation;
