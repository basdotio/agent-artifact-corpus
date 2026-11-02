import os, sys
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from skillpay import billing_check
    _ok = billing_check(
        user_id=os.environ.get("SKILLPAY_USER_ID", "anonymous_user"),
        amount=0.001
    )
    if not _ok:
        print("[SkillPay] ❌ 余额不足，退出。充值：https://skillpay.me")
        sys.exit(1)
except Exception as _e:
    print(f"[SkillPay] ⚠️  跳过（演示模式）: {_e}")


#!/usr/bin/env python3
"""
每日收益记录与追踪脚本
用法: python3 track_income.py --date 2026-03-25 --platform 阿里众包 --amount 85 --note "数据标注任务"
"""
import json
import sys
import os
from datetime import datetime

TRACK_FILE = os.path.expanduser("~/.openclaw/profit_tracker.json")

def load_data():
    if os.path.exists(TRACK_FILE):
        with open(TRACK_FILE, "r") as f:
            return json.load(f)
    return {"records": [], "monthly_goals": {}}

def save_data(data):
    with open(TRACK_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_record(date, platform, amount, note=""):
    data = load_data()
    data["records"].append({
        "date": date,
        "platform": platform,
        "amount": float(amount),
        "note": note,
        "created_at": datetime.now().isoformat()
    })
    save_data(data)
    print(f"✅ 记录已添加：{platform} +¥{amount}")

def show_summary(month=None):
    data = load_data()
    records = data.get("records", [])
    
    if not records:
        print("📊 暂无收益记录")
        return
    
    if month:
        records = [r for r in records if r["date"].startswith(month)]
    
    total = sum(r["amount"] for r in records)
    by_platform = {}
    for r in records:
        by_platform.setdefault(r["platform"], 0)
        by_platform[r["platform"]] += r["amount"]
    
    print(f"\n📊 收益汇总 {'(' + month + ')' if month else '(全部)'}")
    print(f"总收益：¥{total:.2f}")
    print(f"记录数：{len(records)}")
    print("\n按平台分布：")
    for platform, amount in sorted(by_platform.items(), key=lambda x: -x[1]):
        print(f"  {platform}: ¥{amount:.2f}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: track_income.py add <金额> <平台> [备注]")
        print("      track_income.py summary [月份如2026-03]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "add":
        if len(sys.argv) < 4:
            print("错误：缺少参数")
            sys.exit(1)
        amount = sys.argv[2]
        platform = sys.argv[3]
        note = sys.argv[4] if len(sys.argv) > 4 else ""
        date = datetime.now().strftime("%Y-%m-%d")
        add_record(date, platform, amount, note)
    elif cmd == "summary":
        month = sys.argv[2] if len(sys.argv) > 2 else None
        show_summary(month)
    else:
        print(f"未知命令: {cmd}")
