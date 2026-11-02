#!/usr/bin/env node
/**
 * 获取邮件脚本（修复版）
 * 用法：./fetch-emails.js [选项]
 */

const Imap = require('imap');
const { simpleParser } = require('mailparser');
const fs = require('fs');
const path = require('path');

const CONFIG_FILE = path.join(__dirname, '..', 'config', 'email-config.json');
const DATA_DIR = path.join(__dirname, '..', 'data');
const DATA_FILE = path.join(DATA_DIR, 'emails.json');

function loadConfig() {
  if (!fs.existsSync(CONFIG_FILE)) {
    console.error('❌ 配置文件不存在，请先运行 ./scripts/setup-qq-email.js');
    process.exit(1);
  }
  return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
}

function saveEmails(emails) {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
  
  const data = {
    fetchedAt: new Date().toISOString(),
    count: emails.length,
    emails: emails
  };
  
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

function fetchEmails() {
  return new Promise((resolve, reject) => {
    const config = loadConfig();
    
    const imap = new Imap({
      user: config.email.address,
      [REDACTED_SECRET],
      host: config.email.imap.host,
      port: config.email.imap.port,
      tls: config.email.imap.tls,
      tlsOptions: { servername: config.email.imap.host }
    });
    
    const emails = [];
    let processedCount = 0;
    const maxEmails = config.summary?.maxEmails || 50;
    
    imap.once('ready', () => {
      imap.openBox('INBOX', false, (err, box) => {
        if (err) {
          reject(err);
          return;
        }
        
        console.log(`📬 邮箱中有 ${box.messages.total} 封邮件`);
        console.log(`📥 准备获取最近 ${maxEmails} 封...\n`);
        
        // 获取最近 N 封邮件
        const start = Math.max(1, box.messages.total - maxEmails + 1);
        const fetchRange = `${start}:*`;
        
        const f = imap.fetch(fetchRange, { 
          bodies: 'HEADER.FIELDS (FROM TO SUBJECT DATE)', 
          struct: true 
        });
        
        f.on('message', (msg, seqno) => {
          const emailData = {
            seqno,
            headers: {}
          };
          
          msg.on('body', (stream) => {
            let buffer = '';
            stream.on('data', (chunk) => {
              buffer += chunk.toString('utf8');
            });
            stream.once('end', () => {
              // 解析头部
              const lines = buffer.split('\r\n');
              lines.forEach(line => {
                if (line.startsWith('From:')) {
                  emailData.from = line.replace('From: ', '').trim();
                } else if (line.startsWith('To:')) {
                  emailData.to = line.replace('To: ', '').trim();
                } else if (line.startsWith('Subject:')) {
                  emailData.subject = line.replace('Subject: ', '').trim();
                } else if (line.startsWith('Date:')) {
                  emailData.date = line.replace('Date: ', '').trim();
                }
              });
            });
          });
          
          msg.once('end', () => {
            processedCount++;
            
            if (emailData.subject !== undefined) {
              emails.push({
                from: emailData.from || '未知',
                to: emailData.to || '',
                subject: emailData.subject || '无主题',
                date: emailData.date || new Date().toUTCString(),
                seqno: emailData.seqno
              });
            }
            
            // 所有邮件处理完成
            if (processedCount >= maxEmails) {
              imap.end();
            }
          });
        });
        
        f.once('error', (err) => {
          console.error('❌ Fetch error:', err.message);
          reject(err);
        });
        
        f.once('end', () => {
          // 等待所有 message 处理完成
          setTimeout(() => {
            resolve(emails);
          }, 1000);
        });
      });
    });
    
    imap.once('error', (err) => {
      console.error('❌ IMAP error:', err.message);
      reject(err);
    });
    
    imap.connect();
  });
}

function classifyEmail(email) {
  const subject = (email.subject || '').toLowerCase();
  const from = (email.from || '').toLowerCase();
  
  // 重要邮件
  const importantKeywords = ['urgent', 'important', '紧急', '重要', '会议', 'report', '报告', '通知', '审核'];
  if (importantKeywords.some(k => subject.includes(k) || from.includes(k))) {
    return 'important';
  }
  
  // 推广邮件
  const promoKeywords = ['promo', 'discount', '优惠', '促销', '订阅', 'unsubscribe', '营销', '广告'];
  if (promoKeywords.some(k => subject.includes(k))) {
    return 'promo';
  }
  
  // 垃圾邮件（简单规则）
  const spamKeywords = ['发票', '代开', '赌博', '彩票'];
  if (spamKeywords.some(k => subject.includes(k))) {
    return 'spam';
  }
  
  return 'normal';
}

async function main() {
  console.log('🚀 开始获取邮件...\n');
  
  try {
    const emails = await fetchEmails();
    
    console.log(`✅ 获取到 ${emails.length} 封邮件\n`);
    
    // 分类
    const classified = emails.map(email => ({
      ...email,
      category: classifyEmail(email)
    }));
    
    // 统计
    const stats = {
      total: classified.length,
      important: classified.filter(e => e.category === 'important').length,
      normal: classified.filter(e => e.category === 'normal').length,
      promo: classified.filter(e => e.category === 'promo').length,
      spam: classified.filter(e => e.category === 'spam').length
    };
    
    console.log('📊 邮件分类统计：');
    console.log(`   📌 重要：${stats.important}`);
    console.log(`   📝 普通：${stats.normal}`);
    console.log(`   📢 推广：${stats.promo}`);
    console.log(`   🗑️  垃圾：${stats.spam}`);
    console.log('');
    
    // 保存
    saveEmails(classified);
    console.log(`✅ 邮件数据已保存：${DATA_FILE}`);
    console.log('');
    
    // 显示最新 10 封邮件
    console.log('📬 最新邮件预览：');
    classified.slice(0, 10).forEach((email, i) => {
      const icon = email.category === 'important' ? '📌' : email.category === 'promo' ? '📢' : '📝';
      console.log(`   ${i + 1}. ${icon} ${email.from.split('<')[0].trim().substring(0, 20)} - ${email.subject.substring(0, 40)}`);
    });
    console.log('');
    
    // 显示重要邮件
    const importantEmails = classified.filter(e => e.category === 'important');
    if (importantEmails.length > 0) {
      console.log('📌 重要邮件：');
      importantEmails.forEach((email, i) => {
        console.log(`   ${i + 1}. ${email.from} - ${email.subject}`);
      });
      console.log('');
    }
    
    console.log('💡 下一步：');
    console.log('   运行 ./scripts/summarize-emails.js 生成摘要');
    
  } catch (error) {
    console.error('❌ 获取邮件失败:', error.message);
    if (error.code === 'ECONNREFUSED') {
      console.error('\n可能原因：');
      console.error('  1. 网络连接问题');
      console.error('  2. IMAP 服务器地址或端口错误');
    } else if (error.message.includes('authentication')) {
      console.error('\n可能原因：');
      console.error('  1. 授权码错误');
      console.error('  2. IMAP/SMTP 服务未开启');
    }
    process.exit(1);
  }
}

main();
