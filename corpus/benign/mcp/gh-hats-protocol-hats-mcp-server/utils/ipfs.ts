import { type KeyRestrictions } from '../types/index.js';
import fetch from 'node-fetch';
import pkg from 'lodash';
const { gt, toNumber, isEqual } = pkg;
import { CID } from 'multiformats/cid';
import * as json from 'multiformats/codecs/json';
import { sha256 } from 'multiformats/hashes/sha2';

const MAX_KEY_USES = 60;
const { PINATA_JWT } = process.env;

export const ipfsUrl = (hash: string) => {
  if (!hash) return null;
  // You can add multiple gateways here for redundancy
  return `https://ipfs.io/ipfs/${hash}`;
};

interface PinataResponse {
  IpfsHash: string;
  JWT: string;
}

// Add token generation function
const generateApiKey = async (keyRestrictions: KeyRestrictions) => {
  const options = {
    method: 'POST',
    headers: {
      accept: 'application/json',
      'content-type': 'application/json',
      authorization: `Bearer ${PINATA_JWT}`,
    },
    body: JSON.stringify(keyRestrictions),
  };

  return fetch('https://api.pinata.cloud/users/generateApiKey', options)
    .then((response) => response.json())
    .then((json) => {
      const { JWT } = json as PinataResponse;
      return JWT;
    })
    .catch((error) => {
      console.error(error);
      return null;
    });
};

// Add function to get a temporary token
export const getTemporaryToken = async (count?: number) => {
  const date = new Date();
  const keyRestrictions: KeyRestrictions = {
    keyName: `Signed Upload JWT-${date.toISOString()}`,
    maxUses: 2,
    permissions: {
      endpoints: {
        data: {
          pinList: false,
          userPinnedDataTotal: false,
        },
        pinning: {
          pinFileToIPFS: true, // image
          pinJSONToIPFS: true, // json
          pinJobs: false,
          unpin: true, // image (both?)
          userPinPolicy: false,
        },
      },
    },
  };

  if (gt(toNumber(count), 0)) {
    keyRestrictions.maxUses = gt(toNumber(count), MAX_KEY_USES)
      ? MAX_KEY_USES
      : toNumber(count);
  }

  try {
    const apiKey = await generateApiKey(keyRestrictions);
    return apiKey;
  } catch (error) {
    console.error(error);
    return null;
  }
};

export const fetchIpfs = async (value: string | undefined) => {
  if (!value) return { details: '', data: null };

  let hash = value;
  if (hash.startsWith('ipfs://')) {
    hash = hash.slice(7);
  }

  const url = ipfsUrl(hash);
  if (!url) return { details: hash, data: null };

  // timeout for slow IPFS gateways
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 5000);

  try {
    const response = await fetch(url, { signal: controller.signal });

    // Try text first, then JSON if text fails
    try {
      const textBody = await response.text();
      if (textBody) {
        try {
          // Attempt to parse as JSON first
          const jsonData = JSON.parse(textBody);
          return { details: hash, data: jsonData };
        } catch {
          // If JSON parse fails, return as text
          return { details: hash, data: textBody };
        }
      }
    } catch {
      const result = await response.json();
      return { details: hash, data: result || null };
    }
  } catch (err) {
    console.error('IPFS fetch error:', err);
    return { details: hash, data: null };
  } finally {
    clearTimeout(timeoutId);
  }
};

export const pinJson = async (
  data: object,
  metadata: object,
  token: string
) => {
  const pinataData = JSON.stringify({
    pinataOptions: { cidVersion: 1 },
    pinataMetadata: { ...metadata },
    pinataContent: data,
  });

  console.log('pinning json', { pinataData });
  const url = 'https://api.pinata.cloud/pinning/pinJSONToIPFS';
  const config = {
    method: 'post',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: pinataData,
  };

  const res = await fetch(url, config);
  const resultData = (await res.json()) as PinataResponse;
  console.log('resultData', { resultData });
  return resultData.IpfsHash;
};

/**
 * Calculates the IPFS CID for a JSON object
 * @param data The JSON object to calculate the CID for
 * @returns The CID string prefixed with "ipfs://"
 */
export const calculateCid = async (data: object): Promise<string> => {
  try {
    const bytes = json.encode(data);

    // Calculate the hash of the bytes
    const hash = await sha256.digest(bytes);

    // Create a CID with the JSON codec and SHA-256 hash
    const cid = await CID.create(1, json.code, hash);

    // Return the CID as a string with ipfs:// prefix
    return `ipfs://${cid.toString()}`;
  } catch (error) {
    console.error('Error calculating CID:', error);
    throw new Error('Failed to calculate CID for data');
  }
};

/**
 * Calculates CID and pins the content to IPFS in one operation
 * @param data The JSON object to pin
 * @param metadata Optional Pinata metadata
 * @returns The IPFS CID with ipfs:// prefix
 */
export const calculateAndPinJson = async (
  data: object,
  metadata: object = {}
): Promise<string> => {
  try {
    // Wrap the data in the expected structure
    const formattedData = {
      type: '1.0',
      data,
    };

    // First calculate the CID - this matches what useCid does
    const calculatedCid = await calculateCid(formattedData);

    // Strip ipfs:// prefix for comparison
    const expectedHash = calculatedCid.replace('ipfs://', '');

    // Use the main PINATA_JWT directly instead of getting a temporary token
    if (!PINATA_JWT) {
      throw new Error('PINATA_JWT environment variable is not set');
    }

    // Pin the content using the main JWT
    const pinnedHash = await pinJson(formattedData, metadata, PINATA_JWT);
    if (!pinnedHash) {
      throw new Error('Failed to pin content to IPFS');
    }

    // Verify the pinned hash matches our calculated CID
    if (!isEqual(pinnedHash, expectedHash)) {
      console.warn('Pinned hash does not match calculated CID', {
        pinnedHash,
        expectedHash,
      });
    }

    // Return the calculated CID to match useCid behavior
    return calculatedCid;
  } catch (error) {
    console.error('Error in calculateAndPinJson:', error);
    throw error;
  }
};
