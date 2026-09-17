---
name: go-live
description: Pre-flight checks and deployment procedure for live trading. Use when deploying to mainnet, going live with a new asset, or transitioning from paper to live. Covers code parity audit, config validation, first-30-min monitoring, and rollback.
disable-model-invocation: true
context: fork
agent: general-purpose
argument-hint: "[asset]"
allowed-tools: Read, Grep, Glob, Bash
---

# Go-Live Workflow

Pre-flight checklist and deployment procedure for transitioning from paper trading to live mainnet. This workflow catches the bugs that cost real money -- the ones where paper looks great but live silently degrades because a learning loop is missing or a config flag is wrong.

**When to use**: Deploying to mainnet for the first time, adding a new asset to live trading, or redeploying after significant code changes.

**Key files**:
```
src/bin/market_maker.rs                              # Binary: CLI args, paper/live mode setup
src/market_maker/orchestrator/handlers.rs            # Fill handlers with all learning loops
src/market_maker/orchestrator/quote_engine.rs        # Quote generation pipeline
src/market_maker/fills/processor.rs                  # Unified fill processing (FillProcessor)
src/market_maker/config/auto_derive.rs               # First-principles parameter derivation
src/market_maker/risk/state.rs                       # Risk state including drawdown calculation
src/market_maker/risk/kill_switch.rs                 # Emergency shutdown logic
src/market_maker/strategy/signal_integration.rs      # Signal hub with staleness detection
src/market_maker/analytics/live.rs                   # LiveAnalytics (Sharpe, attribution, logging)
src/market_maker/learning/quote_outcome.rs           # QuoteOutcomeTracker for unbiased edge
src/market_maker/learning/baseline_tracker.rs        # RL counterfactual reward baseline
```

---

## Phase 1: Paper Validation Review

Before going live, the paper trader must demonstrate viable performance. Run paper trading for at least 24 hours on real market data and verify these minimum thresholds:

### Minimum Thresholds

| Metric | Threshold | How to Check | Why |
|--------|-----------|-------------|-----|
| Edge (mean realized) | > 0 bps | Log: `[Phase5] Quote outcome tracker stats` | Negative edge = guaranteed loss after fees |
| Fill rate | > 10 fills/hour | Log: `fills_processed` count | Too few fills = can't learn, kappa is stale |
| Adverse selection rate | < 40% | Log: `[AS OUTCOME]` count vs total fills | > 40% = getting run over by informed flow |
| Sharpe ratio | > 0 | Log: `LiveAnalytics` periodic summary | Negative Sharpe = losing money systematically |
| Kill switch triggers | 0 in 24h | Log: `KILL SWITCH` | Any trigger = config is too tight or market is hostile |
| Position bounds | Never hit max | Log: position tracking | Hitting max = sizing is wrong or inventory management is broken |

### Paper Validation Commands

```bash
# Run paper for 24 hours (86400 seconds)
cargo run --release --bin market_maker -- paper --duration 86400 \
  --asset <ASSET> [--dex <DEX>] --max-position <POS>

# After paper run, check the checkpoint for summary metrics:
cat data/checkpoints/paper/<ASSET>/prior.json | python3 -m json.tool | head -50
```

### What to Look For in Paper Logs

```
# Positive edge after warmup (first 5-10 minutes may be negative)
grep "Quote outcome tracker stats" paper.log | tail -5

# AS rate should settle below 40%
grep "AS OUTCOME" paper.log | wc -l  # adverse fills
grep "fills_processed" paper.log | wc -l  # total fills

# No kill switch triggers
grep "KILL SWITCH" paper.log  # should be empty

# Kappa should stabilize (not stuck at default)
grep "kappa_effective" paper.log | tail -10
```

**STOP HERE if any threshold is not met.** Diagnose with `/debug-pnl` workflow before proceeding.

---

## Phase 2: Code Parity Audit

This is the most critical step. The unified architecture means paper and live share the same `MarketMaker<S, Env>` handlers, but parity can still break at the binary setup level.

### Architecture Overview

Both paper and live use:
- Same `handle_user_fills()` at `handlers.rs:571`
- Same `FillProcessor::process()` at `fills/processor.rs:720`
- Same learning loops at `handlers.rs:700-805`
- Same `quote_engine` at `quote_engine.rs`

Parity risks exist in `src/bin/market_maker.rs` where paper (`run_paper_mode()` at line 2467) and live setup diverge on config, feature flags, and prior injection.

### Learning Loop Verification

There are 9 learning feedback loops that must all be active in live mode. See `references/learning-loop-parity.md` for the complete table. Run the combined verification:

```bash
# Quick parity check - all 9 must match
echo "1. Kappa from own fills:" && grep -c "estimator.on_own_fill" src/market_maker/orchestrator/handlers.rs
echo "2. AS markout queue:" && grep -c "pending_fill_outcomes.push_back" src/market_maker/orchestrator/handlers.rs
echo "3. Pre-fill classifier:" && grep -c "pre_fill_classifier.record_outcome" src/market_maker/orchestrator/handlers.rs
echo "4. AS prediction update:" && grep -c "update_as_prediction" src/market_maker/orchestrator/handlers.rs
echo "5. LiveAnalytics record_fill:" && grep -c "live_analytics.record_fill" src/market_maker/orchestrator/handlers.rs
echo "6. record_quote_cycle:" && grep -c "record_quote_cycle" src/market_maker/orchestrator/quote_engine.rs
echo "7. maybe_log_summary:" && grep -c "maybe_log_summary" src/market_maker/orchestrator/handlers.rs
echo "8. Quote outcome tracker:" && grep -c "quote_outcome_tracker" src/market_maker/orchestrator/quote_engine.rs
echo "9. RL baseline:" && grep -c "BaselineTracker" src/market_maker/learning/rl_agent.rs
```

**Every line must show count >= 1.** If any shows 0, that learning loop has been removed or broken.

### Known Past Regressions to Verify

These bugs have occurred before and cost real money. Explicitly verify each one has not regressed:

#### 1. Duplicate on_trade (handlers.rs)

**Bug**: `handlers.rs` had a duplicate `estimator.on_market_trade()` call that double-counted market trades for kappa estimation. The canonical call is in `messages/trades.rs`.

```bash
# Should return exactly 0 matches in handlers.rs for on_market_trade
# (the canonical call is in messages/trades.rs, NOT handlers.rs)
grep -n "on_market_trade" src/market_maker/orchestrator/handlers.rs
grep -n "on_market_trade" src/market_maker/messages/trades.rs  # should have 1 match
```

#### 2. WaitToLearn Deadlock (quote_engine.rs)

**Bug**: A "wait to learn" gate blocked quoting until the estimator warmed up, but the estimator can only warm up from fills, which require quoting. This creates a cold-start deadlock.

```bash
# Should NOT find any WaitToLearn or "wait_to_learn" blocking gate
grep -in "WaitToLearn\|wait_to_learn" src/market_maker/orchestrator/quote_engine.rs
# If found, verify it falls through (quotes anyway) rather than blocking
```

#### 3. Kappa Raw vs Effective

**Bug**: Code compared raw kappa (~6400-7700 for HIP-3) against thresholds meant for kappa_effective (~3250). Raw kappa from `estimator.kappa()` is the unsmoothed book-implied value; `kappa_orchestrator.kappa_effective()` is the EWMA-smoothed blended value.

```bash
# Check for any threshold comparisons against raw kappa
# The orchestrator's kappa_effective is at kappa_orchestrator.rs:268
grep -n "estimator.kappa()" src/market_maker/orchestrator/quote_engine.rs
# Any comparison like "if self.estimator.kappa() > THRESHOLD" is suspicious
# Should use kappa_effective from the orchestrator instead
```

#### 4. Drawdown Denominator Bug (risk/state.rs)

**Bug**: `drawdown()` previously divided by `peak_pnl` (tiny early in session) instead of `account_value`, causing 1000%+ phantom drawdown that triggered the kill switch.

```bash
# Verify drawdown divides by account_value, NOT peak_pnl
# The fixed version is at state.rs:261
grep -A2 "fn drawdown" src/market_maker/risk/state.rs
# Should see: (self.peak_pnl - self.daily_pnl) / self.account_value
```

#### 5. Cold-Start Staleness (signal_integration.rs)

**Bug**: Without an `observation_count > 0` guard, signals that were never warmed up (cold start) triggered permanent 2x staleness widening. The fix ensures staleness only penalizes signals that WERE warmed up and then went stale.

```bash
# Verify observation_count guard exists at signal_integration.rs:1006
grep -B2 -A2 "observation_counts" src/market_maker/strategy/signal_integration.rs | head -20
# Should see: && self.lag_analyzer.observation_counts() != (0, 0)
```

---

## Phase 3: Config Validation

### Auto-Derive Parameters

The system auto-derives trading parameters from capital via `auto_derive()` at `config/auto_derive.rs:56`. Verify the derivation is sane:

```bash
# Check auto_derive function signature and logic
grep -A5 "pub fn auto_derive" src/market_maker/config/auto_derive.rs
```

Key derived parameters:
- `max_position`: `min(capital/price, margin*leverage*0.5/price)` -- never exceeds what capital can support
- `target_liquidity`: profile-dependent fraction of max_position (20% Default, 30% HIP-3, 40% Aggressive)
- `risk_aversion`: 0.30 Default, 0.15 HIP-3, 0.10 Aggressive
- `max_bps_diff`: `(fee_bps * 2.0).clamp(3, 15)` -- cold-start, refined at runtime

### Kill Switch Thresholds

Located in `risk/kill_switch.rs`. The kill switch config has these critical parameters:

| Parameter | Default | Conservative | What It Does |
|-----------|---------|-------------|-------------|
| `max_daily_loss` | Position-dependent | $50 for small | Hard USD loss limit |
| `max_drawdown` | 0.05 (5%) | 0.02 (2%) | Peak-to-trough as fraction of account_value |
| `max_position_value` | Position-dependent | 2x target | USD value of position |
| `stale_data_threshold` | 15s | 10s | Kill if no market data for this long |
| `min_peak_for_drawdown` | $1.00 | $1.00 | Don't check drawdown until this much profit |

```bash
# Verify kill switch config defaults
grep -A20 "impl Default for KillSwitchConfig" src/market_maker/risk/kill_switch.rs
# Or check the from_position_size() factory:
grep -A20 "fn from_position_size" src/market_maker/risk/kill_switch.rs
```

### Binance Signal Toggles

For HIP-3 tokens (builder-deployed DEX assets) that have NO Binance feed, you MUST disable Binance signals. Leaving them enabled causes permanent 2x staleness widening.

```bash
# Verify disable_binance_signals is called for HIP-3 assets
grep -n "disable_binance_signals" src/bin/market_maker.rs
# Should see calls in both paper mode (~line 2636) and live mode (~line 2099)
```

The disable function sets `use_lead_lag = false` and `use_cross_venue = false` in the signal integrator (`signal_integration.rs:1040`).

### Config Checklist

Before starting the live binary, verify these config values:

- [ ] `risk_model_blend: 1.0` -- Full cutover to log-additive gamma (stochastic config default). Value of 0.0 uses old multiplicative model which can explode.
- [ ] `spread_profile` matches the asset type (Default for BTC/ETH, Hip3 for HIP-3 tokens, Aggressive only if you know what you're doing)
- [ ] `max_position` is set appropriately for the capital deployed (auto_derive handles this if using `--capital`)
- [ ] `initial_isolated_margin` is set for HIP-3 assets (default $1000)
- [ ] Kill switch thresholds are appropriate for the position size
- [ ] `--dex` flag is set for HIP-3 assets (e.g., `--dex hyna`)

---

## Phase 4: Dry Run Procedure

Before placing real orders, do a dry run to validate the full startup path without submitting orders.

### Step 1: Build Release Binary

```bash
cargo build --release
# Or for production with LTO (slower build, faster runtime):
cargo build --profile release-prod
```

### Step 2: Run Dry Mode

```bash
cargo run --release --bin market_maker -- \
  --asset <ASSET> \
  [--dex <DEX>] \
  --max-position <MAX_POS> \
  --dry-run \
  [--paper-checkpoint data/checkpoints/paper/<ASSET>]
```

The `--dry-run` flag (defined at `market_maker.rs:155`) validates everything but exits before the main loop:
- Configuration is parsed and validated
- Exchange connection is established
- Account state is queried (position, open orders, margin)
- Auto-derive computes parameters
- Kill switch checkpoint is loaded (if any)
- But NO orders are placed

### Step 3: Verify Dry Run Output

The dry run should log:
```
=== DRY RUN MODE ===
Configuration validated successfully
Exchange connection established
Account state verified: position=X, open_orders=Y
Exiting dry-run mode (no orders placed)
```

**Red flags in dry run**:
- "Asset not found" -- wrong asset name or missing `--dex` flag
- "Capital too small" -- auto_derive says position is not viable
- "Failed to get metadata" -- network issue or wrong base URL
- "Invalid private key" -- key format error
- Kill switch already armed from a previous session

---

## Phase 5: First 30 Minutes Monitoring

This is the most critical monitoring window. Have the terminal visible and ready to Ctrl+C.

### Minute-by-Minute Checklist

#### 0-1 Minutes: Orders Appearing?

```bash
# Watch for order placement logs
tail -f market_maker.log | grep -E "order_placement|Calculated ladder|KILL|ERROR"
```

**Verify**:
- [ ] "Calculated ladder quotes" appears within 10 seconds
- [ ] Orders show reasonable prices (within 50 bps of mid)
- [ ] API headroom is stable (> 20%)
- [ ] No "NoQuote" decisions (check for quote gate reasons)

**Red flags**: No order logs after 30 seconds, API headroom < 10%, "OI cap" messages, "config validation failed"

#### 1-5 Minutes: First Fills?

```bash
# Watch for fills
tail -f market_maker.log | grep -E "fills_processed|position|UserFill|KILL"
```

**Verify**:
- [ ] First fill appears within 5 minutes (for liquid assets)
- [ ] Position stays within max_position bounds
- [ ] Spread is within 2x of what paper trader showed
- [ ] No duplicate fill warnings
- [ ] No "unmatched fill" warnings (> 1 is concerning)

**Red flags**: Position jumps to max_position immediately (inventory forcing), spread > 100 bps for a liquid asset, fill dedup errors

#### 5-15 Minutes: Learning Loops Updating?

```bash
# Check kappa is adapting (not stuck at default)
tail -f market_maker.log | grep -E "kappa_effective|kappa_raw|Periodic component"

# Check AS predictions are flowing
tail -f market_maker.log | grep "AS OUTCOME"

# Check quote outcome tracker is accumulating
tail -f market_maker.log | grep "Quote outcome tracker stats"
```

**Verify**:
- [ ] Kappa is changing from its initial value (indicates on_own_fill is working)
- [ ] AS outcomes are being recorded (indicates markout queue is working)
- [ ] Quote outcome tracker shows n_total > 0 (indicates registration is working)
- [ ] No persistent "model degraded" or "model health" warnings

**Red flags**: Kappa stuck at default (6000+) after 10 fills, zero AS outcomes after 10 fills, quote outcome tracker showing 0 total

#### 15-30 Minutes: PnL Trending?

```bash
# Check PnL and edge
tail -f market_maker.log | grep -E "LiveAnalytics|edge_bps|Sharpe|summary"

# Check for any risk escalation
tail -f market_maker.log | grep -E "RiskSeverity|circuit_breaker|kill_switch"
```

**Verify**:
- [ ] PnL is trending positive or at least not deeply negative
- [ ] Mean realized edge > -2 bps (slight negative is ok during warmup)
- [ ] No sustained NoQuote periods > 2 minutes
- [ ] Risk severity stays at Normal or Elevated (not Critical)
- [ ] API headroom stabilizes > 15%

**Red flags**: PnL steadily declining, edge < -5 bps after 30 minutes, repeated kill switch near-misses, API headroom dropping

---

## Phase 6: Red Flags -- Immediate Manual Intervention

If any of these conditions occur, **immediately Ctrl+C** the market maker and investigate:

| Red Flag | Threshold | Likely Cause | Immediate Action |
|----------|-----------|-------------|-----------------|
| Position > 2x max_inventory | `position.abs() > 2 * max_position` | Fill dedup failure, position tracking bug | Kill, cancel all orders, check exchange position |
| NoQuote > 5 minutes | No "Calculated ladder" for 5+ min | Quote gate stuck, WaitToLearn deadlock, estimator crash | Kill, check logs for panic/error |
| API headroom < 5% | `headroom < 0.05` in logs | Rate limiting, too aggressive reconciliation | Kill, wait for headroom recovery, increase max_bps_diff |
| Spread > 100 bps for > 2 min | Sustained wide spread on liquid asset | Staleness cascade, sigma spike, risk escalation | Kill, check signal staleness and regime detection |
| Kill switch triggered | `KILL SWITCH TRIGGERED` in logs | Various -- see KillReason in log | Already killed, save checkpoint, analyze |
| Drawdown > 2% | `drawdown > 0.02` | Getting run over, AS too high, market hostile | Kill, close position if large, analyze fill quality |
| Negative edge < -5 bps sustained | After 15+ min of trading | Model miscalibration, stale kappa, wrong fees | Kill, compare with paper metrics |
| Exchange errors | Repeated 4xx/5xx from exchange | API changes, rate limits, maintenance | Kill, check exchange status page |

### Emergency Kill Procedure

```bash
# 1. Ctrl+C the market maker (graceful shutdown saves checkpoint)
# 2. If Ctrl+C doesn't work within 5 seconds, Ctrl+C again (force)
# 3. Verify all orders are cancelled:
#    The kill switch should have cancelled them, but verify on exchange UI

# 4. Check final position on exchange
#    If position is small (< 0.5x max_position), consider leaving it
#    If position is large, close manually via exchange UI

# 5. Save the checkpoint (should be auto-saved on graceful shutdown)
ls -la data/checkpoints/<ASSET>/
```

---

## Phase 7: Rollback Procedure

If something goes wrong and you need to revert to paper-only:

### Step 1: Stop the Live Trader

Ctrl+C for graceful shutdown. The shutdown sequence:
1. Cancels all open orders
2. Flushes analytics (`live_analytics.flush()` at `analytics/live.rs:207`)
3. Saves checkpoint to disk
4. Logs final PnL summary

### Step 2: Assess Position

```bash
# Check checkpoint for final position
cat data/checkpoints/<ASSET>/latest/checkpoint.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'Position: {d.get(\"position\", \"unknown\")}')
print(f'PnL: {d.get(\"pnl\", \"unknown\")}')
"
```

Decision matrix:
- **Position < 0.1x max_position**: Leave it, no action needed
- **Position 0.1x-0.5x max_position**: Consider closing manually if PnL is negative
- **Position > 0.5x max_position**: Close manually via exchange UI to avoid carrying overnight risk

### Step 3: Analyze What Went Wrong

```bash
# Extract key metrics from logs
grep "LiveAnalytics" market_maker.log | tail -5     # Sharpe/edge summary
grep "AS OUTCOME" market_maker.log | wc -l           # Total adverse fills
grep "fills_processed" market_maker.log | wc -l       # Total fills
grep "KILL\|kill_switch" market_maker.log             # Kill switch activity
grep "NoQuote\|no_quote" market_maker.log | wc -l     # Quote gate blocks
grep "headroom" market_maker.log | tail -10           # API headroom trend
```

### Step 4: Fix and Re-validate

1. Fix the identified issue
2. Run `cargo test && cargo clippy -- -D warnings`
3. Run paper trading again for at least 4 hours
4. Verify the fix in paper (the specific metric that failed)
5. Start from Phase 2 of this workflow again

### Step 5: Save Lessons Learned

Update the following:
- Serena memory: `.serena/memories/session_<date>_live_<issue>.md`
- MEMORY.md: Add to Known Issues or Live MM sections
- This skill's "Known Past Regressions" if a new pattern was discovered

---

## Quick Reference: Go-Live Command

```bash
# Standard go-live for a validator perp (BTC, ETH, etc.)
cargo run --release --bin market_maker -- \
  --asset BTC \
  --max-position 0.01 \
  --paper-checkpoint data/checkpoints/paper/BTC \
  2>&1 | tee market_maker.log

# Go-live for a HIP-3 DEX asset (HYPE, etc.)
cargo run --release --bin market_maker -- \
  --asset "hyna:HYPE" \
  --dex hyna \
  --max-position 10.0 \
  --initial-isolated-margin 1000 \
  --spread-profile hip3 \
  --paper-checkpoint data/checkpoints/paper/hyna:HYPE \
  2>&1 | tee market_maker.log

# Dry run first (validates everything, places no orders)
# Add --dry-run to either of the above commands
```

---

## Appendix: Config Comparison -- Paper vs Live

| Setting | Paper Mode | Live Mode | Risk if Wrong |
|---------|-----------|-----------|--------------|
| Environment | `PaperEnvironment` | `LiveEnvironment` | N/A (binary level) |
| Binance signals | Disabled (line 2636) | Auto-detected (line 2099) | 2x staleness if enabled without feed |
| Checkpoint dir | `data/checkpoints/paper/<ASSET>` | `data/checkpoints/<ASSET>` | Wrong prior loaded |
| Prior injection | Cold start | Loads paper prior | Cold start = slow warmup |
| Account balance | Seeded $1000 (line 2642) | Real exchange balance | Paper: orders fail min notional |
| Position | Starts at 0 | Loaded from exchange | Live: stale position = wrong quoting |
| StochasticConfig | `default()` | From config file | Paper uses defaults, live may differ |
| Kill switch | Default thresholds | Position-sized thresholds | Too tight = unnecessary kills |
