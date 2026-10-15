import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any, Dict, List
from hyperliquid.info import Info
from hyperliquid.utils import constants
from mcp.server.fastmcp import FastMCP, Context, Image
from mcp.server.fastmcp.prompts import base
from PIL import Image as PILImage
import json
from datetime import datetime
import iso8601

info = Info(constants.MAINNET_API_URL, skip_ws=True)  # Initialize Info for mainnet

# Create MCP server
mcp = FastMCP(
    name="Hyperliquid Info",
    dependencies=["hyperliquid-python-sdk", "pillow", "python-iso8601"]
)

# Tool: Get user state
@mcp.tool()
async def get_user_state(account_address: str, check_spot: bool=False, ctx: Context=None) -> str:
    """
    Query user state including trading positions, margin, and withdrawable balance.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        check_spot (bool, optional): If True, queries spot user state; otherwise, queries perpetuals state. Defaults to False.
        ctx (Context, optional): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing the user state, including a list of positions (with symbol, size, entry_price,
            current_price, unrealized_pnl), margin_summary, and withdrawable balance. Returns a JSON string with an
            error message if the query fails.
    """
    try:
        user_state = info.spot_user_state(account_address) if check_spot else info.user_state(account_address)
        return json.dumps(user_state)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user state: {str(e)}"})

# Tool: Get user open orders
@mcp.tool()
async def get_user_open_orders(account_address: str, ctx: Context) -> str:
    """
    Fetch all open orders for a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of open orders, each with details such as order ID, symbol, size, price,
            and status. Returns a JSON string with an error message if the query fails.
    """
    try:
        open_orders = info.open_orders(account_address)
        return json.dumps(open_orders)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user open orders: {str(e)}"})

# Tool: Get all mids
@mcp.tool()
async def get_all_mids(ctx: Context) -> str:
    """
    Retrieve the mid prices for all trading pairs available on the exchange.

    Parameters:
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a dictionary of trading pairs and their mid prices.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        all_mids = info.all_mids()
        return json.dumps(all_mids)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch all mids: {str(e)}"})

# Tool: Get user trade history
@mcp.tool()
async def get_user_trade_history(account_address: str, ctx: Context) -> str:
    """
    Fetch the trade fill history for a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of trade fills, each with details such as symbol, size, price, timestamp,
            and trade ID. Returns a JSON string with an error message if the query fails.
    """
    try:
        fills = info.user_fills(account_address)
        return json.dumps(fills)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user fills: {str(e)}"})

# Tool: Get perpetual DEXs
@mcp.tool()
async def get_perp_dexs(ctx: Context) -> str:
    """
    Retrieve metadata about perpetual markets available on the Hyperliquid decentralized exchange.

    Parameters:
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing metadata about perpetual markets, including a list of trading pairs and their
            contract details (e.g., symbol, tick size, contract type). Returns a JSON string with an error message if
            the query fails.
    """
    try:
        data = info.meta()  # Use meta() as perp_dexs is not a valid SDK method
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch perpetual DEXs: {str(e)}"})

# Tool: Get coin funding history
@mcp.tool()
async def get_coin_funding_history(coin_name: str, start_time: str, end_time: str, ctx: Context) -> str:
    """
    Fetch the funding rate history for a specific coin.

    Parameters:
        coin_name (str): The trading symbol (e.g., 'BTC', 'ETH').
        start_time (str): The start time for the funding history in ISO 8601 format (e.g., '2025-01-01T00:00:00Z').
        end_time (str): The end time for the funding history in ISO 8601 format (e.g., '2025-12-31T23:59:59Z').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of funding rate records, each with details such as funding rate and timestamp.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        start_ms = int(iso8601.parse_date(start_time).timestamp() * 1000)
        end_ms = int(iso8601.parse_date(end_time).timestamp() * 1000)
        data = info.funding_history(coin_name, start_ms, end_ms)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch coin funding history: {str(e)}"})

# Tool: Get user funding history
@mcp.tool()
async def get_user_funding_history(account_address: str, start_time: str, end_time: str, ctx: Context) -> str:
    """
    Fetch the funding payment history for a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        start_time (str): The start time for the funding history in ISO 8601 format (e.g., '2025-01-01T00:00:00Z').
        end_time (str): The end time for the funding history in ISO 8601 format (e.g., '2025-12-31T23:59:59Z').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of funding payment records, each with details such as amount and timestamp.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        start_ms = int(iso8601.parse_date(start_time).timestamp() * 1000)
        end_ms = int(iso8601.parse_date(end_time).timestamp() * 1000)
        data = info.user_funding_history(account_address, start_ms, end_ms)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user funding history: {str(e)}"})

# Tool: Get L2 snapshot
@mcp.tool()
async def get_l2_snapshot(coin_name: str, ctx: Context) -> str:
    """
    Fetch the Level 2 order book snapshot for a specific coin.

    Parameters:
        coin_name (str): The trading symbol (e.g., 'BTC', 'ETH').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing the Level 2 order book snapshot, including bids and asks with prices and sizes.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.l2_snapshot(coin_name)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch L2 snapshot: {str(e)}"})

# Tool: Get candles snapshot
@mcp.tool()
async def get_candles_snapshot(coin_name: str, interval: str, start_time: str, end_time: str, ctx: Context) -> str:
    """
    Fetch the candlestick data snapshot for a specific coin.

    Parameters:
        coin_name (str): The trading symbol (e.g., 'BTC', 'ETH').
        interval (str): The candlestick interval (e.g., '1m', '5m', '1h').
        start_time (str): The start time for the candles in ISO 8601 format (e.g., '2025-01-01T00:00:00Z').
        end_time (str): The end time for the candles in ISO 8601 format (e.g., '2025-12-31T23:59:59Z').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of candlestick data, each with open, high, low, close, volume, and timestamp.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        start_ms = int(iso8601.parse_date(start_time).timestamp() * 1000)
        end_ms = int(iso8601.parse_date(end_time).timestamp() * 1000)
        data = info.candles_snapshot(coin_name, interval, start_ms, end_ms)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch candles snapshot: {str(e)}"})

# Tool: Get user fees
@mcp.tool()
async def get_user_fees(account_address: str, ctx: Context) -> str:
    """
    Fetch the fee structure and rates for a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing the user's fee structure, including maker and taker fees.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.user_fees(account_address)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user fees: {str(e)}"})

# Tool: Get user staking summary
@mcp.tool()
async def get_user_staking_summary(account_address: str, ctx: Context) -> str:
    """
    Fetch the staking summary for a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing the staking summary, including staked amounts and status.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.user_staking_summary(account_address)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user staking summary: {str(e)}"})

# Tool: Get user staking rewards
@mcp.tool()
async def get_user_staking_rewards(account_address: str, ctx: Context) -> str:
    """
    Fetch the staking rewards history for a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of staking reward records, each with amount and timestamp.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.user_staking_rewards(account_address)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user staking rewards: {str(e)}"})

# Tool: Get user order by OID
@mcp.tool()
async def get_user_order_by_oid(account_address: str, oid: int, ctx: Context) -> str:
    """
    Fetch details of a specific order by its order ID for a user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        oid (int): The order ID to query.
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing the order details, including symbol, size, price, and status.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.query_order_by_oid(account_address, oid)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user order by oid: {str(e)}"})

# Tool: Get user order by CLOID
@mcp.tool()
async def get_user_order_by_cloid(account_address: str, cloid: str, ctx: Context) -> str:
    """
    Fetch details of a specific order by its client order ID for a user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        cloid (str): The client order ID to query.
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing the order details, including symbol, size, price, and status.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.query_order_by_cloid(account_address, cloid)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user order by cloid: {str(e)}"})

# Tool: Get user sub-accounts
@mcp.tool()
async def get_user_sub_accounts(account_address: str, ctx: Context) -> str:
    """
    Fetch the sub-accounts associated with a specific user account.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').
        ctx (Context): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing a list of sub-accounts and their details.
            Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.query_sub_accounts(account_address)
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch user sub accounts: {str(e)}"})

# Tool: Get perpetual metadata
@mcp.tool()
async def get_perp_metadata(include_asset_ctxs: bool=False, ctx: Context=None) -> str:
    """
    Fetch metadata about perpetual markets on the Hyperliquid exchange.

    Parameters:
        include_asset_ctxs (bool, optional): If True, includes asset contexts with metadata. Defaults to False.
        ctx (Context, optional): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing metadata about perpetual markets, including trading pairs and contract details
            (e.g., symbol, tick size). Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.meta_and_asset_ctxs() if include_asset_ctxs else info.meta()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch perpetual metadata: {str(e)}"})

# Tool: Get spot metadata
@mcp.tool()
async def get_spot_metadata(include_asset_ctxs: bool=False, ctx: Context=None) -> str:
    """
    Fetch metadata about spot markets on the Hyperliquid exchange.

    Parameters:
        include_asset_ctxs (bool, optional): If True, includes asset contexts with metadata. Defaults to False.
        ctx (Context, optional): The MCP context object for accessing server state.

    Returns:
        str: A JSON string containing metadata about spot markets, including trading pairs and contract details
            (e.g., symbol, tick size). Returns a JSON string with an error message if the query fails.
    """
    try:
        data = info.spot_meta_and_asset_ctxs() if include_asset_ctxs else info.spot_meta()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch spot metadata: {str(e)}"})

# Prompt: Analyze user positions
@mcp.prompt()
def analyze_positions(account_address: str) -> List[base.Message]:
    """
    Analyze the user's trading positions and trading activity.

    Parameters:
        account_address (str): The Hyperliquid account address (e.g., '0xcd5051944f780a621ee62e39e493c489668acf4d').

    Returns:
        List[base.Message]: A list of messages guiding the analysis process, including instructions to use
            relevant tools for fetching trading data.
    """
    return [
        base.UserMessage(f"Please analyze the trading positions for account {account_address}:"),
        base.UserMessage("Use the get_user_state, get_user_open_orders, get_user_trade_history, get_user_funding_history, and get_user_fees tools to fetch data."),
        base.AssistantMessage(
            "I'll analyze the user's trading positions, open orders, trade history, funding payments, and fees to provide insights on risk and performance."
        )
    ]

if __name__ == "__main__":
    mcp.run()
