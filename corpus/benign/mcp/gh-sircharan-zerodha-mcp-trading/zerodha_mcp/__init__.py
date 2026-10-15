"""
Zerodha Market Connect Pro (MCP) - A sophisticated trading automation system.

This package provides a comprehensive suite of tools for automated trading on the
Zerodha platform, including:
- Automated trading execution
- Market analysis and visualization
- LLM-powered decision making
- Risk management systems
- Custom strategy implementation
- Real-time market data processing

For more information, see the documentation at:
https://github.com/charandeepkapoor/zerodha-mcp

Author: Charandeep Kapoor
License: MIT
"""

__version__ = "0.1.0"
__author__ = "Charandeep Kapoor"
__license__ = "MIT"

# Package level imports for convenience
from .trading.base import Strategy
from .auth.client import ZerodhaClient
from .analysis.market_data import MarketAnalyzer

# Version information
VERSION_INFO = {
    'major': 0,
    'minor': 1,
    'patch': 0,
    'status': 'beta'
} 