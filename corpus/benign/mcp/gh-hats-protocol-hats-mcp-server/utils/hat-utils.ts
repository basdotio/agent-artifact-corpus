import {
  hatIdDecimalToIp,
  hatIdHexToDecimal,
  hatIdIpToDecimal,
} from '@hatsprotocol/sdk-v1-core';

/**
 * Utility functions for working with Hat IDs and related operations
 */

/**
 * Determines if a hat ID is in human-readable IP format (e.g., "1.3.2.2")
 * @param hatId The hat ID to check
 * @returns boolean indicating if the ID is in human-readable IP format
 */
export function isHumanReadableHatId(hatId: string): boolean {
  return /^\d+(\.\d+)*$/.test(hatId);
}

/**
 * Determines if a hat ID is in hex format (starts with 0x)
 * @param hatId The hat ID to check
 * @returns boolean indicating if the ID is in hex format
 */
export function isHexHatId(hatId: string): boolean {
  return hatId.startsWith('0x');
}

/**
 * Converts a human-readable hat ID (e.g., "1.2.3") to its hex representation
 * Uses the official Hats Protocol SDK conversion functions
 * @param humanReadableId The human-readable hat ID to convert
 * @returns The hex representation of the hat ID
 */
export function convertHumanReadableToHex(humanReadableId: string): string {
  // Convert IP format to decimal first, then to hex
  const decimal = hatIdIpToDecimal(humanReadableId);
  return `0x${decimal.toString(16).padStart(64, '0')}`;
}

/**
 * Converts a hex hat ID to human-readable IP format (e.g., "1.2.3")
 * Uses the official Hats Protocol SDK conversion functions
 * @param hexHatId The hex hat ID to convert
 * @returns The human-readable IP format of the hat ID
 */
export function convertHexToHumanReadable(hexHatId: string): string {
  // Remove 0x prefix and convert to decimal first, then to IP format
  const decimal = hatIdHexToDecimal(hexHatId);
  return hatIdDecimalToIp(decimal);
}

/**
 * Converts any hat ID format to its hex representation
 * @param hatId The hat ID in either human-readable IP or hex format
 * @returns The hex representation of the hat ID
 */
export function normalizeHatId(hatId: string): string {
  if (isHumanReadableHatId(hatId)) {
    return convertHumanReadableToHex(hatId);
  }

  if (isHexHatId(hatId)) {
    return hatId;
  }

  throw new Error(
    `Invalid hat ID format: ${hatId}. Expected either hex format (0x...) or IP format (1.2.3)`
  );
}

/**
 * Converts any hat ID format to human-readable IP format
 * @param hatId The hat ID in either hex or IP format
 * @returns The human-readable IP format of the hat ID
 */
export function toHumanReadableHatId(hatId: string): string {
  if (isHumanReadableHatId(hatId)) {
    return hatId;
  }

  if (isHexHatId(hatId)) {
    return convertHexToHumanReadable(hatId);
  }

  throw new Error(
    `Invalid hat ID format: ${hatId}. Expected either hex format (0x...) or IP format (1.2.3)`
  );
}
