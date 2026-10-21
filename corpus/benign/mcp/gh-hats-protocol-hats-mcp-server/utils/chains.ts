/**
 * Chain ID mappings and utilities for MCP operations
 */

import type { Chain } from 'viem';

export type SupportedChains =
  | 1 // mainnet
  | 10 // optimism
  | 100 // gnosis
  | 137 // polygon
  | 8453 // base
  | 42161 // arbitrum
  | 42220 // celo
  | 84532 // base sepolia
  | 11155111;

export type ExtendedChain = Chain & {
  hasIcon: boolean;
  iconUrl: string;
  iconBackground: string;
};

// Canonical chain names - use these as the source of truth
export const CHAIN_NAMES = {
  MAINNET: 'mainnet',
  BASE: 'base',
  OPTIMISM: 'optimism',
  POLYGON: 'polygon',
  ARBITRUM: 'arbitrum',
  SEPOLIA: 'sepolia',
  GNOSIS: 'gnosis',
  BASE_SEPOLIA: 'baseSepolia',
} as const;

// Chain name aliases for more flexible matching
export const CHAIN_ALIASES: Record<string, string> = {
  'base-sepolia': CHAIN_NAMES.BASE_SEPOLIA,
  base_sepolia: CHAIN_NAMES.BASE_SEPOLIA,
  basesepolia: CHAIN_NAMES.BASE_SEPOLIA,
  ethereum: CHAIN_NAMES.MAINNET,
  eth: CHAIN_NAMES.MAINNET,
  op: CHAIN_NAMES.OPTIMISM,
  arb: CHAIN_NAMES.ARBITRUM,
  'arbitrum-one': CHAIN_NAMES.ARBITRUM,
  arbitrum_one: CHAIN_NAMES.ARBITRUM,
  matic: CHAIN_NAMES.POLYGON,
  'polygon-pos': CHAIN_NAMES.POLYGON,
  xdai: CHAIN_NAMES.GNOSIS,
};

export const CHAINS: Record<string, number> = {
  [CHAIN_NAMES.MAINNET]: 1,
  [CHAIN_NAMES.BASE]: 8453,
  [CHAIN_NAMES.OPTIMISM]: 10,
  [CHAIN_NAMES.POLYGON]: 137,
  [CHAIN_NAMES.ARBITRUM]: 42161,
  [CHAIN_NAMES.SEPOLIA]: 11155111,
  [CHAIN_NAMES.GNOSIS]: 100,
  [CHAIN_NAMES.BASE_SEPOLIA]: 84532,
} as const;

/**
 * Normalize a chain name to its canonical form
 * @param chainName The name of the chain to normalize
 * @returns The canonical chain name
 */
export const normalizeChainName = (chainName: string): string => {
  const normalized = chainName.toLowerCase().trim();
  return CHAIN_ALIASES[normalized] || normalized;
};

/**
 * Convert a chain name to its corresponding chain ID
 * @param chainName The name of the chain
 * @returns The chain ID, defaults to mainnet (1) if chain not found
 */
export const getChainId = (chainName: string): number => {
  const normalized = normalizeChainName(chainName);
  return CHAINS[normalized] || 1; // Default to mainnet if chain not found
};

/**
 * Get the chain name from a chain ID
 * @param chainId The chain ID to look up
 * @returns The chain name or 'unknown' if not found
 */
export const getChainName = (chainId: number): string => {
  const entry = Object.entries(CHAINS).find(([_, id]) => id === chainId);
  return entry ? entry[0] : 'unknown';
};

/**
 * Check if a chain is supported
 * @param chainName The name of the chain to check
 * @returns boolean indicating if the chain is supported
 */
export const isChainSupported = (chainName: string): boolean => {
  const normalized = normalizeChainName(chainName);
  return normalized in CHAINS;
};

/**
 * Get a list of all supported chain names
 * @returns Array of supported chain names
 */
export const getSupportedChains = (): string[] => {
  return Object.keys(CHAINS);
};
