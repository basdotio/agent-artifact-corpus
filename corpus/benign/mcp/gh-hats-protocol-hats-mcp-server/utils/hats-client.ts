import { HatsClient } from '@hatsprotocol/sdk-v1-core';
import { viemPublicClient } from './modules.js';

/**
 * Creates a HatsClient instance for a specific chain
 * Since this is server-side and only for generating calldata,
 * we don't need wallet client support
 * @param chainId - The chain ID to use
 * @returns HatsClient instance or undefined if no chainId provided
 */
export async function createHatsClient(
  chainId: number | undefined
): Promise<HatsClient | undefined> {
  if (!chainId) return undefined;

  try {
    const publicClient = viemPublicClient(chainId);

    const hatsClient = new HatsClient({
      chainId,
      publicClient,
    });

    return hatsClient;
  } catch (error) {
    console.error('Error creating Hats client:', error);
    return undefined;
  }
}
