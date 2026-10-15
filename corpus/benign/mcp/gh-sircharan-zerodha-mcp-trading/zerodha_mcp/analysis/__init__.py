"""
Market Analysis Module for Zerodha MCP Trading System.

This module provides comprehensive market analysis tools and utilities for:
- Technical Analysis
  - Moving averages (SMA, EMA, VWAP)
  - Momentum indicators (RSI, MACD, Stochastic)
  - Volume analysis
  - Price patterns
  
- Statistical Analysis
  - Volatility calculations
  - Correlation analysis
  - Risk metrics
  - Performance statistics
  
- Market Data Processing
  - Real-time data handling
  - Historical data analysis
  - Data normalization
  - Feature engineering

Example Usage:
-------------
>>> from zerodha_mcp.analysis import TechnicalAnalyzer
>>> 
>>> # Create analyzer instance
>>> analyzer = TechnicalAnalyzer()
>>> 
>>> # Calculate RSI
>>> rsi = analyzer.calculate_rsi(data, period=14)
>>> 
>>> # Get VWAP
>>> vwap = analyzer.calculate_vwap(data)

The module integrates with the trading system to provide real-time
analysis for automated trading decisions.
"""

from .indicators import calculate_rsi, calculate_vwap, calculate_macd
from .statistics import calculate_volatility, calculate_sharpe_ratio
from .patterns import identify_patterns, scan_candlesticks

__all__ = [
    'calculate_rsi',
    'calculate_vwap',
    'calculate_macd',
    'calculate_volatility',
    'calculate_sharpe_ratio',
    'identify_patterns',
    'scan_candlesticks',
] 