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
      'The ID of the hat to transfer (can be in human-readable format like "1.2.3" or hex)'
    ),
  fromAddress: z
    .string()
    .describe('The Ethereum address of the current hat wearer'),
  toAddress: z
    .string()
    .describe('The Ethereum address of the recipient who will receive the hat'),
});

async function generateTransferCalldata(
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
    // Generate the transfer hat calldata using the SDK
    const { callData, functionName } = await hatsClient.transferHatCallData({
      hatId: BigInt(hatId),
      from: args.fromAddress as `0x${string}`,
      to: args.toAddress as `0x${string}`,
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
      from: args.fromAddress,
      to: args.toAddress,
    };

    // Return with transaction data prominently displayed and formatted
    return {
      content: [
        {
          type: 'text',
          text: `⚠️ IMPORTANT: This transaction will only succeed if:
1. It is executed from a wallet that has permission to transfer the hat
2. The recipient address is eligible to wear the hat ⚠️

=== TRANSACTION DATA FOR TRANSFERRING HAT ===

CONTRACT ADDRESS:
${transactionData.contractAddress}

CALLDATA:
${transactionData.callData}

CHAIN: ${transactionData.chainName} (Chain ID: ${transactionData.chainId})
FUNCTION: ${transactionData.functionName}
HAT ID: ${transactionData.hatId}
FROM: ${transactionData.from}
TO: ${transactionData.to}

=== END TRANSACTION DATA ===

Raw Calldata for Copy/Paste:
${transactionData.callData}

Note: Please verify the recipient's eligibility using get_eligibility before proceeding with the transfer.`,
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
        from: args.fromAddress,
        to: args.toAddress,
        function: {
          name: functionName,
          signature: 'transferHat(uint256,address,address)',
        },
        contractAddress,
        callData,
      },
    };
  } catch (error) {
    throw new Error(
      `Failed to generate transfer hat calldata: ${
        error instanceof Error ? error.message : 'Unknown error'
      }`
    );
  }
}

// Export the operation interface
export const operation = {
  name: 'transfer_hat',
  description: `Generate calldata for transferring a hat from one address to another.

### Important Note
This operation requires proper permissions to execute. The transaction must be signed by an address with permission to transfer the hat.

### Best Practices
Before generating transfer calldata, it's recommended to:
1. Check the current wearer's status using get_wearer
2. Verify recipient's eligibility using get_eligibility
This ensures the transfer operation will succeed and helps prevent unnecessary transactions.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic hat transfer:
  "Generate calldata to transfer hat 1.2.3 from 0x1234 to 0x5678 on mainnet"
  {"hatId": "1.2.3", "chain": "mainnet", "fromAddress": "0x1234", "toAddress": "0x5678"}

- Transfer with hex hat ID:
  "Generate calldata to transfer hat 0x0000000100020003 from vitalik.eth to buterin.eth on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia", "fromAddress": "vitalik.eth", "toAddress": "buterin.eth"}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Warning about execution requirements
   - Descriptive text explaining the transfer operation
   - Chain and address information

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to transfer (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- fromAddress: The Ethereum address or ENS name of the current hat wearer
- toAddress: The Ethereum address or ENS name of the recipient who will receive the hat

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format using our utilities
- Both fromAddress and toAddress can be either Ethereum addresses or ENS names
- Consider checking wearer status and eligibility before proceeding with transfer
- The transaction must be executed by an address with permission to transfer the hat`,
  parameters,
  execute: generateTransferCalldata,
} as const;

export type TransferHatOperation = typeof operation;
