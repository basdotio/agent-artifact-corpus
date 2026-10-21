import type { HatPropsConfig } from '@hatsprotocol/sdk-v1-subgraph';

interface TreePropsConfig {
  hats?: {
    props: HatPropsConfig;
    filters?: {
      first?: number;
      skip?: number;
    };
  };
}
