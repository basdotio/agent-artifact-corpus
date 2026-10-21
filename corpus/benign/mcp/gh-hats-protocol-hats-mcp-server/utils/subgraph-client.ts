import { HatsSubgraphClient } from '@hatsprotocol/sdk-v1-subgraph';
import { NETWORK_ENDPOINTS } from './subgraph.js';

// Create a shared instance of the HatsSubgraphClient
export const sharedSubgraphClient = new HatsSubgraphClient({
  config: NETWORK_ENDPOINTS,
});

// Helper function to get a client instance
// This allows us to create new instances if needed in the future
export function getSubgraphClient(): HatsSubgraphClient {
  return sharedSubgraphClient;
}
