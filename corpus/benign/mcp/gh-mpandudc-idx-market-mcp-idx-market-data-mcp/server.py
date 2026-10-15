"""IDX Market Data, Chart Pattern & Quantitative Risk MCP Server."""
import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
import httpx
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplfinance as mpf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("idx-market-data-mcp")

mcp = FastMCP(
    name="idx-market-data-mcp",
)

USD_REPORTING_EMITEN = {
    "KRAS", "AMMN", "MEDC", "ADRO", "INDY", "BUMI", "MBMA", "NCKL", "ITMG", "HRUM", "PTRO", "DOID"
}

SCRATCH_DIR = os.environ.get("IDX_MCP_CACHE_DIR", tempfile.gettempdir())
os.makedirs(SCRATCH_DIR, exist_ok=True)
STOCKBIT_TOKEN_FILE = os.path.expanduser("~/.config/stockbit/token")
HERMES_TOKEN_FILE = os.path.expanduser("~/.hermes/stockbit_token")


def _get_stockbit_headers() -> Optional[Dict[str, str]]:
    token = os.environ.get("STOCKBIT_BEARER_TOKEN", "").strip()
    if not token:
        for path in (STOCKBIT_TOKEN_FILE, HERMES_TOKEN_FILE):
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        t = f.read().strip()
                        if t:
                            token = t
                            break
                except Exception as e:
                    logger.warning("Failed to read stockbit token from %s: %s", path, e)

    if token:
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
    return None



@mcp.tool()
async def idx_get_market_quote(ticker: str) -> Dict[str, Any]:
    """Fetch live market quote, price, volume, and intraday range for an Indonesian stock (.JK).

    Args:
        ticker: 4-letter IDX stock code without suffix (e.g. 'SMSM', 'BBCA', 'MYOR').
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_ticker}.JK?range=1d&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {
                    "status": "error",
                    "ticker": clean_ticker,
                    "error": f"Upstream Yahoo returned HTTP {res.status_code}"
                }
            data = res.json()
            chart = data.get("chart", {}).get("result", [{}])[0]
            meta = chart.get("meta", {})
            price = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
            prev_close = meta.get("chartPreviousClose") or price
            day_high = meta.get("regularMarketDayHigh")
            day_low = meta.get("regularMarketDayLow")
            currency = meta.get("currency", "IDR")
            change = (price - prev_close) if (price and prev_close) else 0.0
            change_pct = (change / prev_close * 100.0) if prev_close else 0.0

            indicators = chart.get("indicators", {}).get("quote", [{}])[0]
            volumes = [v for v in indicators.get("volume", []) if v is not None]
            volume = volumes[-1] if volumes else 0

            return {
                "status": "success",
                "ticker": clean_ticker,
                "exchange": "IDX",
                "price_idr": price,
                "prev_close_idr": prev_close,
                "change_idr": round(change, 2),
                "change_pct": round(change_pct, 2),
                "day_high": day_high,
                "day_low": day_low,
                "volume_shares": volume,
                "volume_lots": int(volume / 100) if volume else 0,
                "currency": currency,
            }
    except Exception as exc:
        logger.warning("Failed fetching quote for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
async def idx_analyze_chart_pattern(
    ticker: str,
    timeframe: str = "1d",
    period: str = "3mo"
) -> Dict[str, Any]:
    """Algorithmically analyze chart patterns (triangles, channels, support/resistance) and generate an annotated candlestick chart image.

    Args:
        ticker: 4-letter IDX ticker code (e.g. 'SMSM', 'MYOR', 'BBCA').
        timeframe: Candle interval ('1d' for daily, '60m' for 1-hour).
        period: Historical lookback period ('1mo', '3mo', '6mo', '1y').
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    interval = "60m" if timeframe.lower() in ("1h", "60m") else "1d"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_ticker}.JK?range={period}&interval={interval}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        async with httpx.AsyncClient(timeout=12.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {"status": "error", "error": f"Failed fetching OHLCV: HTTP {res.status_code}"}
            data = res.json()
            chart = data.get("chart", {}).get("result", [{}])[0]
            timestamps = chart.get("timestamp", [])
            quotes = chart.get("indicators", {}).get("quote", [{}])[0]

            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
            df = pd.DataFrame({
                "Open": quotes.get("open", []),
                "High": quotes.get("high", []),
                "Low": quotes.get("low", []),
                "Close": quotes.get("close", []),
                "Volume": quotes.get("volume", [])
            }, index=pd.DatetimeIndex(dates)).dropna()

            if len(df) < 15:
                return {"status": "error", "error": "Insufficient candle bars for pattern recognition"}

            order = 5 if interval == "60m" else 3
            high_idx = argrelextrema(df["High"].values, np.greater, order=order)[0]
            low_idx = argrelextrema(df["Low"].values, np.less, order=order)[0]

            if len(high_idx) < 2 or len(low_idx) < 2:
                high_idx = np.array([0, len(df) - 1])
                low_idx = np.array([0, len(df) - 1])

            x_all = np.arange(len(df))
            p_high = np.polyfit(high_idx, df["High"].iloc[high_idx].values, 1)
            line_high = np.polyval(p_high, x_all)

            p_low = np.polyfit(low_idx, df["Low"].iloc[low_idx].values, 1)
            line_low = np.polyval(p_low, x_all)

            slope_high = p_high[0]
            slope_low = p_low[0]
            curr_price = float(df["Close"].iloc[-1])
            res_now = float(line_high[-1])
            sup_now = float(line_low[-1])

            pct_slope_high = slope_high / curr_price * 100.0
            pct_slope_low = slope_low / curr_price * 100.0

            if pct_slope_high < -0.05 and abs(pct_slope_low) <= 0.15:
                pattern = "DESCENDING_TRIANGLE"
                prob_breakdown = 64
                prob_breakout = 36
                bias = "BEARISH_BREAKDOWN_OR_DIVIDEND_ACCUMULATION"
            elif abs(pct_slope_high) <= 0.15 and pct_slope_low > 0.05:
                pattern = "ASCENDING_TRIANGLE"
                prob_breakout = 65
                prob_breakdown = 35
                bias = "BULLISH_BREAKOUT"
            elif pct_slope_high < -0.05 and pct_slope_low > 0.05:
                pattern = "SYMMETRICAL_TRIANGLE"
                prob_breakout = 52
                prob_breakdown = 48
                bias = "NEUTRAL_COIL_WAIT_BREAK"
            elif pct_slope_high < -0.05 and pct_slope_low < -0.05:
                pattern = "FALLING_WEDGE_OR_CHANNEL"
                prob_breakout = 68
                prob_breakdown = 32
                bias = "BULLISH_REVERSAL"
            else:
                pattern = "RECTANGLE_RANGE"
                prob_breakout = 50
                prob_breakdown = 50
                bias = "RANGE_BOUND"

            chart_filename = f"chart_{clean_ticker}_{interval}.png"
            chart_path = os.path.join(SCRATCH_DIR, chart_filename)
            seq = [
                list(zip(df.index, line_high)),
                list(zip(df.index, line_low)),
            ]

            mpf.plot(
                df,
                type="candle",
                volume=True,
                alines=dict(alines=seq, colors=["blue", "red"], linewidths=2),
                style="yahoo",
                savefig=chart_path,
                title=f"{clean_ticker} ({interval}) — {pattern}"
            )

            return {
                "status": "success",
                "ticker": clean_ticker,
                "timeframe": interval,
                "current_price": curr_price,
                "pattern": pattern,
                "bias": bias,
                "resistance_line_now": round(res_now, 1),
                "support_line_now": round(sup_now, 1),
                "slope_resistance_pct": round(pct_slope_high, 3),
                "slope_support_pct": round(pct_slope_low, 3),
                "breakout_confirmation_level": round(res_now * 1.015, 1),
                "breakdown_discount_level": round(sup_now * 0.985, 1),
                "bulkowski_probabilities": {
                    "breakdown_pct": prob_breakdown,
                    "breakout_pct": prob_breakout
                },
                "chart_image_path": chart_path,
                "media_directive": f"MEDIA:{chart_path}"
            }
    except Exception as exc:
        logger.exception("Failed pattern analysis for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
def idx_sanitize_financials(
    ticker: str,
    pbv: float,
    roe_pct: float,
    der: float,
    is_bank: bool = False,
    usd_idr_rate: float = 16000.0,
) -> Dict[str, Any]:
    """Sanitize financial metrics against USD denomination mismatches, thin-equity ROE distortions, and solvency traps.

    Args:
        ticker: 4-letter IDX ticker code.
        pbv: Reported Price-to-Book Value ratio.
        roe_pct: Reported Return on Equity in percent (e.g. 28.8 for 28.8%).
        der: Reported Debt-to-Equity ratio.
        is_bank: Whether the company is a banking institution.
        usd_idr_rate: Current USD/IDR exchange rate (default: 16,000).
    """
    clean_ticker = ticker.strip().upper()
    flags = []
    sanitized_pbv = pbv
    sanitized_roe = roe_pct
    risk_verdict = "QUALIFIED"

    # 1. USD Currency Mismatch Check
    is_usd_reporter = clean_ticker in USD_REPORTING_EMITEN or pbv > 1000.0
    if is_usd_reporter and pbv > 500.0:
        sanitized_pbv = round(pbv / usd_idr_rate, 2)
        flags.append(f"USD_DENOMINATED_PBV_NORMALIZED: {pbv} -> {sanitized_pbv}")
    elif pbv > 100.0:
        sanitized_pbv = 50.0
        flags.append("PBV_CAPPED_AT_50")

    # 2. Solvency & Distress Trap
    if not is_bank and der > 1.5:
        risk_verdict = "DISTRESSED_LEVERAGE"
        flags.append(f"SOLVENCY_VIOLATION: DER {der:.2f} > 1.5x (Non-Bank)")

    # 3. Thin-Equity ROE Accounting Distortion
    if not is_bank and sanitized_pbv < 0.6 and roe_pct > 25.0:
        sanitized_roe = 6.0
        flags.append(f"THIN_EQUITY_ROE_CLAMPED: {roe_pct:.1f}% -> 6.0% (Cost of capital floor)")

    return {
        "ticker": clean_ticker,
        "is_usd_reporter": is_usd_reporter,
        "raw_pbv": pbv,
        "sanitized_pbv": sanitized_pbv,
        "raw_roe_pct": roe_pct,
        "sanitized_roe_pct": sanitized_roe,
        "der": der,
        "is_bank": is_bank,
        "risk_verdict": risk_verdict,
        "flags": flags,
        "recommendation_ceiling": "WATCHLIST" if risk_verdict != "QUALIFIED" else "ACCUMULATE",
    }


@mcp.tool()
def idx_check_sector_concentration(
    holdings: List[Dict[str, Any]],
    candidate_ticker: str,
    candidate_sector: str,
) -> Dict[str, Any]:
    """Audit portfolio sector weights against the 50% single-sector concentration ceiling before adding new stock.

    Args:
        holdings: List of current holdings dicts containing 'ticker', 'sector', 'value_idr'.
        candidate_ticker: Ticker of the stock to be evaluated.
        candidate_sector: Sector of the candidate stock.
    """
    total_val = sum(float(h.get("value_idr", 0)) for h in holdings) or 1.0
    sector_totals: Dict[str, float] = {}

    for h in holdings:
        sec = str(h.get("sector", "Other")).strip().capitalize()
        val = float(h.get("value_idr", 0))
        sector_totals[sec] = sector_totals.get(sec, 0.0) + val

    sector_weights = {sec: round(val / total_val * 100.0, 1) for sec, val in sector_totals.items()}
    overconcentrated_sectors = [sec for sec, w in sector_weights.items() if w >= 50.0]

    cand_sec = candidate_sector.strip().capitalize()
    is_blocked = cand_sec in overconcentrated_sectors

    return {
        "total_portfolio_idr": total_val,
        "sector_weights_pct": sector_weights,
        "overconcentrated_sectors": overconcentrated_sectors,
        "candidate_ticker": candidate_ticker.upper(),
        "candidate_sector": cand_sec,
        "is_sector_permitted": not is_blocked,
        "verdict": "REJECT_SECTOR_CLUSTER" if is_blocked else "PERMITTED_DIVERSIFICATION",
        "guidance": (
            f"Sector '{cand_sec}' holds {sector_weights.get(cand_sec, 0.0)}% (Ceiling: 50%). Reject candidate."
            if is_blocked
            else f"Sector '{cand_sec}' is acceptable. Permitted for allocation."
        )
    }


@mcp.tool()
def idx_calc_tranche_orders(
    ticker: str,
    budget_idr: float,
    current_price: float,
    support_level: float = 0.0,
    dividend_per_share: float = 0.0,
) -> Dict[str, Any]:
    """Calculate mathematically disciplined 2-tranche limit orders and lot allocations for an IDX stock.

    Args:
        ticker: 4-letter IDX ticker code.
        budget_idr: Total IDR allocation budget for this stock (e.g. 12,000,000).
        current_price: Latest market price per share.
        support_level: Nearest resting orderbook support level (default: current price * 0.995).
        dividend_per_share: Expected annual dividend per share in IDR for yield projection.
    """
    clean_ticker = ticker.strip().upper()
    tranche_budget = budget_idr / 2.0
    ref_support = support_level if support_level > 0 else round(current_price * 0.995)

    # Tranche 1: Accumulation (50% budget)
    price_1a = ref_support
    price_1b = round(ref_support * 0.997)
    budget_1a = tranche_budget / 2.0
    budget_1b = tranche_budget / 2.0

    lots_1a = int(budget_1a / (price_1a * 100))
    lots_1b = int(budget_1b / (price_1b * 100))
    val_1a = lots_1a * price_1a * 100
    val_1b = lots_1b * price_1b * 100

    total_lots_t1 = lots_1a + lots_1b
    total_val_t1 = val_1a + val_1b
    avg_price_t1 = round(total_val_t1 / (total_lots_t1 * 100), 1) if total_lots_t1 else current_price
    dy_t1 = round(dividend_per_share / avg_price_t1 * 100.0, 2) if (dividend_per_share and avg_price_t1) else 0.0

    # Tranche 2: Tactical Reserve (50% budget)
    discount_target = round(ref_support * 0.93)  # -7% breakdown discount
    breakout_target = round(current_price * 1.03)  # +3% breakout confirmation

    lots_t2_discount = int(tranche_budget / (discount_target * 100))
    lots_t2_breakout = int(tranche_budget / (breakout_target * 100))

    return {
        "ticker": clean_ticker,
        "total_budget_idr": budget_idr,
        "current_price": current_price,
        "tranche_1_immediate": {
            "budget_allocated_idr": total_val_t1,
            "total_lots": total_lots_t1,
            "average_entry_price": avg_price_t1,
            "projected_yield_pct": dy_t1,
            "orders": [
                {"order": "1A (Aggressive Limit)", "price": price_1a, "lots": lots_1a, "val_idr": val_1a},
                {"order": "1B (Passive Support)", "price": price_1b, "lots": lots_1b, "val_idr": val_1b},
            ]
        },
        "tranche_2_tactical_reserve": {
            "reserve_idr": tranche_budget,
            "scenario_discount_breakdown": {
                "target_price": discount_target,
                "lots": lots_t2_discount,
                "val_idr": lots_t2_discount * discount_target * 100,
                "projected_yield_pct": round(dividend_per_share / discount_target * 100.0, 2) if dividend_per_share else 0.0,
            },
            "scenario_breakout_momentum": {
                "target_price": breakout_target,
                "lots": lots_t2_breakout,
                "val_idr": lots_t2_breakout * breakout_target * 100,
            }
        }
    }


@mcp.tool()
async def idx_get_orderbook(ticker: str) -> Dict[str, Any]:
    """Fetch live 10-level Level 2 Orderbook depth, bid/ask queues, and order imbalance from Stockbit API.

    Args:
        ticker: 4-letter IDX stock code (e.g. 'MYOR', 'SMSM', 'BBCA').
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    headers = _get_stockbit_headers()
    if not headers:
        return {"status": "error", "error": "Stockbit token not configured in ~/.hermes/stockbit_token"}

    url = f"https://exodus.stockbit.com/company-price-feed/v2/orderbook/companies/{clean_ticker}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {"status": "error", "error": f"Stockbit returned HTTP {res.status_code}"}
            data = res.json().get("data", {})
            bids = data.get("bid", [])
            offers = data.get("offer", [])
            last_price = data.get("close") or data.get("lastprice")
            total_bo = data.get("total_bid_offer", {})
            fnet = data.get("fnet", 0)
            ara = data.get("ara", 0)
            arb = data.get("arb", 0)

            return {
                "status": "success",
                "ticker": clean_ticker,
                "last_price": last_price,
                "ara_price": ara,
                "arb_price": arb,
                "foreign_net_idr": fnet,
                "bids_count": len(bids),
                "offers_count": len(offers),
                "bid_ladder": bids[:10],
                "offer_ladder": offers[:10],
                "total_bid_offer": total_bo,
                "market_status": "CLOSED_CLEARED" if (len(bids) == 0 and len(offers) == 0) else "ACTIVE",
                "message": "Orderbook queues cleared post-market (16:15 WIB). Active during trading hours 09:00-16:00 WIB." if (len(bids) == 0 and len(offers) == 0) else "Live L2 orderbook active."
            }
    except Exception as exc:
        logger.exception("Failed fetching orderbook for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
async def idx_get_bandarmology(ticker: str) -> Dict[str, Any]:
    """Fetch broker summary, institutional accumulation/distribution status, and big player flows from Stockbit API.

    Args:
        ticker: 4-letter IDX stock code (e.g. 'MYOR', 'SMSM', 'BBCA').
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    headers = _get_stockbit_headers()
    if not headers:
        return {"status": "error", "error": "Stockbit token not configured in ~/.hermes/stockbit_token"}

    url = f"https://exodus.stockbit.com/marketdetectors/{clean_ticker}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {"status": "error", "error": f"Stockbit returned HTTP {res.status_code}"}
            data = res.json().get("data", {})
            bd = data.get("bandar_detector", {})
            avg = bd.get("avg", {})
            avg5 = bd.get("avg5", {})
            top1 = bd.get("top1", {})
            top3 = bd.get("top3", {})
            top5 = bd.get("top5", {})
            broker_status = bd.get("broker_accdist", "Unknown")

            return {
                "status": "success",
                "ticker": clean_ticker,
                "broker_summary_action": broker_status,
                "overall_status": avg.get("accdist", "Unknown"),
                "net_institutional_flow_idr": avg.get("amount", 0),
                "flow_percent": avg.get("percent", 0),
                "avg5_status": avg5.get("accdist", "Unknown"),
                "top1_flow": {"status": top1.get("accdist"), "amount_idr": top1.get("amount"), "vol_lots": top1.get("vol")},
                "top3_flow": {"status": top3.get("accdist"), "amount_idr": top3.get("amount"), "vol_lots": top3.get("vol")},
                "top5_flow": {"status": top5.get("accdist"), "amount_idr": top5.get("amount"), "vol_lots": top5.get("vol")},
                "average_bandar_price": bd.get("average", 0),
            }
    except Exception as exc:
        logger.exception("Failed fetching bandarmology for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
async def idx_get_keystats(ticker: str) -> Dict[str, Any]:
    """Fetch official audited financial ratios, balance sheet, valuation, and Piotroski F-score from Stockbit.

    Args:
        ticker: 4-letter IDX stock code (e.g. 'MYOR', 'SMSM', 'BBCA').
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    headers = _get_stockbit_headers()
    if not headers:
        return {"status": "error", "error": "Stockbit token not configured in ~/.hermes/stockbit_token"}

    url = f"https://exodus.stockbit.com/keystats/{clean_ticker}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {"status": "error", "error": f"Stockbit returned HTTP {res.status_code}"}
            data = res.json().get("data", {})
            closure = data.get("closure_fin_items_results", [])
            kv = {}
            for sec in closure:
                for item in sec.get("fin_name_results", []):
                    name = item.get("fitem_name")
                    val = item.get("fitem_value")
                    if name and val is not None:
                        kv[name] = val

            return {
                "status": "success",
                "ticker": clean_ticker,
                "f_score": kv.get("Piotroski F-Score"),
                "pe_annualised": kv.get("Current PE Ratio (Annualised)"),
                "pe_ttm": kv.get("Current PE Ratio (TTM)"),
                "pbv": kv.get("Current PBV (Quarter)") or kv.get("Current PBV"),
                "roe_ttm": kv.get("Return on Equity (TTM)"),
                "roa_ttm": kv.get("Return on Assets (TTM)"),
                "roce_ttm": kv.get("Return on Capital Employed (TTM)"),
                "der": kv.get("Debt to Equity Ratio (Quarter)"),
                "current_ratio": kv.get("Current Ratio (Quarter)"),
                "dividend_value": kv.get("Dividend") or kv.get("Dividend (TTM)"),
                "payout_ratio": kv.get("Payout Ratio"),
                "gross_margin": kv.get("Gross Profit Margin (Quarter)"),
                "operating_margin": kv.get("Operating Profit Margin (Quarter)"),
                "net_margin": kv.get("Net Profit Margin (Quarter)"),
                "revenue_ttm": kv.get("Revenue (TTM)"),
                "operating_cash_flow_ttm": kv.get("Cash From Operations (TTM)"),
                "total_cash": kv.get("Cash (Quarter)"),
                "total_assets": kv.get("Total Assets (Quarter)"),
                "total_liabilities": kv.get("Total Liabilities (Quarter)"),
            }
    except Exception as exc:
        logger.exception("Failed fetching keystats for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
async def idx_get_dividends(ticker: str) -> Dict[str, Any]:
    """Fetch official corporate action dividend calendar and payment history from Stockbit.

    Args:
        ticker: 4-letter IDX stock code (e.g. 'SMSM', 'MYOR', 'BBCA').
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    headers = _get_stockbit_headers()
    if not headers:
        return {"status": "error", "error": "Stockbit token not configured in ~/.hermes/stockbit_token"}

    url = f"https://exodus.stockbit.com/corpaction/dividend?symbol={clean_ticker}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {"status": "error", "error": f"Stockbit returned HTTP {res.status_code}"}
            divs = res.json().get("data", {}).get("dividend", []) or []
            summary = []
            for d in divs[:10]:
                summary.append({
                    "cum_date": d.get("dividend_cumdate"),
                    "ex_date": d.get("dividend_exdate"),
                    "pay_date": d.get("dividend_paydate"),
                    "amount_idr": d.get("dividend_value"),
                })
            return {
                "status": "success",
                "ticker": clean_ticker,
                "history_count": len(divs),
                "recent_dividends": summary,
            }
    except Exception as exc:
        logger.exception("Failed fetching dividends for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
async def idx_get_insider_activity(ticker: str, limit: int = 10) -> Dict[str, Any]:
    """Fetch official insider disclosures (major shareholders, directors, commissioners trading) from Stockbit.

    Args:
        ticker: 4-letter IDX stock code (e.g. 'MYOR', 'SMSM', 'BBCA').
        limit: Number of disclosures to retrieve (default: 10).
    """
    clean_ticker = ticker.strip().upper().replace(".JK", "")
    headers = _get_stockbit_headers()
    if not headers:
        return {"status": "error", "error": "Stockbit token not configured in ~/.hermes/stockbit_token"}

    url = f"https://exodus.stockbit.com/insider/company/majorholder?symbol={clean_ticker}&limit={limit}"
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return {"status": "error", "error": f"Stockbit returned HTTP {res.status_code}"}
            movements = res.json().get("data", {}).get("movement", []) or []
            clean_moves = []
            for m in movements:
                clean_moves.append({
                    "date": m.get("date"),
                    "name": m.get("name"),
                    "badges": m.get("badges", []),
                    "action": m.get("action_type"),
                    "change": m.get("changes", {}).get("value"),
                    "price": m.get("price_formatted"),
                })
            return {
                "status": "success",
                "ticker": clean_ticker,
                "movements_count": len(movements),
                "disclosures": clean_moves,
            }
    except Exception as exc:
        logger.exception("Failed fetching insider activity for %s: %s", clean_ticker, exc)
        return {"status": "error", "ticker": clean_ticker, "error": str(exc)}


@mcp.tool()
async def idx_stockbit(action: str, ticker: str) -> Dict[str, Any]:
    """Unified single-entry gateway for all Stockbit intelligence endpoints.

    Args:
        action: One of 'orderbook', 'bandarmology', 'keystats', 'dividends', 'insider'.
        ticker: 4-letter IDX stock code (e.g. 'MYOR', 'SMSM', 'BBCA').
    """
    act = action.strip().lower()
    if act in ("orderbook", "l2", "depth"):
        return await idx_get_orderbook(ticker)
    elif act in ("bandarmology", "bandar", "broker", "broker_summary"):
        return await idx_get_bandarmology(ticker)
    elif act in ("keystats", "financials", "ratios", "fundamental"):
        return await idx_get_keystats(ticker)
    elif act in ("dividends", "dividend", "corpaction", "corporate_action"):
        return await idx_get_dividends(ticker)
    elif act in ("insider", "majorholder", "insider_activity"):
        return await idx_get_insider_activity(ticker)
    else:
        return {
            "status": "error",
            "error": f"Unknown action '{action}'. Valid actions: orderbook, bandarmology, keystats, dividends, insider."
        }


if __name__ == "__main__":
    mcp.run()
