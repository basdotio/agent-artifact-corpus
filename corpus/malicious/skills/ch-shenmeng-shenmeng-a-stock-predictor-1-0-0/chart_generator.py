#!/usr/bin/env python3
"""
股票图表生成器
生成走势图和技术指标可视化
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta


def generate_stock_chart(predictions, output_path='/tmp/stock_chart.png'):
    """
    生成股票走势图
    
    Args:
        predictions: List[StockPrediction] 预测结果列表
        output_path: 输出图片路径
    """
    n = len(predictions)
    fig, axes = plt.subplots(n, 2, figsize=(14, 5*n))
    
    if n == 1:
        axes = axes.reshape(1, 2)
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    for idx, (pred, color) in enumerate(zip(predictions, colors)):
        # 模拟5日历史数据
        dates = [datetime.now() - timedelta(days=i) for i in range(4, -1, -1)]
        
        # 基于预测价格推算历史
        atr = pred.close * 0.02  # 模拟ATR
        prices = [
            pred.ma - atr * 2,
            pred.ma - atr,
            pred.ma,
            (pred.close + pred.ma) / 2,
            pred.close
        ]
        
        # 左图：价格走势
        ax1 = axes[idx, 0]
        ax1.plot(dates, prices, 'o-', color=color, linewidth=2, markersize=8, label='Close')
        ax1.axhline(y=pred.ma, color='orange', linestyle='--', alpha=0.7, label=f'MA: {pred.ma:.2f}')
        ax1.axhline(y=pred.boll, color='purple', linestyle=':', alpha=0.7, label=f'BOLL: {pred.boll:.2f}')
        
        # 预测点
        tomorrow = datetime.now() + timedelta(days=1)
        ax1.plot([dates[-1], tomorrow], [pred.close, pred.pred_price], 
                 '--', color='red', linewidth=2, alpha=0.7, label='Prediction')
        ax1.scatter([tomorrow], [pred.pred_price], color='red', s=150, zorder=5, marker='*')
        
        change_str = f"+{pred.change:.2f}%" if pred.change > 0 else f"{pred.change:.2f}%"
        ax1.set_title(f'{pred.name} ({pred.code})\nToday: {pred.close:.2f} ({change_str}) | Pred: {pred.pred_price:.2f}', 
                      fontsize=11, fontweight='bold')
        ax1.set_ylabel('Price (CNY)', fontsize=10)
        ax1.legend(loc='best', fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        # 右图：技术指标
        ax2 = axes[idx, 1]
        
        categories = ['KDJ', 'RSI', 'CCI', 'MACD', 'Trend']
        cci_norm = min(100, max(0, (pred.rsi - 50) * 2 + 50))  # 简化CCI
        macd_norm = min(100, max(0, (pred.macd + 2) * 25))
        trend_score = pred.prob_up
        
        values = [min(100, pred.kdj), pred.rsi, cci_norm, macd_norm, trend_score]
        
        bars = ax2.bar(categories, values, color=color, alpha=0.7, edgecolor='black')
        ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax2.axhline(y=70, color='red', linestyle='--', alpha=0.3, label='Overbought')
        ax2.axhline(y=30, color='green', linestyle='--', alpha=0.3, label='Oversold')
        
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9)
        
        ax2.set_ylim(0, 100)
        ax2.set_title(f'Technical Indicators | {pred.trend} (Up: {pred.prob_up}%)', 
                      fontsize=11, fontweight='bold')
        ax2.set_ylabel('Value', fontsize=10)
        ax2.legend(loc='upper right', fontsize=8)
        ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    print(f"📉 图表已保存: {output_path}")
    return output_path


if __name__ == '__main__':
    # 测试
    from stock_predictor import AStockPredictor
    
    predictor = AStockPredictor()
    predictions = predictor.predict(['000001', '600519'])
    generate_stock_chart(predictions)
