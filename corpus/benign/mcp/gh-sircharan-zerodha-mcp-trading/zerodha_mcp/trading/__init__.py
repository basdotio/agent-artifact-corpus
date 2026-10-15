"""
Trading module for executing and managing trades on the Zerodha platform.

This module provides a comprehensive suite of trading functionality including:

Core Features:
-------------
- Order execution (market, limit, stop-loss)
- Position management
- Portfolio tracking
- Risk management
- Trade logging and analysis

Submodules:
-----------
- utils: Utility functions for trading operations
- strategies: Trading strategy implementations
- risk: Risk management tools and calculations
- orders: Order management and execution
- positions: Position tracking and management

Example Usage:
-------------
>>> from zerodha_mcp.trading import ZerodhaTrade
>>> trader = ZerodhaTrade()
>>> 
>>> # Place a market order
>>> order = trader.place_market_order(
...     symbol="RELIANCE",
...     quantity=1,
...     transaction_type="BUY"
... )
>>> 
>>> # Get current positions
>>> positions = trader.get_positions()

For detailed documentation on each submodule, refer to their respective docstrings.
"""

from .utils import calculate_risk, validate_order_params, calculate_position_value

__all__ = [
    'calculate_risk',
    'validate_order_params',
    'calculate_position_value',
] 