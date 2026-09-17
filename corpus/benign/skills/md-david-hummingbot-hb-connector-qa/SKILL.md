---
name: hummingbot-connector-qa
description: Automate the QA process for new Hummingbot exchange connectors. Use when a user provides a GitHub PR link for a new connector or asks to test a specific exchange integration (CEX Spot/Perp, DEX/CLMM).
---

# Hummingbot Connector QA

This skill provides a standardized workflow for QA testers to validate new Hummingbot connectors. It ensures all mandatory tests (connection, balances, market data, and order execution) are performed and reported consistently.

## Execution Rules

These rules apply throughout the entire QA workflow:

1. **Working Directory**: At the start of the workflow, detect the current working directory or active workspace and use it as the base path for all file operations, cloning, and script execution. Do **not** default to `/` or any hardcoded root path.
2. **Wait for Responses**: After executing any command that interacts with the exchange (e.g., fetching candles, placing an order, checking status), always allow sufficient time for the system to execute and return a response before reading the result or proceeding to the next step. Do not assume instant completion.

## Workflow

To QA a new connector, follow these steps:

### 0. Prerequisite Check: hummingbot-mcp
Before doing anything else, verify that the `hummingbot-mcp` MCP tool is available in the current environment.
- Check whether `hummingbot-mcp-docker` (or an equivalent hummingbot-mcp server) is listed among the active MCP servers/tools.
- **If hummingbot-mcp IS present**: proceed normally to Step 1.
- **If hummingbot-mcp is NOT present**:
  - Immediately alert the user: **"⚠️ The `hummingbot-mcp` tool was not detected. This skill requires hummingbot-mcp to function. Would you like to add it now, or continue anyway?"**
  - **If the user wants to add it**, instruct them to add the following entry to their MCP server configuration (e.g. `~/.gemini/settings.json` under `mcpServers`):
    ```json
    "hummingbot-mcp-docker": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--network",
        "host",
        "-v",
        "hummingbot_mcp:/root/.hummingbot_mcp",
        "hummingbot/hummingbot-mcp:latest"
      ]
    }
    ```
    After adding it, ask the user to reload/restart their MCP client and then re-run this skill.
  - **If the user wants to continue anyway**: inform the user that the skill will use **manual `curl` commands** to test the connector in place of hummingbot-mcp tools.

### 1. PR Setup & Environment
First, prepare the environment by running the PR setup workflows for both Source and Docker builds.
- Execute the [PR Setup Workflow](references/pr-setup.md). This is a Turbo Workflow. Substitute the PR ID from the user's prompt and run it to automatically perform the setup.
- **Source Build**: Must be completed and the client must start without errors.
- **Docker Build**: Must be completed and the container must start without issues.
- **Validation**: BOTH Source and Docker setups must pass. If one of them fails, mark the setup as incomplete and do NOT move on to the next test.

### 2. Hummingbot API Setup (Required)
Build the hummingbot library from the PR source and deploy it via hummingbot-api.
- Execute the [Hummingbot API Setup Workflow](references/hummingbot-api-setup.md). This is a Turbo Workflow. Run it to automatically perform the API setup.
- **Connection**: If `localhost` fails, try `host.docker.internal`.
- **CRITICAL RULE**: Throughout the duration of this skill, you MUST ONLY connect to the `hummingbot-api` server instance that you just created in this step. If there are other API servers connected or configured on the system, you must ignore them completely.
- If there are any issues or errors during this setup, notify the user immediately before proceeding.

### 3. Connection & Market Data
Ensure the connector can communicate with the exchange and retrieve data.
- Use `setup_connector` to configure credentials.
- Use `get_market_data` to verify:
  - `prices`: Latest ticker prices.
  - `order_book`: Snapshot depth and spreads.
  - `candles`: Historical OHLCV data.
  - `funding_rate`: (For Perps) Current funding rates.

### 4. Portfolio & Trading Execution
Test the core trading functionality using small amounts (Dust/Minimum order sizes).
- **Balances**: Use `get_portfolio_overview` to verify token balances.
- **Order Execution**: Use `order_executor` to test:
  - `LIMIT` Buy/Sell.
  - `MARKET` Buy/Sell.
  - `LIMIT_MAKER` (Post-only) orders.
- **LIMIT Order Fill Validation**: After a LIMIT order is expected to fill (tight spread / near market), use `trading_active` or `search_history` to confirm:
  - Status transitions from `OPEN` → `FILLED`.
  - `filled_amount` is **not** flat `0`.
  - `fees_paid` is **not** flat `0`.
- **MARKET Order Fill Validation**: After a MARKET order is placed, verify:
  - Status transitions from `OPEN` → `FILLED`.
  - `filled_amount` is **not** flat `0`.
  - `fees_paid` is **not** flat `0`.
- **Cancellation**: To test cancellation, first fetch the current `mid_price` for the trading pair, then place a LIMIT order at least **1% away** from the mid_price (buy order at ≤ 99% of mid_price, sell order at ≥ 101% of mid_price) to prevent the order from being filled before cancellation. Then immediately cancel using `action="stop"` and verify the order is cancelled.
- **Position Management**: (For Perps/CLMM) Use `lp_executor` or `position_executor` to verify lifecycle tracking.

### 5. Generate QA Report
After testing, summarize the results using the bundled reporting script.
- Collect results in a JSON format. Valid statuses are `PASS`, `FAIL`, and `SKIPPED` (use `SKIPPED` for tests that don't apply to the connector, e.g. candles or funding rate on a spot-only connector): `[{"name": "Connect", "status": "PASS"}, {"name": "Limit Buy", "status": "FAIL", "notes": "Order rejected due to precision"}, {"name": "Candles", "status": "SKIPPED", "notes": "Not supported by this connector"}]`.
- Run the script: `node scripts/generate_qa_report.cjs '<json_results>'`.
- Display the full generated Markdown report to the user in the chat.
- Ask the user: **"Would you like to post this report back to the GitHub PR?"** and only post it if they confirm.

## Bug & Error Handling Rule
**CRITICAL RULE**: If a bug or issue is found during any step of the QA process:
1. **NO CODE CHANGES**: Do not attempt to modify the codebase to fix the issue.
2. **LOG ERRORS**: Document the issue in a specific logfile (e.g., `qa_errors.log`). Your log MUST include:
   - Steps taken / steps to reproduce the issue.
   - The exact error messages and stack traces.
   - An explanation of the issue.
3. **NOTIFY USER**: Inform the user about the issue immediately.
4. **CONTINUE IF POSSIBLE**: If it's still possible to proceed with other independent items in the checklist, continue testing. If the issue prevents further progress entirely, inform the user that the testing is halted and display the current overall test summary.

### Log File Format
Each entry in the log file must use the following format for readability:

```
##### <Test Name> - <STATUS>
- <description / details>

---------

##### <Test Name> - <STATUS>
- <description / details>

---------
```

**Example:**
```
##### Candles Test - PASSED
- Successfully fetched 100 OHLCV candles for BTC-USDT on 1m interval.

---------

##### LIMIT ORDERS Test - PASSED
- Placed limit buy at 99% of mid_price, verified fill and cancellation.

---------
```

## Mandatory Checklist
Always cross-reference your tests with the [QA Checklist](references/qa-checklist.md) to ensure no connector-specific requirements are missed.

## Examples

**User:** "QA this PR for the new Hyperliquid connector: https://github.com/hummingbot/hummingbot/pull/123"
**Gemini CLI:** *Activates skill, reads PR setup, performs environment checks, and guides the user through the checklist.*

**User:** "Test the balance and limit order execution for the new Binance Spot connector."
**Gemini CLI:** *Uses `get_portfolio_overview` and `order_executor` to perform the requested tests and reports the outcome.*
