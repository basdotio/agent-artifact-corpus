import {
  createPublicClient,
  http,
  type PublicClient,
  type Address,
  type WalletClient,
  type Hex,
  type Chain,
  zeroAddress,
} from 'viem';
import {
  mainnet,
  optimism,
  sepolia,
  base,
  polygon,
  arbitrum,
} from 'viem/chains';
import { HatsModulesClient } from '@hatsprotocol/modules-sdk';
import { FALLBACK_ADDRESS } from '../src/common/constants.js';
import { getChainName } from './chains.js';
import type { HatsSubgraphClient } from '@hatsprotocol/sdk-v1-subgraph';
import { getSubgraphClient } from './subgraph-client.js';

// Create a public client for the chain
export function viemPublicClient(chainId: number): PublicClient {
  let chain: Chain;

  // Map chainId to appropriate chain
  switch (chainId) {
    case 1:
      chain = mainnet;
      break;
    case 10:
      chain = optimism;
      break;
    case 11155111:
      chain = sepolia;
      break;
    case 8453:
      chain = base;
      break;
    case 137:
      chain = polygon;
      break;
    case 42161:
      chain = arbitrum;
      break;
    default:
      throw new Error(
        `Unsupported chain ID: ${chainId} (${getChainName(chainId)})`
      );
  }

  return createPublicClient({
    chain,
    transport: http(),
  });
}

// Format module parameters into readable form
function formatModuleParams(params: any[]): string[] {
  return params.map((param) => {
    if (typeof param === 'object' && param !== null) {
      return JSON.stringify(param, null, 2);
    }
    return String(param);
  });
}

// Create and prepare a HatsModulesClient
export async function createHatsModulesClient(
  chainId: number | undefined,
  walletClient?: WalletClient | undefined // required for write functions
): Promise<HatsModulesClient | null> {
  if (!chainId) return Promise.resolve(null);

  const publicClient = viemPublicClient(chainId);

  const modulesClient = new HatsModulesClient({
    publicClient,
    walletClient,
  });

  // Will look up all modules in registry but can be configured to
  // handle a specific module if passed as argument
  await modulesClient.prepare();

  return Promise.resolve(modulesClient);
}

// Known module implementations
export const KNOWN_ELIGIBILITY_MODULES: { [key: string]: Hex[] } = {
  agreement: [
    '0x4F10B9e99ce11f081652646f4b192ed1b812D5Bb', // v0.0.4
    '0x6AE5a62698f23dB7CAca13FFa7391ac782a94116', // v0.0.3
    '0x8126d02F4EcDE43eca4543a0D90B755C3E225F09', // v0.0.2
    '0xF6bc6Dd30403e6ff5b3Bebead32B8fce1b753aA1', // v0.0.1
  ],
  allowlist: [
    '0x80336fb7b6B653686eBe71d2c3ee685b70108B8f', // v0.0.3
    '0x5302757E4CEAD88d52D014113FCC8cb51dd36255', // v0.0.2
    '0xaC208e6668DE569C6ea1db76DeCea70430335Ed5', // v0.0.1
  ],
  election: [
    '0xd3b916a8F0C4f9D1d5B6Af29c3C012dbd4f3149E', // v0.0.2
    '0x99081d45920818557203CCD62eD36dC2FaD9a43E', // v0.0.1
  ],
  jokeRace: [
    '0x0Bb0a2B9bc5Da206fead8e87D7Cbc6fCBa455320', // v0.0.3
    '0xAE0e56A0c509dA713722c1aFFcF4B5f1C6CDc73a', // v0.0.2
    '0x2bb30E1786a656EC6cD81e79EEf1A28607c9AE5A', // v0.0.1
  ],
  unlock: [
    '0x4c7803041851f7a17Fc6b5Ff5c911FC748160637', // v0.1.2
  ],
  staking: ['0x9E01030aF633Be5a439DF122F2eEf750b44B8aC7'], // v0.1.0
  passthrough: ['0x050079a8fbFCE76818C62481BA015b89567D2d35'], // v0.1.0
  baalStaking: ['0xa1E79f78630F77436C001Af44893A2720180E19F'], // v0.1.0
  erc20: ['0xbA5b218e6685D0607139c06f81442681a32a0EC3'],
  erc721: ['0xF37cf12fB4493D29270806e826fDDf50dd722bab'],
  erc1155: ['0x0089FbD2e0c42F2090890e1d9A3bd8d40E0e2e17'],
  hatWearing: ['0xa2e614CE4FAaD60e266127F4006b812d69977265'],
  eligibilityChain: [
    '0x8AdED513a191e3FeE91Bb192Aba20FcC9c16aF2e', // v0.0.2
    '0x83200f1633cDb6C8f28F202CEA1B6a9105862D83', // v0.0.1
  ],
};

/**
 * Get the module type for a given implementation address
 */
export function getKnownEligibilityModule(
  implementationAddress: Hex
): string | undefined {
  const knownModuleKeys = Object.keys(KNOWN_ELIGIBILITY_MODULES);
  const knownModuleKey = knownModuleKeys.find((key) =>
    KNOWN_ELIGIBILITY_MODULES[key].includes(implementationAddress)
  );

  return knownModuleKey;
}

/**
 * Get detailed information about a module at a specific address
 */
export async function getModuleInfo(
  moduleAddress: Address
): Promise<ModuleInfo> {
  try {
    // Check if this is a known module implementation
    const moduleType = getKnownEligibilityModule(moduleAddress as Hex);
    console.log('moduleType', moduleType);

    if (moduleType) {
      console.log('moduleType', moduleType);
      return {
        details: {
          name: moduleType,
          id: moduleAddress,
          version: 'latest', // Could be enhanced to track versions
        },
      };
    }

    // If not a known implementation, return empty object
    return {};
  } catch (error) {
    console.error('Error getting module info:', error);
    return {};
  }
}

export interface ModuleInfo {
  details?: {
    name?: string;
    id?: string;
    version?: string;
  };
  parameters?: Array<{
    label: string;
    value: unknown;
    solidityType: string;
    displayType: string;
  }>;
}

/**
 * Get eligibility rules for a module at a specific address
 */
export const getEligibilityRules = async ({
  address,
  chainId,
}: {
  address: Hex | undefined;
  chainId: number | undefined;
}) => {
  // Additional safety checks from the original implementation
  if (
    !chainId ||
    !address ||
    address === FALLBACK_ADDRESS ||
    address === zeroAddress
  ) {
    return null;
  }

  try {
    const modulesClient = await createHatsModulesClient(chainId);

    if (!modulesClient) {
      throw new Error('Unable to initialize modulesClient');
    }

    const ruleSets = await modulesClient.getRulesets(address, {
      includeLiveParams: true,
    });

    // Format the rules in a human-readable way
    const formattedRules = ruleSets?.map((ruleSet) =>
      ruleSet.map((rule) => ({
        name: rule.module.name,
        version: rule.module.version,
        description: rule.module.details?.join('\n'),
        parameters: rule.liveParams?.map((param) => ({
          label: param.label,
          value:
            typeof param.value === 'bigint'
              ? param.value.toString()
              : typeof param.value === 'string'
              ? param.value
              : typeof param.value === 'number'
              ? param.value.toString()
              : String(param.value),
          type: param.displayType || param.solidityType,
        })),
      }))
    );

    console.log('ruleSets', JSON.stringify(formattedRules, null, 2));

    return formattedRules || null;
  } catch (err) {
    console.error('Error getting eligibility rules:', err);
    return null;
  }
};

/**
 * Check if an address is eligible for a hat and get their current wearing status
 */
export const checkHatEligibility = async ({
  hatId,
  address,
  chainId,
  eligibilityModule,
}: {
  hatId: string;
  address: Address;
  chainId: number;
  eligibilityModule: Address | null;
}): Promise<{
  isEligible: boolean;
  isWearing: boolean;
  inGoodStanding: boolean;
  canClaim: boolean;
  reasons?: string[];
}> => {
  try {
    // Initialize default response
    const response = {
      isEligible: false,
      isWearing: false,
      inGoodStanding: true,
      canClaim: false,
      reasons: [] as string[],
    };

    // Create modules client
    const modulesClient = await createHatsModulesClient(chainId);
    if (!modulesClient) {
      response.reasons?.push('Unable to initialize modules client');
      return response;
    }

    // Check if address is already wearing the hat
    console.log('\n=== Getting Subgraph Client ===');
    const client = getSubgraphClient();
    const wearer = await client.getWearer({
      chainId,
      wearerAddress: address,
      props: {
        currentHats: {
          props: {
            prettyId: true,
            status: true,
          },
        },
      },
    });

    // Check if they're wearing the hat
    if (wearer?.currentHats) {
      const hatBeingWorn = wearer.currentHats.find(
        (hat) => hat.prettyId === hatId
      );
      if (hatBeingWorn) {
        response.isWearing = true;
        response.inGoodStanding = hatBeingWorn.status ?? true;
        response.reasons?.push(
          response.inGoodStanding
            ? 'Already wearing hat in good standing'
            : 'Wearing hat but not in good standing'
        );
        return response;
      }
    }

    // If there's no eligibility module, they can claim if not already wearing
    if (!eligibilityModule) {
      response.isEligible = true;
      response.canClaim = true;
      response.reasons?.push('No eligibility module - hat can be claimed');
      return response;
    }

    // Get eligibility rules
    const rules = await getEligibilityRules({
      address: eligibilityModule,
      chainId,
    });

    if (!rules || rules.length === 0) {
      response.reasons?.push('No eligibility rules found');
      return response;
    }

    // Check eligibility against each rule set
    // Note: This is a simplified check - in reality we need to implement specific checks
    // for each type of eligibility module
    let eligible = true;
    for (const ruleSet of rules) {
      for (const rule of ruleSet) {
        // Here we would implement specific checks based on rule.name
        // For now we're just logging what would need to be checked
        console.log(
          `Would check rule: ${rule.name} with parameters:`,
          rule.parameters
        );

        // TODO: Implement specific checks for each module type
        // This would involve checking things like:
        // - Agreement signing status
        // - Token balances for ERC20/721/1155
        // - Staking requirements
        // - etc.
      }
    }

    response.isEligible = eligible;
    response.canClaim = eligible;
    if (eligible) {
      response.reasons?.push('Meets all eligibility requirements');
    } else {
      response.reasons?.push('Does not meet all eligibility requirements');
    }

    return response;
  } catch (error) {
    console.error('Error checking eligibility:', error);
    return {
      isEligible: false,
      isWearing: false,
      inGoodStanding: false,
      canClaim: false,
      reasons: [(error as Error).message],
    };
  }
};
