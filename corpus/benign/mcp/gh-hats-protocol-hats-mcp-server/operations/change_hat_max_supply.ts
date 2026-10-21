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

export const parameters = z.object({
  chain: z.string(),
  chainId: z.number(),
  hatId: z.string(),
  newMaxSupply: z.number().min(0, {
    message: 'Maximum supply must be a non-negative number',
  }),
});

async function generateChangeHatMaxSupplyCalldata(
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

  // Generate the change hat max supply calldata
  const { callData, functionName } =
    await hatsClient.changeHatMaxSupplyCallData({
      hatId: BigInt(hatId),
      newMaxSupply: args.newMaxSupply,
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
    newMaxSupply: args.newMaxSupply,
  };

  return {
    content: [
      {
        type: 'text',
        text: `=== TRANSACTION DATA FOR CHANGING HAT MAX SUPPLY ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
NEW MAX SUPPLY: ${transactionData.newMaxSupply}

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
      newMaxSupply: args.newMaxSupply,
      function: {
        name: functionName,
        signature: 'changeHatMaxSupply(uint256,uint32)',
      },
      contractAddress,
      callData,
    },
  };
}

export const operation = {
  parameters,
  description: `Change a hat's maximum supply.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic max supply change:
  "Change hat 1.2.3's max supply to 100 on mainnet"
  {
    "chain": "mainnet",
    "chainId": 1,
    "hatId": "1.2.3",
    "newMaxSupply": 100
  }

- Change with hex hat ID:
  "Update max supply for hat 0x0000000100020003 to 50 on sepolia"
  {
    "chain": "sepolia",
    "chainId": 11155111,
    "hatId": "0x0000000100020003",
    "newMaxSupply": 50
  }

### Response Format
The response includes:
- status: "success" if transaction was successful, "reverted" if transaction reverted
- transactionHash: transaction's hash

### Available Parameters
Required parameters:
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- chainId: The chain ID (e.g. 1 for mainnet, 10 for optimism)
- hatId: The ID of the hat (can be in human-readable format like "1.2.3" or hex)
- newMaxSupply: The new maximum number of wearers allowed for the hat`,
  execute: generateChangeHatMaxSupplyCalldata,
} as const;

export type ChangeHatMaxSupplyOperation = typeof operation;
