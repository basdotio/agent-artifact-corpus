#!/usr/bin/env node
/**
 * 添加账单提醒
 * 用法：./add-bill.js <名称> <金额> <日期> [周期] [提前天数]
 * 示例：./add-bill.js "信用卡" 5000 15 monthly 3
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// 配置
const DATA_DIR = path.join(__dirname, '..', 'data');
const DATA_FILE = path.join(DATA_DIR, 'bills.json');
const CHANNEL = process.env.WEIXIN_CHANNEL || 'openclaw-weixin';
const ACCOUNT = process.env.WEIXIN_ACCOUNT || 'd72d5b576646-im-bot';
const USER_ID = process.env.WEIXIN_USER_ID || '[REDACTED_SECRET]';

function printUsage() {
  console.log(`
🦆 添加账单提醒

用法：
  ./add-bill.js <名称> <金额> <日期> [周期] [提前天数]

参数：
  名称        账单名称（如：信用卡、花呗、房租）
  金额        账单金额（元）
  日期        每月几号（1-31）
  周期        周期类型：monthly（默认）、weekly、yearly
  提前天数    提前几天提醒（默认 3 天）

示例：
  ./add-bill.js "信用卡" 5000 15
  ./add-bill.js "花呗" 2000 8 monthly 1
  ./add-bill.js "房租" 3000 1 monthly 5
`);
}

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    return { bills: [], paymentHistory: [] };
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function saveData(data) {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
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
    console.error('发送微信失败:', error.message);
    return false;
  }
}

function addBill(name, amount, dueDay, cycle = 'monthly', advanceDays = 3) {
  // 参数验证
  if (!name || !amount || !dueDay) {
    console.error('❌ 缺少必需参数');
    printUsage();
    process.exit(1);
  }
  
  amount = parseFloat(amount);
  dueDay = parseInt(dueDay);
  advanceDays = parseInt(advanceDays) || 3;
  
  if (isNaN(amount) || amount <= 0) {
    console.error('❌ 金额必须是正数');
    process.exit(1);
  }
  
  if (isNaN(dueDay) || dueDay < 1 || dueDay > 31) {
    console.error('❌ 日期必须是 1-31 之间的数字');
    process.exit(1);
  }
  
  if (advanceDays < 0 || advanceDays > 30) {
    console.error('❌ 提前天数必须是 0-30 之间的数字');
    process.exit(1);
  }
  
  const validCycles = ['monthly', 'weekly', 'yearly'];
  if (!validCycles.includes(cycle)) {
    console.error(`❌ 周期必须是 ${validCycles.join(', ')} 之一`);
    process.exit(1);
  }
  
  // 加载数据
  const data = loadData();
  
  // 创建账单
  const bill = {
    id: `bill_${Date.now()}`,
    name,
    amount,
    dueDay,
    cycle,
    advanceDays,
    userId: USER_ID,
    createdAt: new Date().toISOString(),
    lastPaid: null,
    nextDue: calculateNextDue(dueDay, cycle),
    status: 'active'
  };
  
  // 添加账单
  data.bills.push(bill);
  saveData(data);
  
  // 输出结果
  const cycleNames = { monthly: '每月', weekly: '每周', yearly: '每年' };
  console.log(`✅ 已添加账单提醒：`);
  console.log(`   📋 ${name}`);
  console.log(`   💰 ¥${amount}`);
  console.log(`   📅 ${cycleNames[cycle]}${dueDay}日`);
  console.log(`   ⏰ 提前${advanceDays}天提醒`);
  
  // 发送微信确认
  const message = `✅ 账单提醒已设置！

📋 ${name}
💰 ¥${amount}
📅 ${cycleNames[cycle]}${dueDay}日
⏰ 提前${advanceDays}天提醒

到期前我会微信提醒你～ 🦆`;
  
  sendWeixinMessage(message);
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
    const dayOfWeek = dueDay % 7;
    next.setDate(next.getDate() + ((dayOfWeek - next.getDay() + 7) % 7));
  } else if (cycle === 'yearly') {
    next.setMonth(0, dueDay); // 1 月 dueDay 日
    if (next <= now) {
      next.setFullYear(next.getFullYear() + 1);
    }
  }
  
  return next.toISOString();
}

// 主程序
function main() {
  const args = process.argv.slice(2);
  
  if (args.length < 3 || args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(args.includes('-h') || args.includes('--help') ? 0 : 1);
  }
  
  const [name, amount, dueDay, cycle, advanceDays] = args;
  addBill(name, amount, dueDay, cycle, advanceDays);
}

main();
