import os
import pysnowball as ball
from fastmcp import FastMCP
from dotenv import load_dotenv
import datetime
import json

load_dotenv()
ball.set_token(os.getenv("XUEQIU_TOKEN"))

mcp = FastMCP(name="Xueqiu MCP")


def convert_timestamps(data):
    """递归地将数据中的所有 timestamp 转换为 datetime 字符串"""
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if key == 'timestamp' and isinstance(value, (int, float)) and value > 1000000000000:  # 毫秒级时间戳
                data[key] = datetime.datetime.fromtimestamp(value/1000).strftime('%Y-%m-%d %H:%M:%S')
            elif key == 'timestamp' and isinstance(value, (int, float)) and value > 1000000000:  # 秒级时间戳
                data[key] = datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            elif key.endswith('_date') and isinstance(value, (int, float)) and value > 1000000000000:  # 毫秒级时间戳
                data[key] = datetime.datetime.fromtimestamp(value/1000).strftime('%Y-%m-%d %H:%M:%S')
            elif key.endswith('_date') and isinstance(value, (int, float)) and value > 1000000000:  # 秒级时间戳
                data[key] = datetime.datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, (dict, list)):
                data[key] = convert_timestamps(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            data[i] = convert_timestamps(item)
    return data


def process_data(data, process_config=None):
    """
    通用数据处理函数，可扩展添加各种数据处理操作
    
    Args:
        data: 原始数据
        process_config: 处理配置字典，用于指定要执行的处理操作
            例如: {'convert_timestamps': True, 'other_process': params}
    
    Returns:
        处理后的数据
    """
    if process_config is None:
        # 默认配置
        process_config = {
            'convert_timestamps': True
        }
    
    # 如果开启了时间戳转换
    if process_config.get('convert_timestamps', True):
        data = convert_timestamps(data)
    
    # 在这里可以添加更多的数据处理逻辑
    # 例如:
    # if 'format_numbers' in process_config:
    #     data = format_numbers(data, **process_config['format_numbers'])
    
    return data


@mcp.tool()
def quotec(stock_code: str="SZ000002") -> dict:
    """获取某支股票的行情数据"""
    result = ball.quotec(stock_code)
    return process_data(result)


@mcp.tool()
def quote_detail(stock_code: str="SZ000002") -> dict:
    """获取某支股票的行情数据-详细"""
    result = ball.quote_detail(stock_code)
    return process_data(result)


@mcp.tool()
def pankou(stock_code: str="SZ000002") -> dict:
    """获取实时分笔数据，可以实时取得股票当前报价和成交信息"""
    result = ball.pankou(stock_code)
    return process_data(result)


@mcp.tool()
def kline(stock_code: str="SZ000002", days: int = 100) -> dict:
    """获取K线数据。第二参数可制定从现在到N天前，默认100"""
    result = ball.kline(stock_code, days)
    return process_data(result)


@mcp.tool()
def earningforecast(stock_code: str="SZ000002") -> dict:
    """按年度获取业绩预告数据"""
    result = ball.earningforecast(stock_code)
    return process_data(result)


@mcp.tool()
def report(stock_code: str="SZ000002") -> dict:
    """获取机构评级数据"""
    result = ball.report(stock_code)
    return process_data(result)


@mcp.tool()
def capital_flow(stock_code: str="SZ000002") -> dict:
    """获取当日资金流如流出数据，每分钟数据"""
    result = ball.capital_flow(stock_code)
    return process_data(result)


@mcp.tool()
def capital_history(stock_code: str="SZ000002") -> dict:
    """获取历史资金流如流出数据，每日数据"""
    result = ball.capital_history(stock_code)
    return process_data(result)


@mcp.tool()
def capital_assort(stock_code: str="SZ000002") -> dict:
    """获取资金成交分布数据"""
    result = ball.capital_assort(stock_code)
    return process_data(result)


@mcp.tool()
def blocktrans(stock_code: str="SZ000002") -> dict:
    """获取大宗交易数据"""
    result = ball.blocktrans(stock_code)
    return process_data(result)


@mcp.tool()
def margin(stock_code: str="SZ000002") -> dict:
    """获取融资融券数据"""
    result = ball.margin(stock_code)
    return process_data(result)


@mcp.tool()
def indicator(stock_code: str="SZ000002", is_annals: int = 1, count: int = 5) -> dict:
    """按年度、季度获取业绩报表数据
    
    Args:
        stock_code: 股票代码
        is_annals: 只获取年报,默认为1
        count: 返回数据数量,默认5条
    """
    result = ball.indicator(symbol=stock_code, is_annals=is_annals, count=count)
    return process_data(result)


@mcp.tool()
def income(stock_code: str="SZ000002", is_annals: int = 1, count: int = 5) -> dict:
    """获取利润表数据
    
    Args:
        stock_code: 股票代码
        is_annals: 只获取年报,默认为1
        count: 返回数据数量,默认5条
    """
    result = ball.income(symbol=stock_code, is_annals=is_annals, count=count)
    return process_data(result)


@mcp.tool()
def balance(stock_code: str="SZ000002", is_annals: int = 1, count: int = 5) -> dict:
    """获取资产负债表数据
    
    Args:
        stock_code: 股票代码
        is_annals: 只获取年报,默认为1
        count: 返回数据数量,默认5条
    """
    result = ball.balance(symbol=stock_code, is_annals=is_annals, count=count)
    return process_data(result)


@mcp.tool()
def cash_flow(stock_code: str="SZ000002", is_annals: int = 1, count: int = 5) -> dict:
    """获取现金流量表数据
    
    Args:
        stock_code: 股票代码
        is_annals: 只获取年报,默认为1
        count: 返回数据数量,默认5条
    """
    result = ball.cash_flow(symbol=stock_code, is_annals=is_annals, count=count)
    return process_data(result)


@mcp.tool()
def business(stock_code: str="SZ000002", count: int = 5) -> dict:
    """获取主营业务构成数据
    
    Args:
        stock_code: 股票代码
        count: 返回数据数量,默认5条
    """
    result = ball.business(symbol=stock_code, count=count)
    return process_data(result)


@mcp.tool()
def top_holders(stock_code: str="SZ000002", circula: int = 1) -> dict:
    """获取十大股东数据
    
    Args:
        stock_code: 股票代码
        circula: 只获取流通股,默认为1
    """
    result = ball.top_holders(symbol=stock_code, circula=circula)
    return process_data(result)


@mcp.tool()
def main_indicator(stock_code: str="SZ000002") -> dict:
    """获取F10主要指标数据"""
    result = ball.main_indicator(stock_code)
    return process_data(result)


@mcp.tool()
def holders(stock_code: str="SZ000002") -> dict:
    """获取F10股东人数数据"""
    result = ball.holders(stock_code)
    return process_data(result)


@mcp.tool()
def org_holding_change(stock_code: str="SZ000002") -> dict:
    """获取F10机构持仓数据"""
    result = ball.org_holding_change(stock_code)
    return process_data(result)


@mcp.tool()
def bonus(stock_code: str="SZ000002", page: int = 1, size: int = 10) -> dict:
    """获取F10分红融资数据
    
    Args:
        stock_code: 股票代码
        page: 第几页 默认1
        size: 每页含有多少数据 默认10
    """
    result = ball.bonus(stock_code, page=page, size=size)
    return process_data(result)


@mcp.tool()
def industry_compare(stock_code: str="SZ000002") -> dict:
    """获取F10行业对比数据"""
    result = ball.industry_compare(stock_code)
    return process_data(result)


@mcp.tool()
def watch_list() -> dict:
    """获取用户自选列表"""
    result = ball.watch_list()
    return process_data(result)


@mcp.tool()
def watch_stock(pid: int) -> dict:
    """获取用户自选列表详情
    
    Args:
        pid: 自选列表ID
    """
    result = ball.watch_stock(pid)
    return process_data(result)


@mcp.tool()
def nav_daily(cube_symbol: str="SZ000002") -> dict:
    """获取组合净值数据
    
    Args:
        cube_symbol: 组合代码
    """
    result = ball.nav_daily(cube_symbol)
    return process_data(result)


@mcp.tool()
def rebalancing_history(cube_symbol: str="SZ000002") -> dict:
    """获取组合历史交易信息
    
    Args:
        cube_symbol: 组合代码
    """
    result = ball.rebalancing_history(cube_symbol)
    return process_data(result)


@mcp.tool()
def convertible_bond(page_size: int = 5, page_count: int = 1) -> dict:
    """获取可转债信息
    
    Args:
        page_size: 每页显示数量
        page_count: 页码
    """
    result = ball.convertible_bond(page_size=page_size, page_count=page_count)
    return process_data(result)


@mcp.tool()
def index_basic_info(index_code: str="SZ000002") -> dict:
    """获取指数基本信息
    
    Args:
        index_code: 指数代码
    """
    result = ball.index_basic_info(index_code)
    return process_data(result)


@mcp.tool()
def index_details_data(index_code: str="SZ000002") -> dict:
    """获取指数详细信息
    
    Args:
        index_code: 指数代码
    """
    result = ball.index_details_data(index_code)
    return process_data(result)


@mcp.tool()
def index_weight_top10(index_code: str="SZ000002") -> dict:
    """获取指数权重股前十
    
    Args:
        index_code: 指数代码
    """
    result = ball.index_weight_top10(index_code)
    return process_data(result)


@mcp.tool()
def index_perf_7(index_code: str="SZ000002") -> dict:
    """获取指数最近7天收益数据
    
    Args:
        index_code: 指数代码
    """
    result = ball.index_perf_7(index_code)
    return process_data(result)


@mcp.tool()
def index_perf_30(index_code: str="SZ000002") -> dict:
    """获取指数最近30天收益数据
    
    Args:
        index_code: 指数代码
    """
    result = ball.index_perf_30(index_code)
    return process_data(result)


@mcp.tool()
def index_perf_90(index_code: str="SZ000002") -> dict:
    """获取指数最近90天收益数据
    
    Args:
        index_code: 指数代码
    """
    result = ball.index_perf_90(index_code)
    return process_data(result)


@mcp.tool()
def northbound_shareholding_sh(date: str = None) -> dict:
    """获取深港通北向数据
    
    Args:
        date: 日期，默认当天，格式：'2022/01/19'
    """
    result = ball.northbound_shareholding_sh(date)
    return process_data(result)


@mcp.tool()
def northbound_shareholding_sz(date: str = None) -> dict:
    """获取沪港通北向数据
    
    Args:
        date: 日期，默认当天，格式：'2022/01/19'
    """
    result = ball.northbound_shareholding_sz(date)
    return process_data(result)


@mcp.tool()
def fund_detail(fund_code: str) -> dict:
    """获取基金详细信息
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_detail(fund_code)
    return process_data(result)


@mcp.tool()
def fund_info(fund_code: str="SZ000002") -> dict:
    """获取基金基本信息
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_info(fund_code)
    return process_data(result)


@mcp.tool()
def fund_growth(fund_code: str="SZ000002") -> dict:
    """获取基金增长数据
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_growth(fund_code)
    return process_data(result)


@mcp.tool()
def fund_nav_history(fund_code: str="SZ000002") -> dict:
    """获取基金历史净值数据
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_nav_history(fund_code)
    return process_data(result)


@mcp.tool()
def fund_achievement(fund_code: str="SZ000002") -> dict:
    """获取基金业绩表现数据
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_achievement(fund_code)
    return process_data(result)


@mcp.tool()
def fund_asset(fund_code: str="SZ000002") -> dict:
    """获取基金资产配置数据
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_asset(fund_code)
    return process_data(result)


@mcp.tool()
def fund_manager(fund_code: str="SZ000002") -> dict:
    """获取基金经理信息
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_manager(fund_code)
    return process_data(result)


@mcp.tool()
def fund_trade_date(fund_code: str="SZ000002") -> dict:
    """获取基金交易日期信息
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_trade_date(fund_code)
    return process_data(result)


@mcp.tool()
def fund_derived(fund_code: str="SZ000002") -> dict:
    """获取基金衍生数据
    
    Args:
        fund_code: 基金代码
    """
    result = ball.fund_derived(fund_code)
    return process_data(result)


@mcp.tool()
def suggest_stock(keyword: str="SZ000002") -> dict:
    """关键词搜索股票代码
    
    Args:
        keyword: 关键词
    """
    result = ball.suggest_stock(keyword)
    return process_data(result)


if __name__ == "__main__":
    # This code only runs when the file is executed directly
    mcp.run()