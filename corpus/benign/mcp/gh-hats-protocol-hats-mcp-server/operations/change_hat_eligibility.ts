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
      'The ID of the hat to modify (can be in human-readable format like "1.2.3" or hex)'
    ),
  newEligibility: z
    .string()
    .describe('The Ethereum address of the new eligibility module'),
});

async function generateChangeEligibilityCalldata(
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

  // Convert hat ID to hex if it's in human-readable format using our utility
  const hatId = normalizeHatId(args.hatId);

  // Get the Hats client instance with the correct chain ID using our utility
  const chainId = getChainId(args.chain);
  const hatsClient = await createHatsClient(chainId);

  if (!hatsClient) {
    throw new Error(`Failed to create Hats client for chain ${args.chain}`);
  }

  try {
    // Generate the change eligibility calldata using the SDK
    const { callData, functionName } =
      await hatsClient.changeHatEligibilityCallData({
        hatId: BigInt(hatId),
        newEligibility: args.newEligibility as `0x${string}`,
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
      newEligibility: args.newEligibility,
    };

    // Return with transaction data prominently displayed and formatted
    return {
      content: [
        {
          type: 'text',
          text: `⚠️ IMPORTANT: This transaction will only succeed if:
1. It is executed from a wallet that has admin permissions for this hat
2. The hat is mutable
3. The new eligibility module address is valid and compatible ⚠️

=== TRANSACTION DATA FOR CHANGING HAT ELIGIBILITY ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
NEW ELIGIBILITY: ${transactionData.newEligibility}

=== END TRANSACTION DATA ===

Raw Calldata for Copy/Paste:
${transactionData.callData}

Note: Please verify that the new eligibility module is properly configured before proceeding with the change.`,
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
        newEligibility: args.newEligibility,
        function: {
          name: functionName,
          signature: 'changeHatEligibility(uint256,address)',
        },
        contractAddress,
        callData,
      },
    };
  } catch (error) {
    throw new Error(
      `Failed to generate change hat eligibility calldata: ${
        error instanceof Error ? error.message : 'Unknown error'
      }`
    );
  }
}

// Export the operation interface
export const operation = {
  name: 'change_hat_eligibility',
  description: `Generate calldata for changing a hat's eligibility module.

### Important Note
This operation requires proper permissions to execute. The transaction must be signed by an address with admin permissions for the hat, and the hat must be mutable.

### Best Practices
Before generating change eligibility calldata, it's recommended to:
1. Check the hat's mutability status
2. Verify admin permissions
3. Ensure the new eligibility module is properly configured
This ensures the operation will succeed and helps prevent unnecessary transactions.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic eligibility change:
  "Generate calldata to change hat 1.2.3's eligibility to 0x1234... on mainnet"
  {"hatId": "1.2.3", "chain": "mainnet", "newEligibility": "0x1234..."}

- Change with hex hat ID:
  "Generate calldata to update eligibility for hat 0x0000000100020003 to 0x5678... on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia", "newEligibility": "0x5678..."}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Warning about execution requirements
   - Descriptive text explaining the eligibility change
   - Chain and address information

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to modify (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- newEligibility: The Ethereum address of the new eligibility module

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format using our utilities
- The hat must be mutable for this operation to succeed
- The transaction must be executed by an address with admin permissions for the hat
- The new eligibility module must implement the IHatsEligibility interface`,
  parameters,
  execute: generateChangeEligibilityCalldata,
} as const;

export type ChangeHatEligibilityOperation = typeof operation;
