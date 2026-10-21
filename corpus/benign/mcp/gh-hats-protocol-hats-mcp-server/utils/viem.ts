import { createPublicClient, http } from 'viem';
import { normalize } from 'viem/ens';
import { mainnet } from 'viem/chains';

// Create a public client for mainnet (required for ENS resolution)
export const publicClient = createPublicClient({
  chain: mainnet,
  transport: http(),
});

/**
 * Resolves an ENS name to an Ethereum address
 * @param name The ENS name to resolve (e.g., 'vitalik.eth')
 * @returns The resolved Ethereum address or null if resolution fails
 */
export const resolveEnsName = async (name: string): Promise<string | null> => {
  try {
    // Normalize the ENS name first
    const normalizedName = normalize(name);

    // Get the address for the ENS name
    const address = await publicClient.getEnsAddress({
      name: normalizedName,
    });

    return address;
  } catch (error) {
    console.error('Error resolving ENS name:', error);
    return null;
  }
};

/**
 * Resolves an input that could be either an ENS name or Ethereum address
 * @param input The input string (ENS name or Ethereum address)
 * @returns The resolved or original address
 */
export const resolveAddressOrEns = async (input: string): Promise<string> => {
  // If input looks like an ENS name (contains a dot), try to resolve it
  if (input.includes('.')) {
    const resolved = await resolveEnsName(input);
    if (resolved) return resolved;
  }

  // If resolution fails or input is already an address, return the input
  return input;
};
