#!/usr/bin/env node
/**
 * QQ 邮箱 IMAP 配置向导
 * 用法：./setup-qq-email.js
 */

const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { execSync } = require('child_process');

const CONFIG_DIR = path.join(__dirname, '..', 'config');
const CONFIG_FILE = path.join(CONFIG_DIR, 'email-config.json');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function printGuide() {
  console.log(`
🦆 QQ 邮箱 IMAP 配置向导

📋 配置前准备：

1. 登录 QQ 邮箱网页版 (https://mail.qq.com)

2. 开启 IMAP/SMTP 服务：
   - 点击"设置" → "账户"
   - 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务"
   - 开启"IMAP/SMTP 服务"

3. 获取授权码：
   - 点击"生成授权码"
   - 按提示发送短信验证
   - 复制生成的授权码（重要！只显示一次）

⚠️  注意：
- 授权码不是 QQ 密码！
- 授权码只显示一次，请妥善保存
- 如果忘记，可以重新生成

按回车继续...
`);
}

function askQuestion(query) {
  return new Promise((resolve) => {
    rl.question(query, (answer) => {
      resolve(answer);
    });
  });
}

async function getConfig() {
  console.log('\n📧 请输入配置信息：\n');
  
  const email = await askQuestion('QQ 邮箱地址（如：[REDACTED_SECRET]）: ');
  
  console.log('\n💡 授权码获取方法：');
  console.log('   1. 登录 https://mail.qq.com');
  console.log('   2. 设置 → 账户 → 开启 IMAP/SMTP 服务');
  console.log('   3. 生成授权码并复制');
  console.log('');
  
  const authCode = await askQuestion('授权码：');
  
  return {
    email,
    authCode
  };
}

function testConnection(email, authCode) {
  console.log('\n🔍 测试连接...');
  
  // 创建一个简单的测试脚本
  const testScript = `
const Imap = require('imap');

const imap = new Imap({
  user: '${email}',
  [REDACTED_SECRET]',
  host: 'imap.qq.com',
  port: 993,
  tls: true,
  tlsOptions: { servername: 'imap.qq.com' }
});

imap.once('ready', () => {
  console.log('✅ 连接成功');
  imap.end();
  process.exit(0);
});

imap.once('error', (err) => {
  console.log('❌ 连接失败:', err.message);
  process.exit(1);
});

imap.connect();
`;
  
  const testFile = path.join(CONFIG_DIR, 'test-connection.js');
  fs.writeFileSync(testFile, testScript);
  
  try {
    execSync(`node ${testFile}`, { 
      encoding: 'utf8', 
      stdio: 'inherit',
      timeout: 10000 
    });
    fs.unlinkSync(testFile);
    return true;
  } catch (error) {
    fs.unlinkSync(testFile);
    return false;
  }
}

function saveConfig(email, authCode) {
  const config = {
    email: {
      provider: 'qq',
      address: email,
      imap: {
        host: 'imap.qq.com',
        port: 993,
        tls: true,
        authCode: authCode
      },
      smtp: {
        host: 'smtp.qq.com',
        port: 465,
        tls: true,
        authCode: authCode
      }
    },
    summary: {
      enabled: true,
      aiProvider: 'modelstudio',
      maxEmails: 50,
      categories: ['important', 'normal', 'promo', 'spam']
    },
    schedule: {
      dailyTime: '20:00',
      weeklyDay: 'sunday'
    }
  };
  
  if (!fs.existsSync(CONFIG_DIR)) {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });
  }
  
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
  
  // 设置文件权限（仅所有者可读写）
  try {
    fs.chmodSync(CONFIG_FILE, 0o600);
    console.log('✅ 配置文件权限已设置为 600（仅所有者可读写）');
  } catch (error) {
    console.log('⚠️  无法设置文件权限，请手动保护配置文件');
  }
  
  console.log(`\n✅ 配置已保存：${CONFIG_FILE}`);
}

async function main() {
  printGuide();
  
  await rl.question('按回车继续...');
  
  const { email, authCode } = await getConfig();
  
  console.log('\n📋 确认配置信息：');
  console.log(`   邮箱：${email}`);
  console.log(`   IMAP: imap.qq.com:993`);
  console.log(`   SMTP: smtp.qq.com:465`);
  console.log('');
  
  const confirm = await askQuestion('确认保存？(y/n): ');
  
  if (confirm.toLowerCase() !== 'y') {
    console.log('❌ 已取消');
    rl.close();
    process.exit(0);
  }
  
  const success = testConnection(email, authCode);
  
  if (success) {
    saveConfig(email, authCode);
    console.log('\n🎉 配置完成！');
    console.log('\n💡 下一步：');
    console.log('   运行 ./scripts/fetch-emails.js 测试获取邮件');
  } else {
    console.log('\n❌ 连接测试失败，请检查：');
    console.log('   1. 邮箱地址是否正确');
    console.log('   2. 授权码是否正确');
    console.log('   3. IMAP/SMTP 服务是否已开启');
    console.log('   4. 网络连接是否正常');
    console.log('\n   然后重新运行 ./setup-qq-email.js');
  }
  
  rl.close();
}

main();
