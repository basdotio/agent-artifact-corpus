---
name: python-trading-bot
description: Generate, refactor, and maintain Python live trading bots for NQ futures prop firm trading (Apex Trader Funding). Supports Databento API for market data, TradersPost for execution, eval/PA modes, custom strategies, and comprehensive production features. Triggers: "live trading bot", "Python bot", "NQ bot", "futures bot", "create bot", "refactor bot", "/bot:new", "/bot:refactor", "/bot:custom".
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(pip:*, python3:*)
---

# Python Trading Bot Skill

Generate, refactor, and maintain production-ready Python trading bots for NQ futures prop firm trading with:
- **Databento API** for real-time and historical market data
- **TradersPost webhooks** for order execution (Apex Trader Funding compatible)
- **Eval and PA modes** with trailing drawdown, profit targets, dynamic sizing
- **5 backtested signals** + support for custom strategies
- **Production features** (state persistence, news filtering, alerting, comprehensive testing)

## Commands

### Bot Generation
| Command | Description |
|---------|-------------|
| `/bot:new` | Start interactive bot builder (with eval/PA mode selection) |
| `/bot:new <signal>` | Start with signal pre-selected |
| `/bot:custom` | Build bot with custom strategy/indicators |
| `/bot:keltner` | Generate Keltner Channel bot (PF 10.04) |
| `/bot:ema` | Generate EMA Cross bot (PF 6.23) |
| `/bot:vwap` | Generate Rolling VWAP bot (PF 5.20) |
| `/bot:supertrend` | Generate SuperTrend bot (PF 4.41) |
| `/bot:alligator` | Generate Alligator bot (PF 4.16) |
| `/bot:list` | Show signals with backtest metrics |

### Bot Refactoring
| Command | Description |
|---------|-------------|
| `/bot:refactor <bot_name>` | Start interactive refactoring session |
| `/bot:add-feature <bot_name> <feature>` | Add feature (news filter, indicator, etc.) |
| `/bot:remove-feature <bot_name> <feature>` | Remove feature cleanly |
| `/bot:migrate-pa <bot_name>` | Convert eval bot to PA mode |
| `/bot:analyze <bot_name>` | Analyze code quality and suggest improvements |

## Top 5 Entry Signals

| Signal | Profit Factor | Win Rate | Key Parameters |
|--------|--------------|----------|----------------|
| **keltner** | 10.04 | 87.8% | EMA=20, ATR_MULT=2.75 |
| **ema_cross** | 6.23 | 82.7% | Fast=3, Slow=8, Sep=0.35 |
| **vwap** | 5.20 | 85.3% | Window=720, Mult=1.0 |
| **supertrend** | 4.41 | 82.5% | Period=10, Mult=3.0 |
| **alligator** | 4.16 | 83.5% | Jaw=13, Teeth=8, Lips=5 |

*Metrics from 219-day NQ futures backtest (May 2025 - Jan 2026) with ADX di_rising, threshold 35.*

---

## When to Use This Skill

**Use this skill when:**
- Creating a new live trading bot for NQ futures
- Refactoring or modifying existing trading bots
- Converting eval bots to PA mode (or vice versa)
- Adding features to bots (news filter, alerts, new indicators)
- Building custom strategies beyond the 5 pre-built signals
- Setting up Apex Trader Funding eval or PA accounts
- Implementing prop firm risk management (trailing DD, dynamic sizing)
- Testing strategies with CSV backtest before going live

**Do NOT use for:**
- Offline backtesting only (use Python/backtest.py instead)
- Creating platform indicators (use indicator-generator skill for TradingView/NinjaTrader/Tradovate)
- Multi-account management (run separate bot instances)
- Non-futures markets (skill optimized for NQ futures)

---

## Generated Bot Structure

Each generated bot includes these files:

```
Python/bots/<signal>/
├── bot_<signal>.py              # Main entry point (asyncio)
├── config.py                    # Configuration from .env
├── databento_client.py          # Market data (Databento API)
├── traderspost_client.py        # Order execution (TradersPost webhook)
├── risk_manager.py              # Apex account tracking (eval/PA modes)
├── indicators.py                # Self-contained indicator calculations
├── news_calendar.py             # Economic calendar filtering (optional)
├── alerting.py                  # Email/SMS alerts (optional)
├── bot_state.db                 # SQLite persistence (created at runtime)
├── requirements.txt             # Python dependencies
├── .env.example                 # Credential template
├── .gitignore                   # Exclude .env, logs, *.db
└── README.md                    # Bot documentation
```

---

## Bot Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DATABENTO API                             │
│  https://databento.com (real-time & historical 2-min bars)  │
│  + CSV files for backtesting                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      PYTHON BOT                              │
│  • Indicator calculation (EMA, ATR, ADX, signal-specific)   │
│  • Signal detection (edge-triggered crossovers)              │
│  • Apex account tracking (eval/PA modes, trailing DD)       │
│  • Position management (SL/TP/trailing stops)               │
│  • Re-entry logic (3 bars wait, ADX > 40)                   │
│  • News calendar filtering (blackout periods)               │
│  • State persistence (SQLite - survive restarts)            │
│  • Alerting (email/SMS on critical events)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   TRADERSPOST WEBHOOK                        │
│  POST https://webhooks.traderspost.io/trading/webhook/...   │
│  {ticker, action, quantity, stopLoss, takeProfit}           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│          BROKER (Tradovate / Apex Trader Funding)           │
│  Order execution, position management, OCO brackets          │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Features

| Feature | Implementation |
|---------|----------------|
| **Market Data** | Databento API (real-time + historical) + CSV files |
| **Account Modes** | Eval (profit target, trailing DD) or PA (risk %, static DD) |
| **Position Sizing** | Fixed contracts (eval) or risk-based % (PA mode) |
| **Indicator calculations** | Self-contained (EMA, ATR, ADX, VWAP, signal-specific) |
| **Signal detection** | Edge-triggered crossovers (5 pre-built + custom) |
| **Position management** | Entry price, SL, TP, HWM/LWM, trailing stops |
| **Re-entry logic** | 3 bars wait, ADX > 40, max 10 per direction |
| **News calendar** | Economic event blackouts (FOMC, NFP, CPI) |
| **Alerting** | Email + SMS on daily loss limit, DD breach, connection loss |
| **State persistence** | SQLite database (survive mid-day restarts) |
| **Session filtering** | Configurable allowed hours (ET timezone) |
| **Volume filter** | Volume > EMA(volume, 20) |
| **Graceful shutdown** | SIGINT/SIGTERM handlers, exit positions on shutdown |
| **Logging** | File + console with timestamps |
| **Testing** | CSV backtest mode, unit tests, integration tests |

---

## Quick Start

### 1. Interactive Mode

```
User: Create a live trading bot
Assistant: [Runs /bot:new workflow]
  - Step 1: Select signal (keltner, ema_cross, vwap, supertrend, alligator)
  - Step 2: Configure signal parameters
  - Step 3: Set risk parameters (contracts, daily max loss)
  - Step 4: Configure exits (SL, TP, trailing)
  - Step 5: API credentials guidance
  - Step 6: Generate bot files
```

### 2. Direct Signal

```
User: /bot:keltner
Assistant: [Generates Keltner bot with optimal settings]
```

### 3. Quick Mode

```
User: /bot:new keltner --quick
Assistant: [Uses all defaults, generates immediately]
```

---

## ADX Filter Modes

All 5 modes from backtest.py supported:

| Mode | Logic | Recommended |
|------|-------|-------------|
| `traditional` | ADX > threshold | |
| `di_aligned` | + DIs aligned with direction | |
| `di_rising` | + Dominant DI rising | ✅ |
| `adx_rising` | + ADX itself rising | |
| `combined` | All conditions | |

---

## Exit Priority Order

1. **Trailing Stop** (if active AND hit)
2. **Stop Loss** (hard protective stop)
3. **Take Profit** (profit target)

---

## Skill References

### Core Documentation
| Resource | Description |
|----------|-------------|
| [Interactive Workflow](reference/workflow-interactive.md) | Interactive bot generation workflow (includes account_mode) |
| [Refactoring Guide](reference/workflow-refactor.md) | Bot refactoring and modification workflows |
| [Configuration Index](reference/config-index.md) | Configuration index with links to topics |
| [Signals Overview](reference/signals-overview.md) | Signal overview and selection guide |
| [Apex Rules](reference/apex-rules.md) | Comprehensive Apex Trader Funding rules |
| [Apex Compliance](reference/apex-compliance.md) | Apex compliance guidelines for automated trading |

### Configuration Topics
| Resource | Description |
|----------|-------------|
| [Apex Accounts](reference/apex-accounts.md) | Account modes, presets, position sizing |
| [Signal Parameters](reference/signal-params.md) | All 5 signal parameters |
| [ADX Modes](reference/adx-modes.md) | ADX filter modes with examples |
| [Exits & Re-entry](reference/exits-reentry.md) | Stop loss, take profit, trailing, re-entry |
| [Risk & Filters](reference/risk-filters.md) | Risk mgmt, filters, alerts, persistence |

### Guides
| Resource | Description |
|----------|-------------|
| [Eval vs PA Comparison](reference/eval-vs-pa.md) | Eval vs PA mode comparison |
| [Eval Mode Guide](reference/apex-eval-mode.md) | Eval account detailed guide |
| [PA Mode Guide](reference/apex-pa-mode.md) | PA account detailed guide |
| [Data Provider Guide](reference/data-provider-guide.md) | Data provider overview |
| [Custom Provider Tutorial](reference/data-provider-custom.md) | Custom provider implementation |
| [Provider Reference](reference/data-provider-reference.md) | Bar format, testing, best practices |
| [Architecture](reference/architecture.md) | Architecture overview |
| [Architecture Components](reference/architecture-components.md) | Component details |
| [Data Flow](reference/architecture-dataflow.md) | Bar processing, entry/exit flows |
| [Deployment Guide](reference/deployment.md) | Deployment overview |
| [VPS Setup](reference/deployment-vps.md) | Server setup and installation |
| [Systemd Service](reference/deployment-systemd.md) | Service configuration |
| [Production Operations](reference/deployment-production.md) | Monitoring, security, backup |
| [Economic Calendar](reference/economic-calendar.md) | News calendar integration |
| [Testing Guide](reference/testing.md) | Unit, integration, CSV backtest testing |
| [Setup Guide](reference/setup.md) | Bot setup and deployment |

### Signal Details
| Resource | Description |
|----------|-------------|
| [Top 5 Signals](reference/signals-top5.md) | Detailed top 5 with all parameters |
| [Keltner Channel](reference/signal-keltner.md) | Keltner Channel details |
| [EMA Crossover](reference/signal-ema.md) | EMA Crossover details |
| [Rolling VWAP](reference/signal-vwap.md) | Rolling VWAP details |
| [SuperTrend](reference/signal-supertrend.md) | SuperTrend details |
| [Williams Alligator](reference/signal-alligator.md) | Williams Alligator details |

### Templates
| Resource | Description |
|----------|-------------|
| [Base Bot](templates/base_bot.py.md) | Main bot template (with persistence, news, alerts) |
| [Config](templates/config.py.md) | Config file template |
| [Indicators](templates/indicators.py.md) | Indicators class overview |
| [Core Indicators](templates/indicators_core.py.md) | EMA, SMA, SMMA, ATR, ADX |
| [Signal Indicators](templates/indicators_signal.py.md) | VWAP, Keltner, SuperTrend, Alligator |
| [Apex Integration](templates/apex_integration.py.md) | Apex account integration template |
| [Risk Manager](templates/risk_manager.py.md) | Risk manager with eval/PA support |
| [Persistence](templates/persistence.py.md) | SQLite state persistence |
| [News Filter](templates/news_filter.py.md) | Economic calendar filtering |
| [Alerting](templates/alerting.py.md) | Email/SMS alerting system |
| [Data Provider](templates/data_provider_base.py.md) | Data provider adapter interface |
| [Test Suite](templates/test_suite.py.md) | Test suite template |
| [TradersPost Client](templates/traderspost_client.py.md) | TradersPost webhook client |
| [Tradovate Client](templates/tradovate_client.py.md) | Tradovate WebSocket client |

### Workflows
| Resource | Description |
|----------|-------------|
| [Add Feature](reference/workflow-add-feature.md) | Add feature to existing bot |
| [Remove Feature](reference/workflow-remove-feature.md) | Remove feature from bot |
| [Change Indicator](reference/workflow-change-indicator.md) | Swap or modify indicators |
| [Migrate to PA](reference/workflow-migrate-eval-pa.md) | Convert eval bot to PA mode |
| [Custom Strategy](reference/workflow-custom-strategy.md) | Build custom strategy bot |

### Examples
| Resource | Description |
|----------|-------------|
| [Keltner Bot Example](examples/keltner_bot.py) | Full working Keltner Channel bot example |
| [Custom Data Provider](examples/custom_data_provider.py) | Example custom data provider adapter |
| [Alert Config](examples/alert_config.py) | Alerting configuration example |
| [Indicator Tests](examples/test_indicators.py) | Unit test examples |
| [Environment Template](examples/config_example.env) | .env file template with all required credentials |

---

## Related Files

| File | Purpose |
|------|---------|
| `Python/backtest.py` | Reference implementation (indicator calculations, signal logic) |
| `Python/docs/TRADOVATE_API_GUIDE.md` | TradersPost payload format, Tradovate WebSocket |
| `Python/STRATEGY.md` | Strategy specification |
