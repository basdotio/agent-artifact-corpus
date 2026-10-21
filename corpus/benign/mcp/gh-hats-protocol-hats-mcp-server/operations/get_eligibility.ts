import { z } from 'zod';
import type { CallToolResult } from '@modelcontextprotocol/sdk/types.js';
import type { HatsSubgraphClient } from '@hatsprotocol/sdk-v1-subgraph';
import type { Hat } from '@hatsprotocol/sdk-v1-subgraph';
import {
  getChainId,
  isChainSupported,
  getSupportedChains,
} from '../utils/chains.js';
import { getModuleInfo, getEligibilityRules } from '../utils/modules.js';
import { normalizeHatId } from '../utils/hat-utils.js';
import type { Address, Hex } from 'viem';
import { chunkResponse } from '../utils/response.js';
import { resolveAddressOrEns } from '../utils/viem.js';
import { getSubgraphClient } from '../utils/subgraph-client.js';

// Define the parameters schema
const parameters = z.object({
  hatId: z.string(), // Hat ID in hex or human-readable format
  chain: z.string(),
  chainId: z.number(),
  address: z.string(), // Address to check eligibility for
});

interface ModuleCheck {
  name: string;
  version: string;
  isEligible: boolean;
  reason?: string;
  parameters?: Array<{
    label: string;
    value: string;
    type: string;
  }>;
}

interface EligibilityStatus {
  address: string;
  hatId: string;
  chain: string;
  chainId: number;
  isEligible: boolean;
  isWearing: boolean;
  inGoodStanding: boolean;
  canClaim: boolean;
  reasons: string[];
  moduleChecks?: ModuleCheck[];
}

async function checkEligibility(
  args: z.infer<typeof parameters>,
  client: HatsSubgraphClient
): Promise<CallToolResult> {
  console.log('\n=== Starting Eligibility Check ===');

  try {
    // Normalize the hat ID to support both formats
    const normalizedHatId = normalizeHatId(args.hatId);
    console.log(`Normalized hat ID from ${args.hatId} to ${normalizedHatId}`);

    // Resolve ENS name if provided
    const resolvedAddress = await resolveAddressOrEns(args.address);
    console.log('Resolved address:', resolvedAddress);

    // First get the hat to check its eligibility module
    const hat = await client.getHat({
      chainId: args.chainId,
      hatId: BigInt(normalizedHatId),
      props: {
        prettyId: true,
        status: true,
        eligibility: true,
        maxSupply: true,
        currentSupply: true,
        wearers: {
          props: {
            currentHats: {
              props: {
                prettyId: true,
                status: true,
              },
            },
          },
        },
      },
    });

    if (!hat) {
      return {
        _meta: {},
        content: [
          {
            type: 'text',
            text: `No hat found with ID ${normalizedHatId} on chain ${args.chain}`,
          },
        ],
      };
    }

    // Initialize response
    const status: EligibilityStatus = {
      address: resolvedAddress,
      hatId: args.hatId,
      chain: args.chain,
      chainId: args.chainId,
      isEligible: false,
      isWearing: false,
      inGoodStanding: true,
      canClaim: false,
      reasons: [],
      moduleChecks: [],
    };

    // Check if hat is active
    if (!hat.status) {
      status.reasons.push('Hat is not active');
      return chunkResponse(status);
    }

    // Check supply
    const maxSupply = BigInt(hat.maxSupply || '0');
    const currentSupply = BigInt(hat.currentSupply || '0');
    if (maxSupply > 0 && currentSupply >= maxSupply) {
      status.reasons.push('Hat has reached maximum supply');
      return chunkResponse(status);
    }

    // Check if already wearing
    if (hat.wearers) {
      const wearer = hat.wearers.find(
        (w) => w.id.toLowerCase() === resolvedAddress.toLowerCase()
      );
      if (wearer?.currentHats) {
        const hatBeingWorn = wearer.currentHats.find(
          (hat: Hat) => hat.prettyId === args.hatId
        );
        if (hatBeingWorn) {
          status.isWearing = true;
          status.inGoodStanding = hatBeingWorn.status ?? true;
          status.reasons.push(
            status.inGoodStanding
              ? 'Already wearing hat in good standing'
              : 'Wearing hat but not in good standing'
          );
          return chunkResponse(status);
        }
      }
    }

    // Check eligibility modules
    if (hat.eligibility) {
      const moduleInfo = await getModuleInfo(hat.eligibility);
      const rules = await getEligibilityRules({
        address: hat.eligibility as Hex,
        chainId: args.chainId,
      });

      if (moduleInfo && rules && rules.length > 0) {
        status.moduleChecks = [];
        let allEligible = true;

        // Handle each ruleset (outer array)
        for (const ruleSet of rules) {
          // Handle each rule in the ruleset (inner array)
          for (const rule of ruleSet) {
            const moduleCheck: ModuleCheck = {
              name: rule.name,
              version: rule.version,
              isEligible: false, // Will be set by eligibility check
              parameters: rule.parameters,
            };

            // TODO: Implement actual eligibility check for each rule
            // For now, we'll assume eligible
            moduleCheck.isEligible = true;

            if (!moduleCheck.isEligible) {
              allEligible = false;
              moduleCheck.reason = 'Does not meet module requirements';
            }

            status.moduleChecks.push(moduleCheck);
          }
        }

        status.isEligible = allEligible;
        status.canClaim = allEligible && !status.isWearing;
      } else {
        status.reasons.push('Unable to check eligibility modules');
      }
    } else {
      status.reasons.push('No eligibility modules found');
      status.isEligible = true;
      status.canClaim = !status.isWearing;
    }

    return chunkResponse(status);
  } catch (error) {
    console.error('Eligibility Check Error:', error);
    return {
      _meta: {},
      content: [
        {
          type: 'text',
          text: `Error during eligibility check: ${
            error instanceof Error ? error.message : 'Unknown error'
          }`,
        },
      ],
    };
  }
}

// Define the operation interface
interface GetEligibilityOperation {
  name: string;
  description: string;
  parameters: typeof parameters;
  execute: (args: z.infer<typeof parameters>) => Promise<CallToolResult>;
}

export const getEligibilityOperation: GetEligibilityOperation = {
  name: 'get_eligibility',
  description: `Get detailed information about an address's eligibility for a specific Hat.

### Examples
Examples of cases when to use the tool and the arguments to extract:

- Check eligibility:
  "Can address 0xabc claim hat 0x1234 on optimism?"
  {"hatId": "0x1234", "chain": "optimism", "chainId": 10, "address": "0xabc"}

### Response Format
The response will include:
- Basic eligibility status
- Current wearing status
- Standing status
- Ability to claim
- Detailed reasons for eligibility/ineligibility
- Module-specific check results

### Available Properties
The following properties are included:
- isEligible: Whether the address meets eligibility requirements
- isWearing: Whether the address is currently wearing the hat
- inGoodStanding: Whether the wearer is in good standing
- canClaim: Whether the address can claim the hat
- reasons: Detailed explanations of eligibility status
- moduleChecks: Results from individual eligibility module checks
`,
  parameters,
  async execute(args) {
    console.log('\n=== Starting Get Eligibility Operation ===');
    console.log('Args:', args);

    try {
      // Validate chain support
      if (!isChainSupported(args.chain)) {
        const supportedChains = getSupportedChains().join(', ');
        return {
          _meta: {},
          content: [
            {
              type: 'text',
              text: `Chain "${args.chain}" is not supported. Please use one of the supported chains: ${supportedChains}`,
            },
          ],
        };
      }

      // Get the proper chain ID from the chain name if provided
      const chainId = args.chain ? getChainId(args.chain) : args.chainId;
      args.chainId = chainId; // Ensure chainId is set in args

      console.log('\n=== Getting Subgraph Client ===');
      const client = getSubgraphClient();

      // Return the result directly without rewrapping
      return await checkEligibility(args, client);
    } catch (error) {
      console.error('Error in get eligibility operation:', error);
      return {
        _meta: {},
        content: [
          {
            type: 'text',
            text: `An error occurred while checking eligibility: ${
              error instanceof Error ? error.message : 'Unknown error'
            }`,
          },
        ],
      };
    }
  },
};
