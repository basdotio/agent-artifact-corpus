---
name: setup
description: Get a new user from zero to ready-to-trade on Turbine. Environment, wallet, credentials, funding.
---

# Turbine Setup

You are helping a user set up their environment to trade on Turbine's prediction markets. This skill handles everything from cloning the repo to having a funded wallet — after this, the user is ready to create their first bot.

### Key URLs

Reference these throughout setup — both for your own lookups and to share with users:

- **Platform:** https://beta.turbinefi.com
- **Leaderboard:** https://beta.turbinefi.com/leaderboard
- **Docs (overview):** https://beta.turbinefi.com/docs
- **Fees & Gas:** https://beta.turbinefi.com/docs/fees-and-gas
- **Architecture:** https://beta.turbinefi.com/docs/architecture
- **Build a Trading Bot:** https://beta.turbinefi.com/docs/api/build-a-trading-bot
- **API Reference:** https://beta.turbinefi.com/docs/api
- **Authentication:** https://beta.turbinefi.com/docs/api/authentication
- **API Host:** https://api.turbinefi.com

If a user asks questions you can't answer from CLAUDE.md or the repo, fetch the relevant docs page above.

**What this skill does NOT do:**
- Generate any bot code (that's `/create-bot`)
- Explain trading algorithms or strategy design
- Deploy anything to the cloud (that's `/railway-deploy`)

---

## Step 0: Understand Who You're Helping

This may be the user's very first interaction with Claude in this repo. Before touching any code, figure out who they are. This shapes everything — how much you explain, what you skip, and what tone you use.

Turbine's users fall into a 2x2 matrix (see CLAUDE.md for full details):

|  | Low Technical | High Technical |
|--|---------------|----------------|
| **Knows PMs** | Understands trading, needs code help | Power user, can self-serve |
| **New to PMs** | Needs help with everything | Can code, needs PM concepts first |

Use `AskUserQuestion` with **two questions**:

1. **"How comfortable are you with Python and the command line?"**
   - Options: "I'm new to Python" / "I've written some Python" / "I'm a developer"

2. **"How familiar are you with prediction markets?"**
   - Options: "I'm not sure how they work" / "I understand the basics" / "I've traded them before"

**Adapt your behavior based on the answers:**

- **Low tech + low PM:** Be thorough on everything. Explain what a virtual environment is, what a private key is, what USDC is. Don't assume any prior knowledge. This is the largest potential user group.
- **Low tech + high PM:** They understand the trading side — don't over-explain markets. Focus your patience on the technical steps (Python, wallet, .env).
- **High tech + low PM:** The code setup will be fast — they might not even need your help. But pause and make sure they understand what they're actually trading before moving on. Reference `docs/prediction-markets.md` or explain the core concepts from CLAUDE.md.
- **High tech + high PM:** Be concise. Skip explanations, just run the commands and move fast. They'll ask if they need something.

Carry this context through every subsequent step. A beginner needs "here's what a virtual environment is and why we use one." An expert needs "setting up venv" and nothing more.

### Save the user context

After the questions above, also ask:

3. **"What brings you to Turbine?"**
   - Options: "I'm in a hackathon right now" / "I want to compete in the weekly competition" / "Just exploring / learning" / "Building for a specific project"

**Create `user-context.md` in the repo root** using the Write tool. This file persists across sessions and skills so Claude doesn't have to re-ask these questions every time. It's gitignored (personal to this user).

```markdown
# User Context

## Profile
- **Technical level:** [beginner / comfortable / expert]
- **PM familiarity:** [none / conceptual / experienced]
- **Goal:** [hackathon / weekly competition / exploring / specific project]

## Setup Status
- **Date:** [today's date]
- **Chain:** [Base Sepolia / Polygon / Avalanche]
- **Wallet address:** [filled in after Step 3]

## Notes
[Any other context gathered during conversation — e.g., "interested in momentum strategies", "coming from Polymarket", "has 3 days for hackathon"]
```

Add `user-context.md` to `.gitignore` if it's not already there — this file is personal and should never be committed.

**Why this file matters:** Other skills (like `/create-bot`) will read `user-context.md` instead of re-asking the same questions. If a user runs `/create-bot` without having run `/setup`, Claude can still ask — but if the file exists, Claude already knows who it's helping.

---

## Step 0.5: Set the Stage

After profiling, **don't immediately jump into running commands.** Have a brief conversational moment first. The user just answered 3 questions — acknowledge them and set expectations for what's coming.

**For all users**, give a quick roadmap:

> "Great — here's the plan. There are a few things we need to get set up: a Python environment, a wallet (for signing trades), and a connection to Turbine's API. I'll check what's already done and handle the rest. Should take just a few minutes."

**Adapt the tone based on their profile:**

- **Low tech + low PM:** Add warmth and reassurance: "Don't worry if any of this sounds unfamiliar — I'll explain each step as we go. You don't need to know crypto or Python internals to get this working."
- **Low tech + high PM:** "You know the trading side — I'll handle the technical plumbing and explain what I'm doing along the way."
- **High tech + low PM:** "The setup itself is straightforward. Once we're done, I'll make sure you understand what you're actually trading before we build anything."
- **High tech + high PM:** Keep it short: "Let me check what's already set up." (They don't need a roadmap.)

**For users new to PMs**, this is also a good moment for a one-line hook about what they're building toward:

> "By the end of this, you'll have a bot that automatically trades Bitcoin prediction markets — betting on whether BTC goes up or down every 15 minutes."

Then move to the environment check.

---

## Step 1: Assess Current State

Check where the user already is. Run this as a **single command** (not separate calls — this avoids noisy parallel failures):

```bash
echo "=== Environment Check ===" && python3 --version 2>&1 && echo "VENV: ${VIRTUAL_ENV:-not_set}" && (python3 -c "import turbine_client; print('SDK: OK')" 2>/dev/null || echo "SDK: NOT_INSTALLED") && (test -f .env && grep -q "TURBINE_PRIVATE_KEY=0x" .env && echo "PRIVATE_KEY: SET" || echo "PRIVATE_KEY: NOT_SET") && (test -f .env && grep -q "TURBINE_API_KEY_ID=." .env && echo "API_CREDS: SET" || echo "API_CREDS: NOT_SET")
```

Based on results, skip any steps that are already complete. Summarize for the user in plain language — don't show them the raw output:

> "Here's where you stand: Python is ready, but you still need [X, Y, Z]. Let me take care of that."

If **everything** is already set up, say so and suggest `/create-bot`:

> "You're fully set up — Python environment, SDK, wallet credentials, everything looks good. Ready to build a bot? Run `/create-bot` to get started."

---

## Step 2: Python Environment

**Skip if:** Python 3.9+ is available AND a venv is active AND `turbine_client` imports successfully.

### If no virtual environment:

```bash
python3 -m venv .venv && source .venv/bin/activate
```

Explain briefly: *"A virtual environment keeps Turbine's dependencies separate from your system Python. This prevents version conflicts."*

> **For non-technical users:** This step can be confusing. Explain clearly:
> - "Think of a virtual environment like a separate workspace. It keeps this project's tools from interfering with anything else on your computer."
> - "The `source .venv/bin/activate` command activates this workspace. You'll need to run it every time you open a new terminal window before running your bot. If you see `(.venv)` at the start of your terminal prompt, you're in the right workspace."
> - Run the commands for them — don't ask them to type them.

### If SDK not installed:

```bash
pip install -e .
```

This installs the Turbine SDK and all its dependencies from the repo's `pyproject.toml`. The install may take 30-60 seconds.

> **For non-technical users:** If they see a wall of text scrolling by during install, reassure them: "That's normal — it's downloading and installing the libraries the bot needs. Just wait for it to finish."

### Verify:

```bash
python3 -c "from turbine_client import TurbineClient; print('Turbine SDK ready')"
```

If this fails, troubleshoot:
- Wrong Python version? Need 3.9+
- Not in the repo root? `cd` to where `pyproject.toml` lives
- pip install failed? Check error output, likely a missing system dependency

---

## Step 3: Wallet & Private Key

**Skip if:** `.env` exists and contains `TURBINE_PRIVATE_KEY=0x...` (non-empty).

The user needs an Ethereum-compatible private key. This is what the bot uses to sign transactions — it never leaves their machine.

> **For users new to prediction markets / crypto:** This step is often the most confusing part of setup. They may not know what a wallet, private key, or Ethereum even is. Explain before asking:
> - "To trade on Turbine, your bot needs a **wallet** — think of it like a bank account number. It has two parts: a **public address** (like an account number — safe to share) and a **private key** (like a password — never share this with anyone)."
> - "Your bot uses the private key to sign its trades. This happens entirely on your computer — the key is never sent to Turbine or anywhere else."
> - "We'll generate one for you right now in Python — it takes one second. You don't need to download anything or create any accounts."
>
> For non-PM users, **strongly recommend Option A** (generate in Python). MetaMask adds steps that aren't necessary and will feel like a detour into crypto-land.

### Ask first:

Use `AskUserQuestion`:
- **"Do you already have an Ethereum wallet (e.g., MetaMask)?"**
- Options: "Yes, I have a private key ready" / "No, I need to create one"

### If they have a key:

Ask them to paste it. **Reassure them:**
> "Your private key stays local in the `.env` file — it's gitignored, so it won't be committed to version control. It's used to sign transactions (free, off-chain) and is never sent to any server."

### If they need to create one:

> **For non-PM users:** Skip the MetaMask option and go straight to Python generation. Present it as the default: "Let me generate a wallet for you." Don't make them choose between two options they don't have context to evaluate.

**Option A — Generate in Python (fastest, recommended for new users):**
```bash
python3 -c "from eth_account import Account; a = Account.create(); print(f'Address: {a.address}'); print(f'Private Key: {a.key.hex()}')"
```

Tell them to **save the address** (they'll need it for funding) and that you'll put the private key in `.env` for them.

**Option B — MetaMask (only offer if they ask, or for users who already know crypto):**
1. Install MetaMask browser extension from metamask.io
2. Create a new wallet (save the seed phrase somewhere safe)
3. Export private key: Click account icon → Settings → Security & Privacy → Export Private Key
4. Copy the key

### Create the .env file:

Once you have the private key, **create the file directly using the Write tool**. Don't tell the user to do it — do it for them:

```
TURBINE_PRIVATE_KEY=0x<their_key>
TURBINE_API_KEY_ID=
TURBINE_API_PRIVATE_KEY=
CHAIN_ID=137
TURBINE_HOST=https://api.turbinefi.com
```

**Explain the fields briefly:**
- `TURBINE_PRIVATE_KEY` — Their wallet's signing key. Never leaves this machine.
- `TURBINE_API_KEY_ID` / `TURBINE_API_PRIVATE_KEY` — Left blank intentionally. The bot auto-registers API credentials on first run and saves them back to this file.
- `CHAIN_ID=137` — Polygon mainnet. This is where Turbine's active markets are.
- `TURBINE_HOST` — Turbine's API endpoint. All SDK operations (approvals, claims, balance checks) route through this — no RPC URL or web3 needed.

---

## Step 4: Funding

**Skip if:** User says they already have USDC on their target chain.

The bot needs USDC (a stablecoin pegged to $1) on the Polygon network. No other tokens are needed — Turbine is fully gasless.

**Turbine currently runs on Polygon mainnet.** The testnet (Base Sepolia) is not operational. This means users trade with real USDC — there is no free/fake-money option right now.

> **For users new to prediction markets / crypto:** The concepts of "USDC" and "funding a wallet" are foreign. Explain clearly:
> - "Your bot trades using **USDC**, which is a digital dollar — 1 USDC = $1 USD. It's the only currency you need."
> - "You'll need at least **$10 of USDC** on the Polygon network to start trading. The bot's default bet size is $0.10 per trade, so $10 goes a long way."
> - "**No other cryptocurrency is needed** — no ETH, no MATIC. Turbine pays all the network fees for you."

### Getting USDC on Polygon

The `.env` is already configured for Polygon (`CHAIN_ID=137`). The user needs USDC in their wallet.

**If they already have crypto:**
> "Send USDC to your wallet address on the Polygon network. If you have USDC on another chain, you can bridge it using a service like [Jumper](https://jumper.exchange)."

**If they're new to crypto:**
> "You'll need to buy USDC and send it to your wallet. The easiest path:"
> 1. Create an account on an exchange like Coinbase
> 2. Buy USDC (at least $10)
> 3. Withdraw the USDC to your wallet address — make sure to select **Polygon** as the network
> 4. Your wallet address is: `0x...` (show from the verification step or .env)

> **For hackathon users:** If the hackathon organizer (Turbine team) is providing USDC, tell the user to share their wallet address with the organizer. This is the fastest path — avoids the exchange signup entirely.

**USDC contract on Polygon:** `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`

**Important:** Be upfront about the fact that this is real money. Don't sugarcoat it:
> "This is real USDC — real money. The bot's default sizes are very small ($0.10 per trade, $1 maximum at risk), so you won't lose much while learning, but it's important to understand that real dollars are involved."

Remind them: **No MATIC or other gas tokens needed.** Turbine's relayer pays all gas fees. They only need USDC.

---

## Step 5: Verify Everything

Run a final check to make sure the full setup works:

```bash
# Activate venv if needed
source .venv/bin/activate 2>/dev/null

# Verify SDK imports
python3 -c "
from turbine_client import TurbineClient
from dotenv import load_dotenv
import os

load_dotenv()

pk = os.environ.get('TURBINE_PRIVATE_KEY', '')
chain = os.environ.get('CHAIN_ID', '84532')
host = os.environ.get('TURBINE_HOST', 'https://api.turbinefi.com')

if not pk or pk == '0x':
    print('FAIL: No private key in .env')
else:
    client = TurbineClient(host=host, chain_id=int(chain), private_key=pk)
    print(f'Wallet address: {client.address}')
    print(f'Chain: {chain}')
    print(f'Host: {host}')

    # Try fetching current market to verify API connectivity
    try:
        qm = client.get_quick_market('BTC')
        strike = qm.start_price / 1e6
        print(f'Current BTC market: strike \${strike:,.2f}')
        print('API connection: OK')
    except Exception as e:
        print(f'API connection: FAILED ({e})')

print()
print('Setup verification complete.')
"
```

Report results to the user clearly:
- Wallet address (so they know where to send USDC)
- Chain they're configured for
- Whether the API is reachable
- Whether there's an active BTC market (confirms everything works end-to-end)

> **For non-technical users:** Don't just dump the output. Interpret it for them in plain language:
> - "Your wallet address is `0x...` — this is like your account number on Turbine."
> - "You're connected to Base Sepolia (the testnet), so no real money is involved."
> - "I can see there's an active BTC market right now with a strike price of $X — that means your bot will be betting on whether Bitcoin goes above or below that price."
> - "Everything is working. You're ready to create your first bot."

> **For users new to PMs:** This is a good moment to connect the dots. They've been doing technical setup and may have lost the thread of *what* they're building. Briefly remind them: "Your setup is connected to a live prediction market right now — it's asking whether BTC will be above $X in the next 15 minutes. When we build your bot next, it'll trade on markets exactly like this one."

**Update `user-context.md`** with the wallet address and chain from the verification output. This keeps the user context file current for other skills.

---

## Step 6: Handoff

Everything is set up. Tell the user what they've accomplished and what's next:

> **You're all set up!** Here's what's ready:
> - Python environment with Turbine SDK installed
> - Wallet configured (address: `0x...`)
> - Trading on [chain name]
> - API connection verified
>
> **Next step: Create your first trading bot.**
>
> Run `/create-bot` — it'll help you pick a trading algorithm and generate a complete bot file. The recommended starting point is the **Price Action** strategy, which trades based on real-time BTC price movement.
>
> Or if you want to explore first:
> - Read `examples/price_action_bot.py` to see how a complete bot works
> - Check `docs/prediction-markets.md` to understand how Turbine's markets work
> - Browse `examples/README.md` for a guide to all example files

**For users new to PMs:** Before handing off to `/create-bot`, make sure they have enough context to make a meaningful choice about strategy. If they said "Never heard of them" in profiling, add:

> "Before we build your bot, it's worth understanding what you're trading. Here's the short version: every 15 minutes, there's a new question — 'Will Bitcoin be above $X?' You can buy YES or NO shares. If you're right, each share pays $1. If you're wrong, you lose what you paid. Your bot automates this decision. If you want a deeper explanation, check out `docs/prediction-markets.md` — or I can walk you through it right now."

This bridges the gap between setup (technical) and create-bot (requires understanding the domain).

### Where to go next — terminal vs IDE

**If the user is comfortable with an IDE** (technical users), suggest moving to their editor:

> "Your repo is all set up. If you use VSCode, Cursor, or another IDE, I'd recommend opening this folder there — you get syntax highlighting, a built-in terminal, and Claude Code works the same way."
>
> "To pick up where we left off, open your IDE's integrated terminal and run:"
> ```
> claude "/create-bot"
> ```
> "That'll start Claude Code and jump straight into bot creation."

**If the user prefers to stay in terminal** (or is non-technical), explain the two-terminal workflow they'll need when it's time to run the bot:

> "One thing to know: when you run your bot later, it takes over the terminal window — so you won't be able to talk to Claude and run the bot in the same window. The easy fix is to open a **second terminal window** when it's time to run the bot. One window stays for Claude, the other runs your bot."

Don't suggest this for non-technical users upfront — wait until they get to the "run it" step. Just keep them in the current terminal for now.

Use `AskUserQuestion`:
- **"Want to create your first trading bot now?"**
- Options: "Yes, let's build a bot" / "No, I want to explore first"

If yes and staying in this terminal: Tell them to run `/create-bot`.
If yes and switching to IDE: Give them the command to copy: `claude "/create-bot"`
If no: Wish them well and remind them `/create-bot` is there when they're ready.
