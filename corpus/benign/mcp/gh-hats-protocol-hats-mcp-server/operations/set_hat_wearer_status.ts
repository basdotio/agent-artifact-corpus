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
import { isValidAddress } from '../utils/validation.js';

export const parameters = z.object({
  chain: z.string(),
  chainId: z.number(),
  hatId: z.string(),
  wearer: z.string().refine(isValidAddress, {
    message: 'Invalid Ethereum address for wearer',
  }),
  eligible: z.boolean(),
  standing: z.boolean(),
});

async function generateSetHatWearerStatusCalldata(
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

  // Generate the set hat wearer status calldata
  const { callData, functionName } =
    await hatsClient.setHatWearerStatusCallData({
      hatId: BigInt(hatId),
      wearer: args.wearer as `0x${string}`,
      eligible: args.eligible,
      standing: args.standing,
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
    wearer: args.wearer,
    eligible: args.eligible,
    standing: args.standing,
  };

  return {
    content: [
      {
        type: 'text',
        text: `=== TRANSACTION DATA FOR SETTING HAT WEARER STATUS ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
WEARER: ${transactionData.wearer}
ELIGIBLE: ${transactionData.eligible}
STANDING: ${transactionData.standing}

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
      wearer: args.wearer,
      eligible: args.eligible,
      standing: args.standing,
      function: {
        name: functionName,
        signature: 'setHatWearerStatus(uint256,address,bool,bool)',
      },
      contractAddress,
      callData,
    },
  };
}

export const operation = {
  parameters,
  description: `Set a wearer's status for a specific hat.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic status update:
  "Set wearer 0x1234... as eligible and in good standing for hat 1.1 on mainnet"
  {
    "chain": "mainnet",
    "chainId": 1,
    "hatId": "1.1",
    "wearer": "0x1234...",
    "eligible": true,
    "standing": true
  }

- Remove eligibility:
  "Mark wearer 0x5678... as ineligible but in good standing for hat 0x1234... on optimism"
  {
    "chain": "optimism",
    "chainId": 10,
    "hatId": "0x1234...",
    "wearer": "0x5678...",
    "eligible": false,
    "standing": true
  }

### Response Format
The response includes:
- status: "success" if transaction was successful, "reverted" if transaction reverted
- transactionHash: transaction's hash

### Available Parameters
Required parameters:
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- chainId: The chain ID (e.g. 1 for mainnet, 10 for optimism)
- hatId: The ID of the hat (can be in human-readable format like "1.1" or hex)
- wearer: The Ethereum address of the wearer to update status for
- eligible: Whether the wearer is eligible for the hat
- standing: Whether the wearer is in good standing`,
  execute: generateSetHatWearerStatusCalldata,
} as const;

export type SetHatWearerStatusOperation = typeof operation;
