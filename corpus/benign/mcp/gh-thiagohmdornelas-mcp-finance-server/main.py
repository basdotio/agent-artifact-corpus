# RODAR PARA HTTP
# fastmcp run main.py --transport streamable-http --host 127.0.0.1 --port 8001

# RODAR PARA stdio. # para executar em STDIO, nao precisa rodar o servidor
# fastmcp run main.py

from fastmcp import FastMCP
import yfinance as yf


mcp = FastMCP('yfinance MCP Server')


@mcp.tool
def get_current_stock_price(ticker: str) -> float:
    '''Retorna valor atual de uma ação com base no
    código da empresa.
    '''
    data = yf.Ticker(ticker)
    return data.fast_info.get('lastPrice')


@mcp.tool
def get_history_stock_price(ticker: str, period: str) -> dict:
    '''Retorna histórico do valor de uma ação
    com base no código da empresa e no período.
    period : str
        | Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
        | Default: 1mo
        | Can combine with start/end e.g. end = start + period
    '''
    data = yf.Ticker(ticker)
    return data.history(period=period).to_dict()


@mcp.tool
def get_company_info(ticker: str) -> dict:
    '''Retorna dados completos da empresa.
    com base no código da empresa.
    '''
    data = yf.Ticker(ticker)
    return data.info


if __name__ == '__main__':
    mcp.run()
