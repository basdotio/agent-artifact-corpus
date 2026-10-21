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
  newImageURI: z.string(),
});

async function generateChangeHatImageCalldata(
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

  // Generate the change hat image URI calldata
  const { callData, functionName } = await hatsClient.changeHatImageURICallData(
    {
      hatId: BigInt(hatId),
      newImageURI: args.newImageURI,
    }
  );

  // Get contract address for the chain
  const contractAddress = HATS_CONTRACT_ADDRESSES[chainId];
  if (!contractAddress) {
    throw new Error(`No contract address found for chain ${args.chain}`);
  }

  return {
    content: [
      {
        type: 'text',
        text: `To: \`${contractAddress}\`
Data: \`${callData}\`
Chain: ${args.chain} (Chain ID: ${chainId})
Value: 0`,
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
      newImageURI: args.newImageURI,
      function: {
        name: functionName,
        signature: 'changeHatImageURI(uint256,string)',
      },
      contractAddress,
      callData,
    },
  };
}

export const operation = {
  parameters,
  description: `Generate calldata for changing a hat's image URI.

### Important Note
This operation requires proper permissions to execute. The transaction must be signed by an address with admin permissions for the hat, and the hat must be mutable.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Basic image URI change:
  "Change hat 1.2.3's image to ipfs://Qm... on mainnet"
  {"hatId": "1.2.3", "chain": "mainnet", "chainId": 1, "newImageURI": "ipfs://Qm..."}

- Change with hex hat ID:
  "Update image for hat 0x0000000100020003 to ipfs://Qm... on sepolia"
  {"hatId": "0x0000000100020003", "chain": "sepolia", "chainId": 11155111, "newImageURI": "ipfs://Qm..."}

### Response Format
The response includes both human-readable and machine-readable formats:

1. Human-Readable:
   - Warning about execution requirements
   - Descriptive text explaining the image change
   - Chain and address information

2. Machine-Readable:
   - Complete transaction data (to, data, chain, value)
   - Metadata with function details and parameters
   - Structured format for automated processing

### Available Parameters
The following parameters are required:
- hatId: The ID of the hat to modify (can be in human-readable format like "1.2.3" or hex)
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- chainId: The chain ID (e.g. 1 for mainnet, 11155111 for sepolia)
- newImageURI: The new image URI for the hat (typically an IPFS URI)

### Notes
- Human-readable hat IDs (e.g., "1.2.3") will be automatically converted to hex format
- The hat must be mutable for this operation to succeed
- The transaction must be executed by an address with admin permissions for the hat
- The new image URI should typically be an IPFS URI (e.g., "ipfs://Qm...")`,
  execute: generateChangeHatImageCalldata,
} as const;

export type ChangeHatImageOperation = typeof operation;
