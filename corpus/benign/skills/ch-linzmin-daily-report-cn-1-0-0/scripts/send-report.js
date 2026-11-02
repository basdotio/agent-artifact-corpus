#!/usr/bin/env node
/**
 * 发送日报到微信
 * 用法：./send-report.js [日期]
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const REPORTS_DIR = path.join(__dirname, '..', 'reports');
const DATA_DIR = path.join(__dirname, '..', 'data');
const DATA_FILE = path.join(DATA_DIR, 'daily-data.json');

const CHANNEL = process.env.WEIXIN_CHANNEL || 'openclaw-weixin';
const ACCOUNT = process.env.WEIXIN_ACCOUNT || 'd72d5b576646-im-bot';
const USER_ID = process.env.WEIXIN_USER_ID || '[REDACTED_SECRET]';

function printUsage() {
  console.log(`
📤 发送日报到微信

用法：
  ./send-report.js [日期]

示例：
  ./send-report.js              # 发送今日日报
  ./send-report.js 2026-03-26   # 发送指定日期日报
`);
}

function getToday() {
  return new Date().toISOString().split('T')[0];
}

function sendWeixin(report, date) {
  const message = report.replace(/\n/g, '\\n');
  const cmd = `openclaw message send \\
    --channel ${CHANNEL} \\
    --account ${ACCOUNT} \\
    --target ${USER_ID} \\
    --message "📊 工作日报 - ${date}\\n\\n${message}"`;
  
  try {
    execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
    console.log('✅ 已发送微信');
    return true;
  } catch (error) {
    console.error('❌ 发送失败:', error.message);
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(0);
  }
  
  const date = args[0] || getToday();
  const reportFile = path.join(REPORTS_DIR, `report-${date}.md`);
  
  // 尝试从文件读取
  if (fs.existsSync(reportFile)) {
    const report = fs.readFileSync(reportFile, 'utf8');
    sendWeixin(report, date);
    return;
  }
  
  // 否则从数据文件生成
  if (!fs.existsSync(DATA_FILE)) {
    console.error('❌ 未找到数据文件，请先运行 ./collect-data.js');
    process.exit(1);
  }
  
  const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  
  if (data.date !== date) {
    console.error(`❌ 数据文件日期不匹配，当前数据是 ${data.date}`);
    process.exit(1);
  }
  
  // 生成微信格式报告
  const calendarText = data.calendar.length > 0
    ? data.calendar.map(e => `📅 ${e.time} ${e.event}`).join('\n')
    : '无日程安排';
  
  const doneCount = data.todo.filter(t => t.status === 'done').length;
  const todoText = data.todo.length > 0
    ? data.todo.map(t => {
        const icon = t.status === 'done' ? '✅' : '⏳';
        return `${icon} ${t.task}`;
      }).join('\n')
    : '无待办事项';
  
  const emailText = `收到：${data.email.received} 封\n发送：${data.email.sent} 封`;
  
  const manualText = data.manual || '无';
  
  const report = `📊 工作日报 - ${date}

📅 今日工作
${calendarText}

✅ 完成情况 (${doneCount}/${data.todo.length})
${todoText}

📧 邮件处理
${emailText}

💡 今日总结
${manualText}

🎯 明日计划
- [ ] 

---
生成时间：${new Date().toLocaleString('zh-CN')}`;
  
  sendWeixin(report, date);
}

main();
