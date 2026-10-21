import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';
import { createHatsClient } from '../utils/hats-client.js';
import { HATS_CONTRACT_ADDRESSES } from '../utils/constants.js';
import { normalizeHatId } from '../utils/hat-utils.js';
import { calculateAndPinJson } from '../utils/ipfs.js';

// Import fallback address for default eligibility/toggle modules
const FALLBACK_ADDRESS = '0x0000000000000000000000000000000000004a75';

// Define the parameters schema for the operation
const parameters = z.object({
  chain: z
    .string()
    .describe('The blockchain network to use (e.g., "sepolia", "mainnet")'),
  adminHatId: z
    .string()
    .describe(
      'The ID of the admin hat (can be in human-readable format like "1.2.3" or hex)'
    ),
  name: z.string().describe('The name of the hat'),
  description: z.string().describe('A description of the hat and its purpose'),
  maxSupply: z
    .number()
    .min(1)
    .describe('The maximum number of addresses that can wear this hat'),
  eligibility: z
    .string()
    .regex(/^0x[a-fA-F0-9]{40}$/, 'Must be a valid Ethereum address')
    .transform((val): `0x${string}` => val as `0x${string}`)
    .optional()
    .default(FALLBACK_ADDRESS as `0x${string}`)
    .describe(
      'Optional: The Ethereum address of the eligibility module (defaults to no eligibility requirements)'
    ),
  toggle: z
    .string()
    .regex(/^0x[a-fA-F0-9]{40}$/, 'Must be a valid Ethereum address')
    .transform((val): `0x${string}` => val as `0x${string}`)
    .optional()
    .default(FALLBACK_ADDRESS as `0x${string}`)
    .describe(
      'Optional: The Ethereum address of the toggle module (defaults to no toggle restrictions)'
    ),
  mutable: z
    .boolean()
    .optional()
    .default(true)
    .describe(
      'Whether the hat properties can be changed after creation (defaults to true)'
    ),
  imageUri: z
    .string()
    .optional()
    .describe('Optional: An IPFS URI for the hat image'),
});

async function generateCreateHatCalldata(
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

  // Convert admin hat ID to hex if it's in human-readable format
  const adminHatId = normalizeHatId(args.adminHatId);

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
    name: `Hat Details - ${args.name}`,
  });

  // Generate the create hat calldata
  const { callData, functionName } = await hatsClient.createHatCallData({
    admin: BigInt(adminHatId),
    details: detailsCid,
    maxSupply: args.maxSupply,
    eligibility: args.eligibility,
    toggle: args.toggle,
    mutable: args.mutable,
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
    adminHatId,
    name: args.name,
    description: args.description,
    maxSupply: args.maxSupply,
    eligibility: args.eligibility,
    toggle: args.toggle,
    mutable: args.mutable,
    detailsCid,
    imageUri: args.imageUri,
  };

  // Log critical transaction data for debugging
  console.log('\n=== CRITICAL TRANSACTION DATA ===');
  console.log('Contract Address:', contractAddress);
  console.log('Calldata:', callData);
  console.log('\n=== CHAIN INFO ===');
  console.log('Chain:', args.chain, '(Chain ID:', chainId, ')');
  console.log('\n=== HAT DETAILS ===');
  console.log('Function:', functionName);
  console.log('Admin Hat ID:', adminHatId);
  console.log('Details CID:', detailsCid);

  // Return with critical transaction data first, followed by additional details
  return {
    content: [
      {
        type: 'text',
        text: `=== CRITICAL TRANSACTION DATA ===
CONTRACT ADDRESS: ${transactionData.contractAddress}
CALLDATA: ${transactionData.callData}

=== CHAIN INFO ===
CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})

=== HAT DETAILS ===
FUNCTION: ${transactionData.functionName}
ADMIN HAT ID: ${transactionData.adminHatId}
HAT NAME: ${transactionData.name}
DESCRIPTION: ${transactionData.description}
MAX SUPPLY: ${transactionData.maxSupply}
ELIGIBILITY MODULE: ${transactionData.eligibility}
TOGGLE MODULE: ${transactionData.toggle}
MUTABLE: ${transactionData.mutable}
IPFS CID: ${transactionData.detailsCid}
${transactionData.imageUri ? `IMAGE URI: ${transactionData.imageUri}` : ''}

=== COPY/PASTE READY ===
Contract: ${transactionData.contractAddress}
Data: ${transactionData.callData}`,
      },
    ],
    transaction: {
      to: transactionData.contractAddress,
      data: transactionData.callData,
      chain: {
        name: transactionData.chainName,
        id: transactionData.chainId,
      },
      value: '0',
    },
    metadata: {
      function: {
        name: transactionData.functionName,
        signature:
          'createHat(uint256,string,uint32,address,address,bool,string)',
      },
      contractAddress: transactionData.contractAddress,
      callData: transactionData.callData,
      adminHatId: transactionData.adminHatId,
      details: transactionData.detailsCid,
      maxSupply: transactionData.maxSupply,
      eligibility: transactionData.eligibility,
      toggle: transactionData.toggle,
      mutable: transactionData.mutable,
      imageUri: transactionData.imageUri,
    },
  };
}

// Export the operation interface
export const operation = {
  name: 'create_hat',
  description: `Generate calldata for creating a new child hat under an existing admin hat.

### What This Does
This operation creates a "child hat" as described in the official Hats Protocol documentation. 
Child hats are created under parent hats (like a Top Hat) and inherit administrative authority from their parent.
See: https://docs.hatsprotocol.xyz/using-hats/creating-my-first-hat#id-2.-creating-your-first-child-hat

### Important Notes
- This operation creates a new hat with the specified admin hat as its parent
- The name and description will be stored on IPFS and linked to the hat
- The transaction must be executed by an address with admin permissions for the specified admin hat
- The contract address and calldata are prominently displayed for easy copy/paste

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic hat creation with minimal parameters:
  "Create a new hat named 'Treasury Manager' under admin hat 1.1 on mainnet with max supply 5"
  {
    "chain": "mainnet",
    "adminHatId": "1.1", 
    "name": "Treasury Manager",
    "description": "Manages treasury operations and financial decisions",
    "maxSupply": 5
  }

- Hat with custom modules:
  "Create hat 'Developer' under 0x123... admin with custom eligibility module on sepolia"
  {
    "chain": "sepolia",
    "adminHatId": "0x0000000100000000000000000000000000000000000000000000000000000000",
    "name": "Developer",
    "description": "Core development team member",
    "maxSupply": 10,
    "eligibility": "0x1234567890123456789012345678901234567890",
    "toggle": "0x5678901234567890123456789012345678901234",
    "mutable": false,
    "imageUri": "ipfs://QmExample..."
  }

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - **CONTRACT ADDRESS and CALLDATA prominently displayed at the top**
   - Chain information and transaction details
   - Hat configuration details
   - Copy/paste ready format at the bottom

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- adminHatId: The ID of the admin hat (parent) in human-readable or hex format
- name: The name of the new hat
- description: A description of the hat and its purpose
- maxSupply: Maximum number of addresses that can wear this hat (minimum 1)

Optional parameters (with defaults):
- eligibility: Ethereum address of the eligibility module (defaults to no eligibility requirements)
- toggle: Ethereum address of the toggle module (defaults to no toggle restrictions)
- mutable: Whether hat properties can be changed after creation (defaults to true)
- imageUri: An IPFS URI for the hat image

### Notes
- The name and description are stored on IPFS and the resulting CID is used as the hat's details
- Admin hat IDs in human-readable format (e.g., "1.2.3") are automatically converted to hex
- The transaction must be executed by an address with admin permissions for the specified admin hat
- If not specified, eligibility and toggle modules default to ${FALLBACK_ADDRESS} (no restrictions)
- The new hat will be created as a child of the specified admin hat`,
  parameters,
  execute: generateCreateHatCalldata,
} as const;

export type CreateHatOperation = typeof operation;
