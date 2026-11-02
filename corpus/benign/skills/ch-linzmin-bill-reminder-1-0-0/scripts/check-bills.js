#!/usr/bin/env node
/**
 * 检查账单到期情况并发送提醒
 * 用法：./check-bills.js（通常由 cron 每天运行）
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DATA_FILE = path.join(__dirname, '..', 'data', 'bills.json');
const LOG_FILE = path.join(__dirname, '..', 'bill-reminder.log');
const CHANNEL = process.env.WEIXIN_CHANNEL || 'openclaw-weixin';
const ACCOUNT = process.env.WEIXIN_ACCOUNT || 'd72d5b576646-im-bot';

function log(message) {
  const timestamp = new Date().toLocaleString('zh-CN');
  const logLine = `[${timestamp}] ${message}\n`;
  console.log(logLine);
  fs.appendFileSync(LOG_FILE, logLine);
}

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    return { bills: [], paymentHistory: [] };
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function sendWeixinMessage(userId, message) {
  const cmd = `openclaw message send \\
    --channel ${CHANNEL} \\
    --account ${ACCOUNT} \\
    --target ${userId} \\
    --message "${message.replace(/\n/g, '\\n')}"`;
  
  try {
    execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
    return true;
  } catch (error) {
    log(`发送微信失败：${error.message}`);
    return false;
  }
}

function calculateDaysUntilDue(dueDay, cycle) {
  const now = new Date();
  const today = now.getDate();
  
  if (cycle === 'monthly') {
    let days = dueDay - today;
    if (days < 0) {
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

function checkBills() {
  log('开始检查账单...');
  
  const data = loadData();
  const activeBills = data.bills.filter(b => b.status === 'active');
  
  if (activeBills.length === 0) {
    log('无活跃账单');
    return;
  }
  
  let reminderCount = 0;
  
  activeBills.forEach(bill => {
    const daysUntilDue = calculateDaysUntilDue(bill.dueDay, bill.cycle);
    const userId = bill.userId || process.env.WEIXIN_USER_ID || '[REDACTED_SECRET]';
    
    // 检查是否需要发送提醒
    let message = null;
    let reminderType = null;
    
    // 提前 N 天提醒
    if (daysUntilDue === bill.advanceDays && daysUntilDue > 0) {
      message = `⏰ 账单提醒

📋 ${bill.name}
💰 ¥${bill.amount}
📅 ${bill.dueDay}日到期

还有${daysUntilDue}天，别忘了哦～ 🦆`;
      reminderType = 'advance';
    }
    
    // 到期当天提醒
    if (daysUntilDue === 0) {
      message = `⚠️ 今天到期！

📋 ${bill.name}
💰 ¥${bill.amount}

今天最后期限，快还！🦆`;
      reminderType = 'due';
    }
    
    // 逾期提醒（前 3 天）
    if (daysUntilDue < 0 && Math.abs(daysUntilDue) <= 3) {
      const overdueDays = Math.abs(daysUntilDue);
      message = `🚨 已逾期！

📋 ${bill.name}
💰 ¥${bill.amount}
📅 逾期${overdueDays}天

赶紧还，要产生利息了！🦆`;
      reminderType = 'overdue';
    }
    
    // 发送提醒
    if (message) {
      // 检查是否已经发送过今天的提醒（避免重复）
      const today = new Date().toDateString();
      const lastReminderKey = `lastReminder_${reminderType}_${today}`;
      
      if (!bill[lastReminderKey]) {
        sendWeixinMessage(userId, message);
        bill[lastReminderKey] = true;
        reminderCount++;
        log(`发送${reminderType}提醒：${bill.name}`);
      }
    }
  });
  
  // 保存数据（清除旧的提醒标记）
  activeBills.forEach(bill => {
    const today = new Date().toDateString();
    Object.keys(bill).forEach(key => {
      if (key.startsWith('lastReminder_') && !key.includes(today)) {
        delete bill[key];
      }
    });
  });
  
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
  
  log(`检查完成，发送${reminderCount}个提醒`);
}

// 主程序
checkBills();
