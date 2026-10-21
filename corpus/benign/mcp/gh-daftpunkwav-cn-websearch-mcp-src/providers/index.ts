/**
 * @file providers/index
 * @description Provider registry: maps provider names to adapter factories.
 *
 * Responsibilities:
 * - Maintain the map from provider name to adapter factory
 * - Build adapter instances in the configured order
 * - Guarantee that adding a provider takes one adapter file plus one registration line here
 */

// Provider registry. Adding a provider = one adapter file + one registration line here.

import type { GatewayConfig, ProviderConfig, ProviderName } from '../config.js';
import type { SearchProvider } from '../types.js';
import createKimiProvider from './kimi.js';
import createMimoProvider from './mimo.js';
import createStepfunProvider from './stepfun.js';
import createZhipuProvider from './zhipu.js';

const FACTORIES: Record<ProviderName, (cfg: ProviderConfig) => SearchProvider> = {
  kimi: createKimiProvider,
  mimo: createMimoProvider,
  stepfun: createStepfunProvider,
  zhipu: createZhipuProvider,
};

/** Builds adapter instances in the configured order (enabled/key checks are left to the caller). */
export default function buildProviders(cfg: GatewayConfig): SearchProvider[] {
  return cfg.order.map((name) => FACTORIES[name](cfg.providers[name]));
}
