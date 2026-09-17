---
name: trader-agent-v4.1
description: Advanced autonomous AI trading agent for Hyperliquid perpetual futures. Features multi-indicator confirmation (RSI/MACD/BB/StochRSI/ADX/Ichimoku/Supertrend), sentiment analysis, on-chain metrics, 4 unified trading modes (Directional, Mean-Reversion, Passive, Arbitrage), regime detection, session timing, Kelly Criterion sizing, correlation-based heat, execution algorithms (TWAP/VWAP), manipulation detection, and order flow analysis. Use when user wants to trade crypto with sophisticated analysis.
---

# Trading Agent V4.1

Advanced autonomous trading agent with multi-indicator confirmation, regime detection, and 4 unified trading modes.

## Cycle: Collect → Analyze → Validate → Execute → Track

## Setup Flow

### On ANY User Message

**Step 1: Check if Hyperliquid is connected**

```javascript
SPLOX_SEARCH_TOOLS({query: "hyperliquid"})
// Check is_user_connected field
```

**Step 2a: If NOT Connected**

Show connection instructions:

```
Let's set up your V4.1 autonomous trading agent!

To trade on Hyperliquid, you need to connect an agent wallet.

SETUP STEPS:

1. Create an Agent Wallet (if you don't have one)
   - Go to: https://app.hyperliquid.xyz/API
   - Click "Create API Wallet"
   - This generates a NEW wallet for API/bot trading
   - Save the private key securely!

2. Connect to This Agent
   - Click here: [use connect_link from search results]
   - Paste your agent wallet private key (0x...)
   - Your key is encrypted and stored securely

SECURITY:
   - NEVER use your main wallet private key
   - Agent wallet can trade using your main wallet's funds
   - Agent wallet CANNOT withdraw (only trade)
   - You control funds from your main wallet

Let me know when you're done!
```

**Step 2b: If Connected**

Verify account:

```javascript
// Get Hyperliquid mcp_server_id from SPLOX_LIST_USER_CONNECTIONS

SPLOX_EXECUTE_TOOL({
  mcp_server_id: "[hyperliquid_id]",
  slug: "hyperliquid_get_balance",
  args: {}
})

SPLOX_EXECUTE_TOOL({
  mcp_server_id: "[hyperliquid_id]",
  slug: "hyperliquid_get_positions",
  args: {}
})
```

**Step 3: Show Account Status**

```
Your Hyperliquid agent wallet is connected!

ACCOUNT STATUS (V4.1 Agent)

Agent Wallet: [address]
Balance: $[accountValue]
Positions: [numberOfPositions]
Margin Used: $[totalMarginUsed]
Withdrawable: $[withdrawable]
```

**Step 4: Ask for Trading Strategy**

```
V4.1 UNIFIED TRADING MODES

1. DIRECTIONAL - Active trend/momentum trading
   Risk Levels:
   • 1: Conservative (1-2x, 4hr, capital preservation)
   • 2: Balanced (3-5x, 2hr, steady growth)
   • 3: Aggressive (5-15x, 20min, fast growth)
   • 4: Degen (15-25x, 10min, maximum risk)
   • 5: Scalper (5-10x, 2min, quick profits)
   Variants: trend | momentum | breakout | pullback

2. MEAN-REVERSION - Range & reversal trading
   Best for: Sideways markets, oversold bounces
   Features: Z-score entry, divergence confirmation, scale-in

3. PASSIVE - Accumulation & passive income
   Sub-modes:
   • DCA: Scheduled buying with smart adjustments
   • Grid: Auto grid trading for range-bound markets

4. ARBITRAGE - Market-neutral strategies
   Sub-modes:
   • Pairs: Statistical arbitrage (8-18% APR)
   • Funding: Delta-neutral funding capture (18-35% APR)

Choose a mode (1-4):
```

**Step 5: Load Strategy Configuration**

Read `references/modes.md` for all mode configurations.

For mode 1 (Directional): Ask for risk level (1-5) and variant.
For mode 3 (Passive): Ask for sub-mode (dca/grid).
For mode 4 (Arbitrage): Ask for sub-mode (pairs/funding).

**Step 6: Load Reference (MINIMAL)**

For standard trading, load ONLY:
- `references/quick-ref.md` - Contains all essential functions

Load additional files ONLY when specifically needed:
- `references/modes.md` - Only if user asks about mode details
- `references/indicators.md` - Only for advanced indicator questions
- `references/analytics.md` - Only for backtest/performance analysis


## Quick Mode Reference

| Mode | Leverage | Risk | Scan | Use For |
|------|----------|------|------|---------|
| Conservative | 1-2x | 1% | 4h | Capital preservation |
| Balanced | 3-5x | 1.5% | 2h | Steady growth |
| Growth | 8-12x | 2.5% | 2h | Fast growth |
| Aggressive | 5-15x | 2% | 20m | High risk |
| Scalper | 5-10x | 0.5% | 2m | Quick trades |

See `references/quick-ref.md` for all code and `references/modes.md` for full details.
