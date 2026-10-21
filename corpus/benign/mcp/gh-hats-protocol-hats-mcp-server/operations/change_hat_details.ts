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
import { calculateAndPinJson } from '../utils/ipfs.js';

export const parameters = z.object({
  chain: z.string(),
  chainId: z.number(),
  hatId: z.string(),
  name: z.string(),
  description: z.string(),
});

async function generateChangeHatDetailsCalldata(
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

  // Create and pin the details to IPFS
  const detailsObject = {
    name: args.name,
    description: args.description,
  };

  const metadata = {
    name: args.name,
    hatId,
    chain: args.chain,
    chainId,
    timestamp: new Date().toISOString(),
  };

  // Pin the details to IPFS and get the CID
  const detailsCid = await calculateAndPinJson(detailsObject, metadata);
  const details = detailsCid;

  // Generate the change hat details calldata
  const { callData, functionName } = await hatsClient.changeHatDetailsCallData({
    hatId: BigInt(hatId),
    newDetails: details,
  });

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
      details,
      detailsObject,
      function: {
        name: functionName,
        signature: 'changeHatDetails(uint256,string)',
      },
      contractAddress,
      callData,
    },
  };
}

export const operation = {
  parameters,
  description: `Change a hat's details (name and description).

### Response Format
MUST ONLY return:
To: \`<contract_address>\`
Data: \`<calldata>\`
Chain: <chain_name> (Chain ID: <chain_id>)
Value: <value>

### Available Parameters
Required parameters:
- chain: The blockchain network to use (e.g., "sepolia", "mainnet")
- chainId: The chain ID (e.g. 1 for mainnet, 10 for optimism)
- hatId: The ID of the hat (can be in human-readable format like "1.2.3" or hex)
- name: The new name for the hat
- description: The new description for the hat`,
  execute: generateChangeHatDetailsCalldata,
} as const;

export type ChangeHatDetailsOperation = typeof operation;
