#!/usr/bin/env node
/**
 * 标记账单已还款
 * 用法：./mark-paid.js <序号> [备注]
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DATA_FILE = path.join(__dirname, '..', 'data', 'bills.json');
const CHANNEL = process.env.WEIXIN_CHANNEL || 'openclaw-weixin';
const ACCOUNT = process.env.WEIXIN_ACCOUNT || 'd72d5b576646-im-bot';
const USER_ID = process.env.WEIXIN_USER_ID || '[REDACTED_SECRET]';

function printUsage() {
  console.log(`
🦆 标记账单已还款

用法：
  ./mark-paid.js <序号> [备注]

示例：
  ./mark-paid.js 1              # 标记第 1 个账单已还
  ./mark-paid.js 2 "已还清"     # 添加备注

提示：
  先用 ./list-bills.js 查看账单列表和序号
`);
}

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    return { bills: [], paymentHistory: [] };
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function saveData(data) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

function sendWeixinMessage(message) {
  const cmd = `openclaw message send \\
    --channel ${CHANNEL} \\
    --account ${ACCOUNT} \\
    --target ${USER_ID} \\
    --message "${message.replace(/\n/g, '\\n')}"`;
  
  try {
    execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
    return true;
  } catch (error) {
    return false;
  }
}

function calculateNextDue(dueDay, cycle) {
  const now = new Date();
  const next = new Date(now);
  
  if (cycle === 'monthly') {
    next.setDate(dueDay);
    if (next <= now) {
      next.setMonth(next.getMonth() + 1);
    }
  } else if (cycle === 'weekly') {
    next.setDate(next.getDate() + 7);
  } else if (cycle === 'yearly') {
    next.setFullYear(next.getFullYear() + 1);
  }
  
  return next;
}

function markPaid(index, note = '') {
  const data = loadData();
  const activeBills = data.bills.filter(b => b.status === 'active');
  
  if (index < 1 || index > activeBills.length) {
    console.error(`❌ 序号必须在 1-${activeBills.length} 之间`);
    process.exit(1);
  }
  
  const bill = activeBills[index - 1];
  const paidAt = new Date().toISOString();
  
  // 更新账单
  bill.lastPaid = paidAt;
  bill.nextDue = calculateNextDue(bill.dueDay, bill.cycle).toISOString();
  
  // 添加还款记录
  data.paymentHistory.push({
    billId: bill.id,
    paidAt,
    amount: bill.amount,
    note
  });
  
  saveData(data);
  
  const cycleNames = { monthly: '月', weekly: '周', yearly: '年' };
  const nextDue = new Date(bill.nextDue);
  const nextDueStr = `${nextDue.getMonth() + 1}月${nextDue.getDate()}日`;
  
  console.log(`✅ 已记录还款：${bill.name} (¥${bill.amount})`);
  console.log(`   下次到期：${nextDueStr}`);
  
  sendWeixinMessage(`✅ 已记录还款！

📋 ${bill.name}
💰 ¥${bill.amount}
📅 下次到期：${nextDueStr}

继续保持良好的信用记录～ 🦆`);
}

// 主程序
function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 1 || args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(args.includes('-h') || args.includes('--help') ? 0 : 1);
  }
  
  const index = parseInt(args[0]);
  if (isNaN(index)) {
    console.error('❌ 序号必须是数字');
    printUsage();
    process.exit(1);
  }
  
  const note = args.slice(1).join(' ');
  markPaid(index, note);
}

main();
