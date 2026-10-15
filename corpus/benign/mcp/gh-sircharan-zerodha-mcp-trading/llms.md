# Zerodha Market Connect Pro (MCP) - LLM Documentation

## Project Overview

Zerodha Market Connect Pro (MCP) is a sophisticated algorithmic trading system designed for the Zerodha trading platform. The project combines advanced market analysis capabilities with LLM-powered decision making to create an intelligent and efficient trading experience.

## Repository Structure

```
zerodha_mcp/
├── auth/           # Authentication and session management
│   ├── __init__.py
│   └── generate_token.py
├── trading/        # Core trading functionality
│   ├── __init__.py
│   └── utils.py
├── analysis/       # Market analysis and indicators
│   └── __init__.py
└── llm/           # Language model integration
    └── __init__.py
```

## Core Components

### 1. Trading Module (`zerodha_mcp/trading/`)
- Order execution (market, limit, stop-loss)
- Position management
- Portfolio tracking
- Risk management
- Trade logging

### 2. Analysis Module (`zerodha_mcp/analysis/`)
- Technical indicators (RSI, MACD, Moving Averages)
- Statistical analysis
- Market data processing
- Pattern recognition

### 3. LLM Integration (`zerodha_mcp/llm/`)
- Natural language trading commands
- Market sentiment analysis
- Strategy optimization
- Trading journal analysis

### 4. Authentication (`zerodha_mcp/auth/`)
- Secure token management
- Session handling
- API authentication

## Key Features

1. **Automated Trading**
   - Real-time order execution
   - Multiple strategy support
   - Custom entry/exit rules
   - Risk management automation

2. **Market Analysis**
   - Real-time data processing
   - Technical indicators
   - Volume analysis
   - Price patterns

3. **LLM Capabilities**
   - Natural language commands
   - Sentiment analysis
   - Strategy optimization
   - Performance analysis

4. **Risk Management**
   - Position sizing
   - Stop-loss automation
   - Exposure limits
   - Portfolio diversification

## Code Examples

### Trading Operations
```python
from zerodha_mcp import ZerodhaMCP

# Initialize client
client = ZerodhaMCP()

# Place market order
order = client.place_order(
    symbol="RELIANCE",
    quantity=1,
    side="BUY",
    order_type="MARKET"
)

# Get positions
positions = client.get_positions()
```

### Market Analysis
```python
from zerodha_mcp.analysis import TechnicalAnalyzer

# Create analyzer
analyzer = TechnicalAnalyzer()

# Calculate indicators
rsi = analyzer.calculate_rsi(data, period=14)
vwap = analyzer.calculate_vwap(data)
```

### LLM Integration
```python
from zerodha_mcp.llm import TradingAssistant

# Create assistant
assistant = TradingAssistant()

# Process natural language command
response = assistant.process_command(
    "Buy 10 shares of Reliance at market price"
)

# Analyze sentiment
sentiment = assistant.analyze_sentiment(
    "Latest market news and trends"
)
```

## Dependencies

- Python 3.8+
- KiteConnect API
- FastAPI
- OpenAI API (for LLM features)
- Technical analysis libraries

## Configuration

The system is configured through:
1. Environment variables (.env file)
2. YAML configuration (config/default.yaml)
3. Strategy-specific parameters

## Security Features

1. **Authentication**
   - Secure token storage
   - API key management
   - Session validation

2. **Data Protection**
   - Local processing
   - Encrypted storage
   - Access controls

3. **Trading Safety**
   - Order validation
   - Risk checks
   - Position limits

## Performance Characteristics

1. **Speed**
   - Low-latency execution
   - Asynchronous operations
   - Efficient data handling

2. **Reliability**
   - Error handling
   - Connection management
   - State persistence

3. **Scalability**
   - Multiple strategies
   - Parallel processing
   - Resource optimization

## Integration Points

1. **Market Data**
   - Real-time feeds
   - Historical data
   - Order book depth

2. **Trading Platform**
   - Order management
   - Position tracking
   - Portfolio updates

3. **Analysis Tools**
   - Technical indicators
   - Statistical models
   - Pattern recognition

## Error Handling

The system implements comprehensive error handling for:
1. Network issues
2. API failures
3. Data inconsistencies
4. Trading errors

## Monitoring

Real-time monitoring available through:
1. Logging system
2. Web dashboard
3. Performance metrics
4. Alert mechanisms

## Development Guidelines

1. **Code Structure**
   - Modular design
   - Clean architecture
   - Type hints
   - Documentation

2. **Testing**
   - Unit tests
   - Integration tests
   - Strategy backtesting

3. **Deployment**
   - Docker support
   - Environment setup
   - Dependency management

## Project Metadata

- Version: 0.1.0
- Status: Beta
- License: MIT
- Author: Charandeep Kapoor
- Email: charandeepkapoor3@gmail.com
- Repository: https://github.com/SirCharan/zerodha-market-connect-pro

## Contact & Support

- GitHub: [@SirCharan](https://github.com/SirCharan)
- Email: charandeepkapoor3@gmail.com
- Issues: [GitHub Issues](https://github.com/SirCharan/zerodha-market-connect-pro/issues)
- Documentation: [Project Wiki](https://github.com/SirCharan/zerodha-market-connect-pro/wiki) 