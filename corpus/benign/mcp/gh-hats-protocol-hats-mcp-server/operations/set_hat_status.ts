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
  active: z
    .boolean()
    .describe('Whether to set the hat as active (true) or inactive (false)'),
});

async function generateSetHatStatusCalldata(
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

  // Generate the set hat status calldata
  const { callData, functionName } = await hatsClient.setHatStatusCallData({
    hatId: BigInt(hatId),
    newStatus: args.active,
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
    active: args.active,
  };

  // Return with transaction data prominently displayed and formatted
  return {
    content: [
      {
        type: 'text',
        text: `⚠️ IMPORTANT: This transaction will only succeed if executed from a wallet that has admin rights for this hat. ⚠️

=== TRANSACTION DATA FOR SETTING HAT STATUS ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
NEW STATUS: ${transactionData.active ? 'Active' : 'Inactive'}

=== END TRANSACTION DATA ===

Raw Calldata for Copy/Paste:
${transactionData.callData}

Note: Setting a hat's status to inactive will prevent it from being worn, while setting it to active will allow it to be worn (subject to eligibility).`,
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
        signature: 'setHatStatus(uint256,bool)',
      },
      contractAddress,
      callData,
      active: args.active,
    },
  };
}

// Export the operation interface
export const operation = {
  name: 'set_hat_status',
  description: `Generate calldata for setting the status (active/inactive) of a hat.

### Important Note
This operation will only succeed if executed from a wallet that has admin rights for the hat.
Setting a hat's status affects whether it can be worn.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Activating a hat:
  "Set hat 1.2.3 to active on mainnet"
  {"hatId": "1.2.3", "chain": "mainnet", "active": true}

- Deactivating a hat:
  "Deactivate hat 0x0000000100020003 on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia", "active": false}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Warning about execution requirements
   - Descriptive text explaining the status change
   - Chain information
   - New status details

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to modify (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- active: Whether to set the hat as active (true) or inactive (false)

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format
- The transaction must be executed from a wallet with admin rights
- An inactive hat cannot be worn, even if the wearer meets eligibility requirements
- Activating a hat allows it to be worn, subject to eligibility checks`,
  parameters,
  execute: generateSetHatStatusCalldata,
} as const;

export type SetHatStatusOperation = typeof operation;
