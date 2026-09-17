# x402 Skill - Agent Payments Protocol

Native HTTP payments for AI agents using the x402 protocol.

## Triggers
- `/x402` - Check status, balances
- `x402 pay` - Pay for a resource
- `x402 status` - Check payment status
- `agent payment`, `pay agent`, `micropayment`

## Overview

x402 is Coinbase's open protocol for HTTP-native payments. When a server returns `402 Payment Required`, the client automatically pays and retries.

**Flow:**
1. Request resource → Server returns 402 + payment requirements
2. Client creates signed payment payload
3. Client retries with `PAYMENT-SIGNATURE` header
4. Server verifies payment via facilitator, returns resource

## Client Commands

```bash
# Check status
node skills/x402/scripts/x402.js status --keystore <path>

# Pay for a resource (auto-handles 402)
node skills/x402/scripts/x402.js fetch --url <url> --keystore <path>

# Quote a payment (without executing)
node skills/x402/scripts/x402.js quote <url>

# Check payment history
node skills/x402/scripts/x402.js history
```

## Flare Facilitator 🔥

We run a Flare-native x402 facilitator for agent payments using USD₮0.

### Starting the Facilitator

```bash
# Set facilitator wallet (pays gas)
export FACILITATOR_PRIVATE_KEY=0x...

# Or create key file
echo '{"privateKey":"0x..."}' > skills/x402/facilitator/facilitator-key.json

# Start server
cd skills/x402/facilitator && ./start.sh

# Or with custom port
X402_PORT=3402 node skills/x402/facilitator/server.js
```

### Facilitator Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check + status |
| `/requirements` | GET | Payment requirements |
| `/verify` | POST | Verify payment signature |
| `/settle` | POST | Execute payment on-chain |

### Why Flare?

- **EIP-3009 native**: USD₮0 supports `transferWithAuthorization`
- **Fast finality**: ~3 second blocks
- **Cheap gas**: Fractions of a cent per tx
- **Stablecoin ready**: USD₮0 is native Tether

## Supported Networks

| Network | Chain ID | Token | Method |
|---------|----------|-------|--------|
| Flare 🔥 | 14 | USD₮0 | EIP-3009 |
| Base | 8453 | USDC | EIP-3009 |
| Ethereum | 1 | USDC | EIP-3009 |

## Integration Example

```javascript
import { wrapFetchWithPaymentFromConfig } from '@x402/fetch';
import { ExactEvmScheme } from '@x402/evm';
import { privateKeyToAccount } from 'viem/accounts';

const account = privateKeyToAccount('0x...');

const x402Fetch = wrapFetchWithPaymentFromConfig(fetch, {
  schemes: [{
    network: 'eip155:14', // Flare
    client: new ExactEvmScheme(account)
  }]
});

// Auto-pays if 402
const response = await x402Fetch('https://api.example.com/paid-endpoint');
```

## Architecture

```
Agent A (payer)
    │ Signs EIP-3009 authorization
    ▼
Resource Server (API)
    │ Verifies via facilitator
    ▼
Flare Facilitator ← We run this!
    │ Settles on-chain (pays gas)
    ▼
Flare Network
    └── USD₮0 transfer
```

## Wallet Gen (for Agents)

Generate EVM wallets for AI agents to participate in x402 payments.

```bash
# Generate new wallet
node skills/x402/wallet-gen/scripts/wallet.js gen --name my-agent

# Show wallet address + balance
node skills/x402/wallet-gen/scripts/wallet.js show --name my-agent

# List all wallets
node skills/x402/wallet-gen/scripts/wallet.js list

# Export private key (careful!)
node skills/x402/wallet-gen/scripts/wallet.js export --name my-agent --confirm
```

See `wallet-gen/SKILL.md` for full documentation.

## Agent Tips (m/payments)

Fee-sharing widget for AI agents. Tip your favorite agents on Moltbook, X, or GitHub.

**Location:** `apps/agent-tips/`

**Features:**
- Multi-chain (Flare + HyperEVM)
- RainbowKit wallet connect
- Pool-funded or wallet-funded tips
- Leaderboard

```bash
cd skills/x402/apps/agent-tips
npm install
npm run dev  # http://localhost:3456
```

## References

- x402 Spec: https://github.com/coinbase/x402
- x402.org: https://x402.org
- EIP-3009: https://eips.ethereum.org/EIPS/eip-3009
