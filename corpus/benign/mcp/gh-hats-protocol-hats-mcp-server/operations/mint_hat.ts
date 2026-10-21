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

// Define the parameters schema for the operation
const parameters = z.object({
  chain: z
    .string()
    .describe('The blockchain network to use (e.g., "sepolia", "mainnet")'),
  hatId: z
    .string()
    .describe(
      'The ID of the hat to mint (can be in human-readable format like "1.2.3" or hex)'
    ),
  recipientAddress: z
    .string()
    .describe('The Ethereum address of the recipient who will receive the hat'),
});

async function generateMintCalldata(
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

  // Convert hat ID to hex if it's in human-readable format
  const hatId = normalizeHatId(args.hatId);

  // Get the Hats client instance with the correct chain ID
  const chainId = getChainId(args.chain);
  const hatsClient = await createHatsClient(chainId);

  if (!hatsClient) {
    throw new Error(`Failed to create Hats client for chain ${args.chain}`);
  }

  // Generate the mint hat calldata
  const { callData, functionName } = await hatsClient.mintHatCallData({
    hatId: BigInt(hatId),
    wearer: args.recipientAddress as `0x${string}`,
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
    hatId,
    recipient: args.recipientAddress,
  };

  // Return with transaction data prominently displayed and formatted
  return {
    content: [
      {
        type: 'text',
        text: `=== TRANSACTION DATA FOR MINTING HAT ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
RECIPIENT: ${transactionData.recipient}

=== END TRANSACTION DATA ===

Raw Calldata for Copy/Paste:
${transactionData.callData}`,
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
      hatId,
      recipient: args.recipientAddress,
      function: {
        name: functionName,
        signature: 'mintHat(uint256,address)',
      },
      contractAddress,
      callData,
    },
  };
}

// Export the operation interface
export const operation = {
  name: 'mint_hat',
  description: `Generate calldata for minting a hat to a recipient address.

### Best Practices
Before generating mint calldata, it's recommended to:
1. Check the recipient's current hats using get_wearer
2. Verify eligibility using get_eligibility
This ensures the mint operation will succeed and helps prevent unnecessary transactions.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic hat minting with verification:
  "Generate calldata to mint hat 1.2.3 to address 0x1234 on mainnet"
  1. Check current hats: get_wearer(address="0x1234", chain="mainnet")
  2. Check eligibility: get_eligibility(hatId="1.2.3", address="0x1234", chain="mainnet")
  3. Generate calldata: {"hatId": "1.2.3", "chain": "mainnet", "recipientAddress": "0x1234"}

- Minting with hex hat ID:
  "Generate calldata to mint hat 0x0000000100020003 to ENS name vitalik.eth on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia", "recipientAddress": "vitalik.eth"}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Descriptive text explaining the mint operation
   - Chain and recipient information

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to mint (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- recipientAddress: The Ethereum address or ENS name of the recipient who will receive the hat

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format
- The recipient address can be either an Ethereum address or ENS name
- Consider checking wearer status and eligibility before proceeding with mint
- The response can be used by both human users and automated agents`,
  parameters,
  execute: generateMintCalldata,
} as const;

export type MintHatOperation = typeof operation;
