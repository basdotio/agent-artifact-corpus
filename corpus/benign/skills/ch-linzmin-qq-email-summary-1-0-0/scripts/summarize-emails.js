#!/usr/bin/env node
/**
 * 生成邮件摘要
 * 用法：./summarize-emails.js [选项]
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DATA_FILE = path.join(__dirname, '..', 'data', 'emails.json');
const REPORTS_DIR = path.join(__dirname, '..', 'reports');
const CONFIG_FILE = path.join(__dirname, '..', 'config', 'email-config.json');

const CHANNEL = process.env.WEIXIN_CHANNEL || 'openclaw-weixin';
const ACCOUNT = process.env.WEIXIN_ACCOUNT || 'd72d5b576646-im-bot';
const USER_ID = process.env.WEIXIN_USER_ID || '[REDACTED_SECRET]';

function loadEmails() {
  if (!fs.existsSync(DATA_FILE)) {
    console.error('❌ 未找到邮件数据，请先运行 ./scripts/fetch-emails.js');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    return { summary: { aiProvider: 'modelstudio' } };
  }
  return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
}

function generateSummary(emails) {
  const date = new Date().toLocaleDateString('zh-CN');
  
  // 分类统计
  const byCategory = {
    important: emails.filter(e => e.category === 'important'),
    normal: emails.filter(e => e.category === 'normal'),
    promo: emails.filter(e => e.category === 'promo'),
    spam: emails.filter(e => e.category === 'spam')
  };
  
  // 生成摘要文本
  let summary = `📧 邮件摘要 - ${date}

📊 总计：${emails.length} 封

`;
  
  // 重要邮件
  if (byCategory.important.length > 0) {
    summary += `📌 重要邮件 (${byCategory.important.length})\n`;
    byCategory.important.forEach((email, i) => {
      const from = email.from.split('<')[0].trim();
      summary += `${i + 1}. ${from}: ${email.subject}\n`;
    });
    summary += '\n';
  }
  
  // 普通邮件
  if (byCategory.normal.length > 0) {
    summary += `📝 普通邮件 (${byCategory.normal.length})\n`;
    byCategory.normal.slice(0, 10).forEach((email, i) => {
      summary += `${i + 1}. ${email.from.split('<')[0].trim()}: ${email.subject}\n`;
    });
    if (byCategory.normal.length > 10) {
      summary += `   ... 还有 ${byCategory.normal.length - 10} 封\n`;
    }
    summary += '\n';
  }
  
  // 推广/垃圾邮件
  if (byCategory.promo.length > 0 || byCategory.spam.length > 0) {
    summary += `📢 推广/垃圾邮件 (${byCategory.promo.length + byCategory.spam.length}) - 已自动过滤\n\n`;
  }
  
  // AI 智能总结（如果有重要邮件）
  if (byCategory.important.length > 0) {
    summary += `💡 今日重点关注：
- 有 ${byCategory.important.length} 封重要邮件需要处理
- 建议优先回复紧急邮件
- 注意会议安排和报告截止日期

`;
  }
  
  summary += `---
生成时间：${new Date().toLocaleString('zh-CN')}`;
  
  return summary;
}

function sendWeixin(message) {
  // 简化消息（微信有长度限制）
  const lines = message.split('\n');
  const simplified = lines.slice(0, 15).join('\n');
  const note = lines.length > 15 ? '\n\n... 完整摘要已保存到报告文件' : '';
  const finalMessage = simplified + note;
  
  // 使用单引号避免引号转义问题
  const cmd = `openclaw message send --channel '${CHANNEL}' --account '${ACCOUNT}' --target '${USER_ID}' --message '${finalMessage.replace(/'/g, "'\"'\"'")}'`;
  
  try {
    execSync(cmd, { encoding: 'utf8', stdio: 'pipe' });
    console.log('✅ 已发送微信');
    return true;
  } catch (error) {
    console.error('❌ 发送失败:', error.message);
    console.log('\n💡 摘要已保存到报告文件，可手动查看');
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);
  
  console.log('🚀 开始生成邮件摘要...\n');
  
  const data = loadEmails();
  const emails = data.emails;
  
  console.log(`📬 共有 ${emails.length} 封邮件\n`);
  
  const summary = generateSummary(emails);
  
  // 预览
  console.log('📊 邮件摘要预览：');
  console.log('='.repeat(50));
  console.log(summary);
  console.log('='.repeat(50));
  console.log('');
  
  // 保存
  const shouldSave = args.includes('--save');
  if (shouldSave) {
    if (!fs.existsSync(REPORTS_DIR)) {
      fs.mkdirSync(REPORTS_DIR, { recursive: true });
    }
    
    const today = new Date().toISOString().split('T')[0];
    const filename = `email-summary-${today}.md`;
    const filepath = path.join(REPORTS_DIR, filename);
    
    fs.writeFileSync(filepath, summary);
    console.log(`✅ 摘要已保存：${filepath}`);
  }
  
  // 发送微信
  const shouldSend = args.includes('--send');
  if (shouldSend) {
    sendWeixin(summary);
  }
  
  console.log('');
  console.log('💡 提示:');
  console.log('  保存：./summarize-emails.js --save');
  console.log('  发送微信：./summarize-emails.js --send');
  console.log('  获取新邮件：./fetch-emails.js');
}

main();
