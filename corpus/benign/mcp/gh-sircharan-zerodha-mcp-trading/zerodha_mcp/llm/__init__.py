"""
Language Model Integration Module for Zerodha MCP Trading System.

This module provides advanced natural language processing capabilities for:
- Trading Command Processing
  - Natural language order placement
  - Position management commands
  - Portfolio queries
  - Market analysis requests
  
- Market Sentiment Analysis
  - News sentiment processing
  - Social media sentiment analysis
  - Market commentary interpretation
  - Trend analysis
  
- Strategy Optimization
  - Parameter tuning suggestions
  - Performance analysis
  - Risk assessment
  - Trading pattern recognition
  
- Trading Journal Analysis
  - Trade review and insights
  - Pattern recognition in trading behavior
  - Performance improvement suggestions
  - Risk management recommendations

Example Usage:
-------------
>>> from zerodha_mcp.llm import TradingAssistant
>>> 
>>> # Create assistant instance
>>> assistant = TradingAssistant()
>>> 
>>> # Process natural language command
>>> response = assistant.process_command(
...     "Buy 10 shares of Reliance at market price"
... )
>>> 
>>> # Analyze market sentiment
>>> sentiment = assistant.analyze_sentiment(
...     "Latest market news and social media data"
... )

The module uses state-of-the-art language models to enhance
trading decisions and automate complex trading operations.

Security Note:
-------------
- API keys should be stored securely in .env file
- Sensitive trading data is processed locally
- Model outputs are validated before execution
- All commands go through safety checks
"""

from .assistant import TradingAssistant
from .sentiment import SentimentAnalyzer
from .optimizer import StrategyOptimizer
from .journal import JournalAnalyzer

__all__ = [
    'TradingAssistant',
    'SentimentAnalyzer',
    'StrategyOptimizer',
    'JournalAnalyzer',
] 