from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
import asyncio
import logging
from pycoingecko import CoinGeckoAPI
import pandas as pd
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("crypto-trader")

# Initialize CoinGecko API client
cg = CoinGeckoAPI()

@mcp.tool("get_crypto_price")
async def get_crypto_price(symbol: str) -> Dict[str, Any]:
    """Get current cryptocurrency price and 24h change.
    
    Args:
        symbol (str): Cryptocurrency symbol (e.g., btc, eth, doge)
    
    Returns:
        Dict containing current price, 24h change, and market data
    """
    try:
        # Convert symbol to lowercase and remove any '-usd' suffix
        symbol = symbol.lower().replace('-usd', '')
        
        # Get coin ID from symbol
        coins_list = cg.get_coins_list()
        coin_id = next((coin['id'] for coin in coins_list if coin['symbol'].lower() == symbol), None)
        
        if not coin_id:
            return {"error": f"Cryptocurrency with symbol {symbol} not found"}
        
        # Get price data
        price_data = cg.get_price(ids=coin_id, vs_currencies='usd', include_24hr_change=True, 
                                 include_24hr_vol=True, include_market_cap=True)
        
        if not price_data or coin_id not in price_data:
            return {"error": f"Price data for {symbol} not available"}
            
        data = price_data[coin_id]
        
        return {
            "symbol": symbol.upper(),
            "name": coin_id,
            "price": data.get('usd', 0),
            "change_24h": data.get('usd_24h_change', 0),
            "volume_24h": data.get('usd_24h_vol', 0),
            "market_cap": data.get('usd_market_cap', 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {str(e)}")
        return {"error": f"Failed to fetch price for {symbol}: {str(e)}"}

@mcp.tool("get_crypto_market_data")
async def get_crypto_market_data(symbol: str) -> Dict[str, Any]:
    """Get detailed market data for a cryptocurrency.
    
    Args:
        symbol (str): Cryptocurrency symbol (e.g., btc, eth, doge)
    
    Returns:
        Dict containing detailed market information
    """
    try:
        # Convert symbol to lowercase and remove any '-usd' suffix
        symbol = symbol.lower().replace('-usd', '')
        
        # Get coin ID from symbol
        coins_list = cg.get_coins_list()
        coin_id = next((coin['id'] for coin in coins_list if coin['symbol'].lower() == symbol), None)
        
        if not coin_id:
            return {"error": f"Cryptocurrency with symbol {symbol} not found"}
        
        # Get detailed coin data
        coin_data = cg.get_coin_by_id(id=coin_id)
        
        market_data = coin_data.get('market_data', {})
        
        return {
            "symbol": symbol.upper(),
            "name": coin_data.get('name', ''),
            "market_cap_rank": market_data.get('market_cap_rank', 0),
            "current_price": market_data.get('current_price', {}).get('usd', 0),
            "market_cap": market_data.get('market_cap', {}).get('usd', 0),
            "total_volume": market_data.get('total_volume', {}).get('usd', 0),
            "high_24h": market_data.get('high_24h', {}).get('usd', 0),
            "low_24h": market_data.get('low_24h', {}).get('usd', 0),
            "price_change_24h": market_data.get('price_change_24h', 0),
            "price_change_percentage_24h": market_data.get('price_change_percentage_24h', 0),
            "circulating_supply": market_data.get('circulating_supply', 0),
            "total_supply": market_data.get('total_supply', 0),
            "max_supply": market_data.get('max_supply', 0),
            "ath": market_data.get('ath', {}).get('usd', 0),
            "ath_date": market_data.get('ath_date', {}).get('usd', ''),
            "atl": market_data.get('atl', {}).get('usd', 0),
            "atl_date": market_data.get('atl_date', {}).get('usd', '')
        }
    except Exception as e:
        logger.error(f"Error fetching market data for {symbol}: {str(e)}")
        return {"error": f"Failed to fetch market data for {symbol}: {str(e)}"}

@mcp.tool("get_crypto_historical_data")
async def get_crypto_historical_data(symbol: str, days: int = 30) -> Dict[str, Any]:
    """Get historical price data for a cryptocurrency.
    
    Args:
        symbol (str): Cryptocurrency symbol (e.g., btc, eth, doge)
        days (int): Number of days of data to fetch (1-365)
    
    Returns:
        Dict containing historical price data
    """
    try:
        # Convert symbol to lowercase and remove any '-usd' suffix
        symbol = symbol.lower().replace('-usd', '')
        
        # Get coin ID from symbol
        coins_list = cg.get_coins_list()
        coin_id = next((coin['id'] for coin in coins_list if coin['symbol'].lower() == symbol), None)
        
        if not coin_id:
            return {"error": f"Cryptocurrency with symbol {symbol} not found"}
        
        # Limit days to valid range
        days = max(1, min(365, days))
        
        # Get historical data
        market_chart = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=days)
        
        prices = []
        for timestamp, price in market_chart.get('prices', []):
            date = datetime.fromtimestamp(timestamp/1000)
            prices.append({
                "date": date.isoformat(),
                "price": price
            })
        
        return {
            "symbol": symbol.upper(),
            "name": coin_id,
            "days": days,
            "prices": prices
        }
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return {"error": f"Failed to fetch historical data for {symbol}: {str(e)}"}

@mcp.tool("search_crypto")
async def search_crypto(query: str) -> Dict[str, Any]:
    """Search for cryptocurrencies by name or symbol.
    
    Args:
        query (str): Search term
        
    Returns:
        Dict containing search results
    """
    try:
        # Get all coins list from CoinGecko
        coins_list = cg.get_coins_list()
        
        # Filter coins by query (case-insensitive)
        query = query.lower()
        matching_coins = [
            coin for coin in coins_list 
            if query in coin['id'].lower() or 
               query in coin['symbol'].lower() or 
               query in coin['name'].lower()
        ]
        
        # Limit to top 25 results to avoid overwhelming response
        matching_coins = matching_coins[:25]
        
        results = []
        for coin in matching_coins:
            results.append({
                "id": coin["id"],
                "symbol": coin["symbol"].upper(),
                "name": coin["name"]
            })
            
        return {"results": results}
    except Exception as e:
        logger.error(f"Error searching for {query}: {str(e)}")
        return {"error": f"Search failed: {str(e)}"}

@mcp.tool("get_trending_crypto")
async def get_trending_crypto() -> Dict[str, Any]:
    """Get trending cryptocurrencies in the last 24 hours.
    
    Returns:
        Dict containing trending cryptocurrencies
    """
    try:
        trending = cg.get_search_trending()
        
        coins = []
        for item in trending.get('coins', []):
            coin = item.get('item', {})
            coins.append({
                "id": coin.get('id', ''),
                "name": coin.get('name', ''),
                "symbol": coin.get('symbol', '').upper(),
                "market_cap_rank": coin.get('market_cap_rank', 0),
                "price_btc": coin.get('price_btc', 0)
            })
            
        return {"trending_coins": coins}
    except Exception as e:
        logger.error(f"Error fetching trending cryptocurrencies: {str(e)}")
        return {"error": f"Failed to fetch trending cryptocurrencies: {str(e)}"}

@mcp.tool("get_global_crypto_data")
async def get_global_crypto_data() -> Dict[str, Any]:
    """Get global cryptocurrency market data.
    
    Returns:
        Dict containing global market overview
    """
    try:
        global_data = cg.get_global()
        
        return {
            "active_cryptocurrencies": global_data.get('active_cryptocurrencies', 0),
            "markets": global_data.get('markets', 0),
            "total_market_cap_usd": global_data.get('total_market_cap', {}).get('usd', 0),
            "total_volume_usd": global_data.get('total_volume', {}).get('usd', 0),
            "market_cap_percentage": {
                k.upper(): v for k, v in global_data.get('market_cap_percentage', {}).items()
            },
            "updated_at": datetime.fromtimestamp(global_data.get('updated_at', 0)).isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching global data: {str(e)}")
        return {"error": f"Failed to fetch global cryptocurrency data: {str(e)}"}

if __name__ == "__main__":
    mcp.run()