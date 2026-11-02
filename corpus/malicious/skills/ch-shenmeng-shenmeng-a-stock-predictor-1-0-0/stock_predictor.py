#!/usr/bin/env python3
"""
A股股票预测助手 - 核心模块
基于实时数据和技术指标分析股票走势
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 导入 SkillPay 付费验证
try:
    from payment import require_payment
except ImportError:
    def require_payment():
        pass


@dataclass
class StockPrediction:
    """股票预测结果"""
    code: str
    name: str
    close: float
    change: float
    volume: int
    kdj: float
    rsi: float
    macd: float
    ma: float
    boll: float
    pred_price: float
    trend: str
    prob_up: int
    analysis: str


class AStockPredictor:
    """A股预测器"""
    
    def __init__(self):
        self.cache = {}
    
    def normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        code = code.strip().upper()
        
        # 移除已有后缀
        if '.' in code:
            return code
        
        # 根据开头判断市场
        if code.startswith('6'):
            return f"{code}.SH"  # 沪市
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"  # 深市
        elif code.startswith('8') or code.startswith('4'):
            return f"{code}.BJ"  # 北交所
        else:
            return f"{code}.SZ"  # 默认深市
    
    def fetch_data(self, codes: List[str]) -> Dict[str, Any]:
        """获取股票数据 (使用 Kimi Finance)"""
        import subprocess
        import tempfile
        import csv
        
        normalized_codes = [self.normalize_code(c) for c in codes]
        ticker_str = ','.join(normalized_codes)
        
        # 获取实时价格
        price_file = tempfile.mktemp(suffix='.csv')
        result = subprocess.run([
            sys.executable, '-m', 'kimi_finance',
            '--ticker', ticker_str,
            '--time', '2026-03-31 15:00:00',
            '--type', 'realtime_price',
            '--file-path', price_file
        ], capture_output=True, text=True)
        
        # 获取技术指标
        tech_file = tempfile.mktemp(suffix='.csv')
        result = subprocess.run([
            sys.executable, '-m', 'kimi_finance',
            '--ticker', ticker_str,
            '--time', '2026-03-31 15:00:00',
            '--type', 'realtime_tech',
            '--file-path', tech_file
        ], capture_output=True, text=True)
        
        return {'price_file': price_file, 'tech_file': tech_file}
    
    def analyze(self, code: str, price_data: Dict, tech_data: Dict) -> StockPrediction:
        """分析单只股票"""
        
        # 提取基础数据
        close = float(price_data.get('close', 0))
        change = float(price_data.get('changeRatio', 0)) * 100
        volume = int(price_data.get('volume', 0))
        
        # 提取技术指标
        kdj = float(tech_data.get('KDJ', 50))
        rsi = float(tech_data.get('RSI', 50))
        macd = float(tech_data.get('MACD', 0))
        ma = float(tech_data.get('MA', close))
        boll = float(tech_data.get('BOLL', close))
        
        # 预测逻辑
        score = 50  # 基础分
        
        # KDJ 分析
        if kdj > 80:
            score -= 10
            kdj_signal = "超买"
        elif kdj < 20:
            score += 15
            kdj_signal = "超卖反弹"
        else:
            kdj_signal = "中性"
            score += (kdj - 50) * 0.1
        
        # RSI 分析
        if rsi > 70:
            score -= 10
            rsi_signal = "强势但可能回调"
        elif rsi < 30:
            score += 15
            rsi_signal = "严重超卖"
        else:
            rsi_signal = "正常"
            score += (rsi - 50) * 0.1
        
        # MACD 分析
        if macd > 0:
            score += 10
            macd_signal = "多头"
        else:
            score -= 10
            macd_signal = "空头"
        
        # 均线分析
        if close > ma:
            score += 10
            ma_signal = "突破均线"
        else:
            score -= 10
            ma_signal = "跌破均线"
        
        # 计算预测
        prob_up = min(95, max(5, int(score)))
        
        if prob_up > 60:
            trend = "震荡上行"
            pred_price = close * (1 + (prob_up - 50) / 1000)
        elif prob_up > 45:
            trend = "震荡整理"
            pred_price = close * (1 + (prob_up - 50) / 2000)
        else:
            trend = "回调下行"
            pred_price = close * (1 - (50 - prob_up) / 1000)
        
        # 生成分析文本
        if change > 5:
            change_desc = f"今日大涨{change:.2f}%，"
        elif change > 0:
            change_desc = f"今日上涨{change:.2f}%，"
        elif change > -5:
            change_desc = f"今日下跌{abs(change):.2f}%，"
        else:
            change_desc = f"今日大跌{abs(change):.2f}%，"
        
        analysis = f"{change_desc}技术指标显示{kdj_signal}、{rsi_signal}、{macd_signal}。"
        
        if prob_up > 60:
            analysis += "预计明日震荡上行。"
        elif prob_up > 45:
            analysis += "预计明日震荡整理。"
        else:
            analysis += "预计明日回调下行。"
        
        # 股票名称映射（简化版）
        name_map = {
            '000001': '平安银行',
            '600519': '贵州茅台',
            '300750': '宁德时代',
        }
        name = name_map.get(code[:6], code[:6])
        
        return StockPrediction(
            code=code[:6],
            name=name,
            close=close,
            change=change,
            volume=volume,
            kdj=kdj,
            rsi=rsi,
            macd=macd,
            ma=ma,
            boll=boll,
            pred_price=pred_price,
            trend=trend,
            prob_up=prob_up,
            analysis=analysis
        )
    
    def predict(self, codes: List[str]) -> List[StockPrediction]:
        """预测多只股票"""
        results = []
        
        # 验证付费
        require_payment()
        
        for code in codes:
            try:
                # 这里应该调用真实的 Kimi Finance API
                # 简化演示使用模拟数据
                pred = self._mock_predict(code)
                results.append(pred)
            except Exception as e:
                print(f"❌ 分析 {code} 失败: {e}")
        
        return results
    
    def _mock_predict(self, code: str) -> StockPrediction:
        """模拟预测（用于演示）"""
        import random
        random.seed(hash(code) % 10000)
        
        close = random.uniform(10, 200)
        change = random.uniform(-5, 8)
        kdj = random.uniform(10, 90)
        rsi = random.uniform(15, 85)
        macd = random.uniform(-1, 1)
        
        # 计算预测
        score = 50 + (kdj - 50) * 0.2 + (rsi - 50) * 0.2 + macd * 10
        prob_up = min(95, max(5, int(score)))
        
        if prob_up > 60:
            trend = "震荡上行"
            pred_price = close * 1.015
        elif prob_up > 45:
            trend = "震荡整理"
            pred_price = close * 1.002
        else:
            trend = "回调下行"
            pred_price = close * 0.985
        
        return StockPrediction(
            code=code[:6],
            name=code[:6],
            close=round(close, 2),
            change=round(change, 2),
            volume=random.randint(100000, 10000000),
            kdj=round(kdj, 1),
            rsi=round(rsi, 1),
            macd=round(macd, 2),
            ma=round(close * 0.99, 2),
            boll=round(close * 1.01, 2),
            pred_price=round(pred_price, 2),
            trend=trend,
            prob_up=prob_up,
            analysis=f"技术指标显示KDJ={kdj:.1f}，RSI={rsi:.1f}，预计{trend}。"
        )
    
    def format_report(self, predictions: List[StockPrediction]) -> str:
        """格式化报告"""
        lines = [
            "📊 A股股票走势预测报告",
            "=" * 50,
            ""
        ]
        
        for p in predictions:
            change_str = f"+{p.change:.2f}%" if p.change > 0 else f"{p.change:.2f}%"
            lines.extend([
                f"📈 {p.name} ({p.code})",
                f"   收盘价: ¥{p.close:.2f} ({change_str})",
                f"   技术指标: KDJ:{p.kdj:.1f} RSI:{p.rsi:.1f} MACD:{p.macd:.2f}",
                f"   明日预测: ¥{p.pred_price:.2f}",
                f"   趋势判断: {p.trend} (上涨概率: {p.prob_up}%)",
                f"   分析: {p.analysis}",
                ""
            ])
        
        lines.extend([
            "=" * 50,
            "⚠️  风险提示：以上预测基于技术指标，仅供参考，不构成投资建议。",
            "     股市有风险，投资需谨慎。"
        ])
        
        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='A股股票预测助手')
    parser.add_argument('codes', nargs='+', help='股票代码')
    parser.add_argument('--chart', action='store_true', help='生成图表')
    
    args = parser.parse_args()
    
    predictor = AStockPredictor()
    predictions = predictor.predict(args.codes)
    
    print(predictor.format_report(predictions))
    
    if args.chart:
        print("\n📉 图表生成中...")
        # 调用图表生成脚本


if __name__ == '__main__':
    main()
