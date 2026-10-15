# 🚀 Zerodha Market Connect Pro

An advanced algorithmic trading system for Zerodha, featuring automated trading strategies, real-time market analysis, and LLM-powered decision making. Built with Python and integrated with Zerodha's Kite API.

## 📝 Description

Zerodha Market Connect Pro (MCP) is a comprehensive algorithmic trading platform designed specifically for Zerodha traders. This system combines cutting-edge technology with sophisticated trading strategies to provide a powerful automated trading solution. Here's what makes it special:

- **Intelligent Trading**: Leverages Large Language Models (LLMs) for market analysis and trading decisions
- **Real-time Processing**: Handles live market data with low-latency execution and websocket streaming
- **Risk Management**: Implements robust risk controls including position sizing, stop-losses, and exposure limits
- **Strategy Flexibility**: Supports multiple trading strategies with customizable parameters
- **Professional Tools**: Includes advanced technical analysis, volume profiling, and price action pattern recognition
- **Developer Friendly**: Well-documented API, extensive testing suite, and Docker support for easy deployment

Perfect for both professional traders looking to automate their strategies and developers interested in algorithmic trading.

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Zerodha-orange)

## 🌟 Key Features

- **🤖 Automated Trading**
  - Real-time order execution
  - Multiple strategy support
  - Customizable entry/exit rules
  - Risk management automation

- **📊 Advanced Market Analysis**
  - Real-time market data processing
  - Technical indicator calculations
  - Volume profile analysis
  - Price action patterns

- **🧠 LLM Integration**
  - Natural language trading commands
  - Market sentiment analysis
  - Strategy optimization
  - Trading journal analysis

- **⚡ High Performance**
  - Asynchronous operations
  - Efficient data handling
  - Real-time websocket streaming
  - Low-latency execution

- **🛡️ Risk Management**
  - Position sizing rules
  - Stop-loss automation
  - Exposure limits
  - Portfolio diversification

## 🔧 Technical Architecture

```
zerodha_mcp/
├── auth/           # Authentication and session management
├── trading/        # Core trading functionality
├── analysis/       # Market analysis and indicators
└── llm/           # Language model integration
```

## 📋 Prerequisites

- Python 3.8 or higher
- [Zerodha Kite](https://kite.zerodha.com/) trading account
- API credentials from [Zerodha Developer Console](https://developers.kite.trade/)
- OpenAI API key (for LLM features)

## 🚀 Quick Start

1. **Clone the Repository**
   ```bash
   git clone https://github.com/SirCharan/zerodha-market-connect-pro.git
   cd zerodha-market-connect-pro
   ```

2. **Set Up Environment**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure Credentials**
   ```bash
   # Create .env file
   cp .env.example .env
   
   # Edit .env with your credentials
   ZERODHA_API_KEY=your_api_key
   ZERODHA_API_SECRET=your_api_secret
   OPENAI_API_KEY=your_openai_api_key  # Optional
   ```

4. **Start Trading System**
   ```bash
   python main.py
   ```

## 📊 Trading Strategies

### Built-in Strategies

1. **Moving Average Crossover**
   ```python
   from zerodha_mcp.trading.strategies import MACrossStrategy
   
   strategy = MACrossStrategy(
       fast_period=10,
       slow_period=30,
       timeframe="5min"
   )
   ```

2. **RSI Mean Reversion**
   ```python
   from zerodha_mcp.trading.strategies import RSIMeanReversionStrategy
   
   strategy = RSIMeanReversionStrategy(
       period=14,
       overbought=70,
       oversold=30
   )
   ```

### Custom Strategy Development

Create your own strategy by inheriting from the base Strategy class:

```python
from zerodha_mcp.trading.base import Strategy

class MyCustomStrategy(Strategy):
    def __init__(self, **params):
        super().__init__()
        self.params = params

    def generate_signals(self, data):
        # Implement your strategy logic here
        pass

    def on_trade(self, trade):
        # Handle trade events
        pass
```

## 🔧 Configuration

### Trading Parameters

Edit `config/default.yaml` to customize trading behavior:

```yaml
trading:
  default_quantity: 1
  max_position_size: 100000
  stop_loss_percent: 2.0
  target_profit_percent: 4.0

risk_management:
  max_daily_loss: 10000
  max_trades_per_day: 10
  max_open_positions: 5

strategies:
  moving_average_crossover:
    enabled: true
    timeframe: "5min"
    fast_period: 10
    slow_period: 30
```

## 🐳 Docker Deployment

1. **Build Image**
   ```bash
   docker build -t zerodha-market-connect-pro .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name zerodha-market-connect-pro \
     -v $(pwd)/config:/app/config \
     -v $(pwd)/.env:/app/.env \
     zerodha-market-connect-pro
   ```

## 📈 Performance Monitoring

### Real-time Monitoring
```bash
# View trading logs
tail -f mcp.log

# Check system status
python -m zerodha_mcp.status

# Generate performance report
python -m zerodha_mcp.report
```

### Metrics Dashboard
Access the web dashboard at `http://localhost:5000/dashboard` for:
- P&L visualization
- Strategy performance
- Risk metrics
- Trade history

## 🧪 Development

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=zerodha_mcp tests/

# Run specific test category
pytest tests/test_trading.py
```

### Code Quality
```bash
# Format code
black zerodha_mcp tests

# Check typing
mypy zerodha_mcp

# Run linter
flake8 zerodha_mcp tests
```

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify API credentials in `.env`
   - Check token expiration
   - Ensure API access is enabled

2. **Order Placement Failures**
   - Verify account balance
   - Check trading hours
   - Review order parameters

3. **Strategy Issues**
   - Validate configuration
   - Check data availability
   - Review error logs

## 📚 API Documentation

### Trading Operations

```python
from zerodha_mcp import ZerodhaMCP

# Initialize client
client = ZerodhaMCP()

# Place order
order = client.place_order(
    symbol="RELIANCE",
    quantity=1,
    side="BUY",
    order_type="MARKET"
)

# Get positions
positions = client.get_positions()

# Get holdings
holdings = client.get_holdings()
```

### Market Data

```python
# Get historical data
data = client.get_historical_data(
    symbol="RELIANCE",
    interval="5minute",
    from_date="2024-01-01",
    to_date="2024-01-31"
)

# Stream live ticks
client.subscribe(["RELIANCE"], callback=on_tick)
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📬 Support & Contact

- 📧 Email: charandeepkapoor3@gmail.com
- 💻 GitHub: [@SirCharan](https://github.com/SirCharan)
- 📝 Issues: [GitHub Issues](https://github.com/SirCharan/zerodha-market-connect-pro/issues)
- 📚 Wiki: [Project Documentation](https://github.com/SirCharan/zerodha-market-connect-pro/wiki)

## 🙏 Acknowledgments

- [Zerodha](https://zerodha.com/) for their excellent trading platform
- [KiteConnect](https://kite.trade/) for the robust API
- All contributors who have helped improve this project
