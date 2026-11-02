#!/usr/bin/env node
/**
 * 生成日报脚本
 * 用法：./generate-report.js [选项]
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DATA_DIR = path.join(__dirname, '..', 'data');
const DATA_FILE = path.join(DATA_DIR, 'daily-data.json');
const REPORTS_DIR = path.join(__dirname, '..', 'reports');
const TEMPLATE_DIR = path.join(__dirname, '..', 'templates');

const CHANNEL = process.env.WEIXIN_CHANNEL || 'openclaw-weixin';
const ACCOUNT = process.env.WEIXIN_ACCOUNT || 'd72d5b576646-im-bot';
const USER_ID = process.env.WEIXIN_USER_ID || '[REDACTED_SECRET]';

function printUsage() {
  console.log(`
📊 生成日报脚本

用法：
  ./generate-report.js [选项]

选项：
  --template <name>   使用指定模板（simple/detailed/professional）
  --output <format>   输出格式（markdown/text/weixin）
  --save              保存到文件
  --send              发送微信
  --preview           预览（默认）
  --help              显示帮助
`);
}

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    console.error('❌ 未找到数据文件，请先运行 ./collect-data.js');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function loadTemplate(name) {
  const templateFile = path.join(TEMPLATE_DIR, `${name}.md`);
  
  if (!fs.existsSync(templateFile)) {
    // 返回默认模板
    return `# 工作日报 - {{date}}

## 📅 今日工作

{{calendar}}

## ✅ 完成情况

{{todo}}

## 📧 邮件处理

{{email}}

## 💡 今日总结

{{manual}}

## 🎯 明日计划

- [ ] 

---
生成时间：{{timestamp}}
`;
  }
  
  return fs.readFileSync(templateFile, 'utf8');
}

function generateReport(data, templateName = 'simple', outputFormat = 'markdown') {
  const template = loadTemplate(templateName);
  
  // 生成日历部分
  const calendarText = data.calendar.length > 0
    ? data.calendar.map(e => `- ${e.time} ${e.event}`).join('\n')
    : '- 无日程安排';
  
  // 生成待办部分
  const doneCount = data.todo.filter(t => t.status === 'done').length;
  const todoText = data.todo.length > 0
    ? data.todo.map(t => {
        const icon = t.status === 'done' ? '✅' : '⏳';
        return `- ${icon} ${t.task}`;
      }).join('\n')
    : '- 无待办事项';
  
  // 生成邮件部分
  const emailText = data.email.received > 0
    ? `收到：${data.email.received} 封\n发送：${data.email.sent} 封` + 
      (data.email.important.length > 0 ? `\n\n重要邮件：\n${data.email.important.map(m => `- ${m.from}: ${m.subject}`).join('\n')}` : '')
    : '- 无邮件';
  
  // 生成总结部分
  const manualText = data.manual || '- 无';
  
  // 替换模板变量
  let report = template
    .replace(/{{date}}/g, data.date)
    .replace(/{{calendar}}/g, calendarText)
    .replace(/{{todo}}/g, todoText)
    .replace(/{{email}}/g, emailText)
    .replace(/{{manual}}/g, manualText)
    .replace(/{{timestamp}}/g, new Date().toLocaleString('zh-CN'));
  
  // 根据输出格式调整
  if (outputFormat === 'text') {
    report = report.replace(/[#*`]/g, '');
  } else if (outputFormat === 'weixin') {
    // 微信格式简化
    report = `📊 工作日报 - ${data.date}

📅 今日工作
${calendarText}

✅ 完成情况 (${doneCount}/${data.todo.length})
${todoText}

📧 邮件处理
${emailText}

💡 今日总结
${manualText}

---
生成时间：${new Date().toLocaleString('zh-CN')}`;
  }
  
  return report;
}

function saveReport(report, date) {
  if (!fs.existsSync(REPORTS_DIR)) {
    fs.mkdirSync(REPORTS_DIR, { recursive: true });
  }
  
  const filename = `report-${date}.md`;
  const filepath = path.join(REPORTS_DIR, filename);
  fs.writeFileSync(filepath, report);
  
  console.log(`✅ 日报已保存：${filepath}`);
  return filepath;
}

function sendWeixin(report) {
  const message = report.replace(/\n/g, '\\n');
  const cmd = `openclaw message send \\
    --channel ${CHANNEL} \\
    --account ${ACCOUNT} \\
    --target ${USER_ID} \\
    --message "${message}"`;
  
  try {
    execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
    console.log('✅ 已发送微信');
    return true;
  } catch (error) {
    console.error('❌ 发送失败:', error.message);
    return false;
  }
}

// 主程序
function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(0);
  }
  
  // 解析参数
  const templateName = args.includes('--template') 
    ? args[args.indexOf('--template') + 1] 
    : 'simple';
  
  const outputFormat = args.includes('--output')
    ? args[args.indexOf('--output') + 1]
    : 'markdown';
  
  const shouldSave = args.includes('--save');
  const shouldSend = args.includes('--send');
  const shouldPreview = args.includes('--preview') || (!shouldSave && !shouldSend);
  
  // 加载数据
  const data = loadData();
  
  // 生成报告
  const report = generateReport(data, templateName, outputFormat);
  
  // 预览
  if (shouldPreview) {
    console.log('\n📊 生成的日报预览\n');
    console.log('='.repeat(50));
    console.log(report);
    console.log('='.repeat(50));
    console.log('');
  }
  
  // 保存
  if (shouldSave) {
    saveReport(report, data.date);
  }
  
  // 发送微信
  if (shouldSend) {
    sendWeixin(report);
  }
  
  console.log('💡 提示:');
  console.log('  保存：./generate-report.js --save');
  console.log('  发送微信：./generate-report.js --send');
  console.log('  更换模板：./generate-report.js --template detailed');
}

main();
