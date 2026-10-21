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
      'The ID of the hat to check (can be in human-readable format like "1.2.3" or hex)'
    ),
});

async function generateCheckHatStatusCalldata(
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

  // Generate the check hat status calldata
  const { callData, functionName } = await hatsClient.checkHatStatusCallData({
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
        text: `=== TRANSACTION DATA FOR CHECKING HAT STATUS ===

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

Note: This is a read-only operation that checks the status of a hat. It returns whether the hat is active or not.`,
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
        signature: 'checkHatStatus(uint256)',
      },
      contractAddress,
      callData,
    },
  };
}

// Export the operation interface
export const operation = {
  name: 'check_hat_status',
  description: `Generate calldata for checking the status of a hat.

### Important Note
This is a read-only operation that checks whether a hat is active or not.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic hat status check:
  "Check status of hat 1.2.3 on mainnet"
  {"hatId": "1.2.3", "chain": "mainnet"}

- Check status with hex hat ID:
  "Check status of hat 0x0000000100020003 on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia"}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Descriptive text explaining the status check operation
   - Chain information
   - Transaction details

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to check (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format
- This is a view function and does not modify the blockchain state
- Returns whether the hat is currently active or not`,
  parameters,
  execute: generateCheckHatStatusCalldata,
} as const;

export type CheckHatStatusOperation = typeof operation;
