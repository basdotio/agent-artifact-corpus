#!/usr/bin/env node
/**
 * 删除账单
 * 用法：./remove-bill.js <序号>
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
🦆 删除账单

用法：
  ./remove-bill.js <序号>

示例：
  ./remove-bill.js 1    # 删除第 1 个账单

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

function removeBill(index) {
  const data = loadData();
  const activeBills = data.bills.filter(b => b.status === 'active');
  
  if (index < 1 || index > activeBills.length) {
    console.error(`❌ 序号必须在 1-${activeBills.length} 之间`);
    process.exit(1);
  }
  
  const bill = activeBills[index - 1];
  bill.status = 'deleted';
  bill.deletedAt = new Date().toISOString();
  
  saveData(data);
  
  console.log(`✅ 已删除账单：${bill.name} (¥${bill.amount})`);
  
  sendWeixinMessage(`🗑️ 账单已删除

📋 ${bill.name}
💰 ¥${bill.amount}

不再提醒此账单～`);
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
  
  removeBill(index);
}

main();
