from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
import uuid
import requests
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np

# 设置路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(SCRIPT_DIR)

# 初始化Flask应用
app = Flask(__name__, 
            template_folder=os.path.join(SKILL_ROOT, 'templates'),
            static_folder=os.path.join(SKILL_ROOT, 'static'))
app.config['SECRET_KEY'] = 'cb-trading-bot-secret-2026'
app.config['DATABASE'] = os.path.join(SKILL_ROOT, 'data', 'trading.db')

# 测试模式：设置为False启用真实支付
TEST_MODE = False

# SkillPay 配置
SKILLPAY_API_KEY = ''
SKILL_ID = 'convertible-bond-trading-bot'
BILLING_URL = "https://skillpay.me/api/v1/billing"
HEADERS = {
    "X-API-Key": SKILLPAY_API_KEY, 
    "Content-Type": "application/json"
}

# 初始化数据库
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # 策略配置表
    c.execute('''CREATE TABLE IF NOT EXISTS config
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  sell_threshold_1 REAL DEFAULT 2.0,
                  sell_threshold_2 REAL DEFAULT 5.0,
                  sell_threshold_3 REAL DEFAULT 8.0,
                  buy_threshold REAL DEFAULT 1.0,
                  stop_loss REAL DEFAULT 5.0,
                  max_position REAL DEFAULT 15.0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 选股结果表
    c.execute('''CREATE TABLE IF NOT EXISTS selected_bonds
                 (id TEXT PRIMARY KEY,
                  user_id TEXT,
                  bond_code TEXT,
                  bond_name TEXT,
                  price REAL,
                  premium_rate REAL,
                  remaining_scale REAL,
                  remaining_term REAL,
                  score REAL,
                  selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 交易记录表
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id TEXT PRIMARY KEY,
                  user_id TEXT,
                  bond_code TEXT,
                  bond_name TEXT,
                  trade_type TEXT,
                  price REAL,
                  amount INTEGER,
                  profit REAL,
                  trade_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 回测结果表
    c.execute('''CREATE TABLE IF NOT EXISTS backtests
                 (id TEXT PRIMARY KEY,
                  user_id TEXT,
                  total_return REAL,
                  max_drawdown REAL,
                  win_rate REAL,
                  annual_return REAL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

# 止跌企稳选股逻辑
def select_bonds():
    # 模拟数据（实际对接akshare/tushare接口获取实时行情）
    mock_bonds = [
        {"code": "113011", "name": "光大转债", "price": 112.5, "premium_rate": 12.3, "remaining_scale": 24.5, "remaining_term": 1.2, "score": 92},
        {"code": "123018", "name": "东财转2", "price": 121.8, "premium_rate": 8.7, "remaining_scale": 12.3, "remaining_term": 0.8, "score": 87},
        {"code": "110059", "name": "浦发转债", "price": 106.2, "premium_rate": 22.5, "remaining_scale": 30.0, "remaining_term": 2.1, "score": 85},
        {"code": "123088", "name": "靖远转债", "price": 118.9, "premium_rate": 15.2, "remaining_scale": 2.8, "remaining_term": 1.5, "score": 83},
        {"code": "113596", "name": "法兰转债", "price": 125.3, "premium_rate": 7.8, "remaining_scale": 3.2, "remaining_term": 0.9, "score": 81}
    ]
    # 实际对接行情接口后的选股逻辑
    # 1. 获取全市场可转债列表和近10日行情数据
    # 2. 过滤价格≤130，溢价率≤30%，剩余规模≥2亿，剩余期限≥1年
    # 3. 筛选连续3日不创新低，站稳MA5，成交量缩量至下跌期30%
    # 4. 计算止跌企稳信号得分，按得分排序返回
    return mock_bonds

# 高抛低吸策略执行
def run_strategy(bond_code, current_price, position):
    signals = []
    avg_cost = position.get('avg_cost', 0)
    hold_amount = position.get('amount', 0)
    
    if hold_amount == 0:
        # 空仓，符合建仓条件则买入
        if current_price >= avg_cost * 1.01:
            signals.append({"type": "buy", "amount": 10, "price": current_price, "reason": "启动信号，建仓1/3"})
    else:
        # 持仓，执行高抛
        profit_rate = (current_price - avg_cost) / avg_cost * 100
        if profit_rate >= 8.0:
            signals.append({"type": "sell", "amount": hold_amount, "price": current_price, "reason": "上涨8%，清仓止盈"})
        elif profit_rate >= 5.0 and hold_amount >= 20:
            signals.append({"type": "sell", "amount": 10, "price": current_price, "reason": "上涨5%，卖出1/3"})
        elif profit_rate >= 2.0 and hold_amount >= 10:
            signals.append({"type": "sell", "amount": 10, "price": current_price, "reason": "上涨2%，卖出1/3"})
        # 执行低吸
        elif profit_rate <= -1.0 and hold_amount < 30:
            signals.append({"type": "buy", "amount": 10, "price": current_price, "reason": "下跌1%，接回仓位"})
        # 止损
        elif profit_rate <= -5.0:
            signals.append({"type": "sell", "amount": hold_amount, "price": current_price, "reason": "亏损5%，止损离场"})
    
    return signals

# 策略回测
def backtest_strategy(start_date, end_date):
    # 模拟回测结果（实际对接历史行情数据计算）
    return {
        "total_return": 32.5,
        "max_drawdown": 7.8,
        "win_rate": 82.3,
        "annual_return": 35.2,
        "trade_count": 128,
        "profit_factor": 2.3
    }

# SkillPay 支付相关函数
def charge_user(user_id: str):
    if TEST_MODE:
        return {"ok": True, "balance": 1000}
    try:
        resp = requests.post(f"{BILLING_URL}/charge", headers=HEADERS, json={
            "user_id": user_id, "skill_id": SKILL_ID, "amount": 0.01,
        }, timeout=10)
        data = resp.json()
        if data.get("success"):
            return {"ok": True, "balance": data.get("balance")}
        return {
            "ok": False, 
            "balance": data.get("balance"), 
            "payment_url": data.get("payment_url")
        }
    except Exception as e:
        print(f"扣费失败: {e}")
        return {"ok": False, "error": str(e)}

# 验证支付中间件
@app.before_request
def check_payment():
    if not TEST_MODE and request.endpoint not in ['index', 'pay', 'static'] and not session.get('payment_verified'):
        user_id = session.get('user_id', str(uuid.uuid4()))
        session['user_id'] = user_id
        charge_result = charge_user(user_id)
        if not charge_result.get('ok'):
            payment_url = charge_result.get('payment_url')
            return render_template('payment_required.html', payment_url=payment_url, test_mode=TEST_MODE) if payment_url else '余额不足，请先充值', 402
        session['payment_verified'] = True

# 路由
@app.route('/')
def index():
    if TEST_MODE and request.args.get('test_payment') == 'success':
        session['payment_verified'] = True
    return render_template('index.html')

@app.route('/pay')
def pay():
    user_id = session.get('user_id', str(uuid.uuid4()))
    session['user_id'] = user_id
    if TEST_MODE:
        return redirect(url_for('index', test_payment='success'))
    try:
        resp = requests.post(f"{BILLING_URL}/payment-link", headers=HEADERS, json={
            "user_id": user_id, "amount": 0.01,
        }, timeout=10)
        payment_url = resp.json().get("payment_url")
        return redirect(payment_url) if payment_url else '获取支付链接失败', 500
    except Exception as e:
        print(f"获取支付链接失败: {e}")
        return '获取支付链接失败', 500

@app.route('/api/select_bonds', methods=['POST'])
def api_select_bonds():
    user_id = session.get('user_id', str(uuid.uuid4()))
    bonds = select_bonds()
    # 保存到数据库
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    for bond in bonds:
        bond_id = str(uuid.uuid4())
        c.execute('''INSERT INTO selected_bonds (id, user_id, bond_code, bond_name, price, premium_rate, remaining_scale, remaining_term, score)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (bond_id, user_id, bond['code'], bond['name'], bond['price'], bond['premium_rate'], bond['remaining_scale'], bond['remaining_term'], bond['score']))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "bonds": bonds})

@app.route('/api/run_strategy', methods=['POST'])
def api_run_strategy():
    data = request.get_json()
    bond_code = data.get('bond_code')
    current_price = float(data.get('current_price'))
    position = data.get('position', {})
    signals = run_strategy(bond_code, current_price, position)
    return jsonify({"success": True, "signals": signals})

@app.route('/api/backtest', methods=['POST'])
def api_backtest():
    data = request.get_json()
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    result = backtest_strategy(start_date, end_date)
    # 保存回测结果
    user_id = session.get('user_id', str(uuid.uuid4()))
    test_id = str(uuid.uuid4())
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''INSERT INTO backtests (id, user_id, total_return, max_drawdown, win_rate, annual_return)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (test_id, user_id, result['total_return'], result['max_drawdown'], result['win_rate'], result['annual_return']))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "result": result})

@app.route('/api/save_config', methods=['POST'])
def api_save_config():
    data = request.get_json()
    user_id = session.get('user_id', str(uuid.uuid4()))
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''DELETE FROM config WHERE user_id = ?''', (user_id,))
    c.execute('''INSERT INTO config (user_id, sell_threshold_1, sell_threshold_2, sell_threshold_3, buy_threshold, stop_loss, max_position)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, data['sell1'], data['sell2'], data['sell3'], data['buy'], data['stop_loss'], data['position']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/get_trades', methods=['GET'])
def api_get_trades():
    user_id = session.get('user_id', str(uuid.uuid4()))
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM trades WHERE user_id = ? ORDER BY trade_time DESC LIMIT 50', (user_id,))
    trades = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"success": True, "trades": trades})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5004, debug=True)
