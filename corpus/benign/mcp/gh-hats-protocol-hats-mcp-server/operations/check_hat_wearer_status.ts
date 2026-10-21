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
});

async function generateCheckHatWearerStatusCalldata(
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

  // Generate the check hat wearer status calldata
  const { callData, functionName } =
    await hatsClient.checkHatWearerStatusCallData({
      hatId: BigInt(hatId),
      wearer: args.wearer as `0x${string}`,
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
  };

  return {
    content: [
      {
        type: 'text',
        text: `=== TRANSACTION DATA FOR CHECKING HAT WEARER STATUS ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
WEARER: ${transactionData.wearer}

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
      function: {
        name: functionName,
        signature: 'checkHatWearerStatus(uint256,address)',
      },
      contractAddress,
      callData,
    },
  };
}

export const operation = {
  parameters,
  description: `Check a wearer's status for a specific hat.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic status check:
  "Check status of wearer 0x1234... for hat 1.1 on mainnet"
  {
    "chain": "mainnet",
    "chainId": 1,
    "hatId": "1.1",
    "wearer": "0x1234..."
  }

- Check with hex hat ID:
  "Check if 0x5678... is eligible and in good standing for hat 0x1234... on optimism"
  {
    "chain": "optimism",
    "chainId": 10,
    "hatId": "0x1234...",
    "wearer": "0x5678..."
  }

### Response Format
The response includes:
- status: "success" if query was successful
- data: Object containing:
  - eligible: Whether the wearer is eligible for the hat
  - standing: Whether the wearer is in good standing
  - wearing: Whether the wearer is currently wearing the hat

### Available Parameters
Required parameters:
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- chainId: The chain ID (e.g. 1 for mainnet, 10 for optimism)
- hatId: The ID of the hat (can be in human-readable format like "1.1" or hex)
- wearer: The Ethereum address of the wearer to check status for`,
  execute: generateCheckHatWearerStatusCalldata,
} as const;

export type CheckHatWearerStatusOperation = typeof operation;
