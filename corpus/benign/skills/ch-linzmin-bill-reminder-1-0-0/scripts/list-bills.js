#!/usr/bin/env node
/**
 * 查看账单列表
 * 用法：./list-bills.js [选项]
 */

const fs = require('fs');
const path = require('path');

const DATA_FILE = path.join(__dirname, '..', 'data', 'bills.json');

function printUsage() {
  console.log(`
🦆 查看账单列表

用法：
  ./list-bills.js [选项]

选项：
  --all       显示所有账单（包括已停用）
  --history   显示还款历史
  --help      显示帮助
`);
}

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    return { bills: [], paymentHistory: [] };
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function listBills(showAll = false, showHistory = false) {
  const data = loadData();
  
  if (showHistory) {
    console.log('\n📜 还款历史\n');
    console.log('='.repeat(60));
    
    if (data.paymentHistory.length === 0) {
      console.log('  (暂无还款记录)');
    } else {
      data.paymentHistory.slice(-10).reverse().forEach(record => {
        const bill = data.bills.find(b => b.id === record.billId);
        const billName = bill ? bill.name : '已删除';
        const date = new Date(record.paidAt).toLocaleDateString('zh-CN');
        console.log(`  ${date}  ${billName}  ¥${record.amount}  ${record.note || ''}`);
      });
    }
    console.log('');
    return;
  }
  
  console.log('\n📋 账单列表\n');
  console.log('='.repeat(60));
  
  let bills = data.bills;
  if (!showAll) {
    bills = bills.filter(b => b.status === 'active');
  }
  
  if (bills.length === 0) {
    console.log('  (暂无账单)');
    console.log('\n  添加账单：./add-bill.js <名称> <金额> <日期>');
    console.log('  示例：./add-bill.js "信用卡" 5000 15\n');
    return;
  }
  
  const cycleNames = { monthly: '月', weekly: '周', yearly: '年' };
  
  bills.forEach((bill, index) => {
    const daysUntilDue = calculateDaysUntilDue(bill.dueDay, bill.cycle);
    const statusIcon = daysUntilDue < 0 ? '🚨' : daysUntilDue <= 3 ? '⚠️' : '✅';
    
    console.log(`\n${index + 1}. ${statusIcon} ${bill.name}`);
    console.log(`   💰 ¥${bill.amount}`);
    console.log(`   📅 每${cycleNames[bill.cycle]}${bill.dueDay}日`);
    console.log(`   ⏰ 提前${bill.advanceDays}天提醒`);
    
    if (daysUntilDue > 0) {
      console.log(`   📆 还有${daysUntilDue}天到期`);
    } else if (daysUntilDue === 0) {
      console.log(`   📆 今天到期！`);
    } else {
      console.log(`   📆 已逾期${Math.abs(daysUntilDue)}天`);
    }
    
    if (bill.lastPaid) {
      const lastPaidDate = new Date(bill.lastPaid).toLocaleDateString('zh-CN');
      console.log(`   ✓ 上次还款：${lastPaidDate}`);
    }
  });
  
  console.log('\n' + '='.repeat(60));
  console.log(`总计：${bills.length}个账单`);
  console.log('\n操作提示:');
  console.log('  删除账单：./remove-bill.js <序号>');
  console.log('  标记还款：./mark-paid.js <序号>\n');
}

function calculateDaysUntilDue(dueDay, cycle) {
  const now = new Date();
  const today = now.getDate();
  
  if (cycle === 'monthly') {
    let days = dueDay - today;
    if (days < 0) {
      // 检查是否已经过了本月但还没到下月到期日
      const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
      days += daysInMonth;
    }
    return days;
  } else if (cycle === 'weekly') {
    const dayOfWeek = dueDay % 7;
    let days = dayOfWeek - now.getDay();
    if (days < 0) days += 7;
    return days;
  } else if (cycle === 'yearly') {
    const thisYear = new Date(now.getFullYear(), 0, dueDay);
    if (now < thisYear) {
      return Math.ceil((thisYear - now) / (1000 * 60 * 60 * 24));
    } else {
      const nextYear = new Date(now.getFullYear() + 1, 0, dueDay);
      return Math.ceil((nextYear - now) / (1000 * 60 * 60 * 24));
    }
  }
  
  return 0;
}

// 主程序
function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(0);
  }
  
  const showAll = args.includes('--all');
  const showHistory = args.includes('--history');
  
  listBills(showAll, showHistory);
}

main();
