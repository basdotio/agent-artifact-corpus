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
      'The ID of the hat to renounce (can be in human-readable format like "1.2.3" or hex)'
    ),
});

async function generateRenounceCalldata(
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

  // Generate the renounce hat calldata
  const { callData, functionName } = await hatsClient.renounceHatCallData({
    hatId: BigInt(hatId),
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
  };

  // Return with transaction data prominently displayed and formatted
  return {
    content: [
      {
        type: 'text',
        text: `⚠️ IMPORTANT: This transaction will only succeed if executed from a wallet that is currently wearing the hat. ⚠️

=== TRANSACTION DATA FOR RENOUNCING HAT ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}

=== END TRANSACTION DATA ===

Raw Calldata for Copy/Paste:
${transactionData.callData}

Note: Renouncing a hat is permanent and cannot be undone. The hat will be burned and removed from your address.`,
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
      function: {
        name: functionName,
        signature: 'renounceHat(uint256)',
      },
      contractAddress,
      callData,
    },
  };
}

// Export the operation interface
export const operation = {
  name: 'renounce_hat',
  description: `Generate calldata for renouncing (burning) a hat that you are currently wearing.

### Important Note
This operation will only succeed if executed from a wallet address that is currently wearing the hat.
Renouncing a hat is permanent and cannot be undone.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic hat renouncing:
  "Generate calldata to renounce hat 1.2.3 on mainnet"
  {"hatId": "1.2.3", "chain": "mainnet"}

- Renouncing with hex hat ID:
  "Generate calldata to renounce hat 0x0000000100020003 on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia"}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Warning about execution requirements
   - Descriptive text explaining the renounce operation
   - Chain information

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to renounce (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format
- The transaction must be executed from the wallet address that is wearing the hat
- This operation is permanent and cannot be undone
- The hat will be burned and removed from your address`,
  parameters,
  execute: generateRenounceCalldata,
} as const;

export type RenounceHatOperation = typeof operation;
