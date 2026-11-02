#!/usr/bin/env node
/**
 * 测试 IMAP 连接
 * 用法：./test-connection.js
 */

const Imap = require('imap');
const fs = require('fs');
const path = require('path');

const CONFIG_FILE = path.join(__dirname, '..', 'config', 'email-config.json');

function main() {
  console.log('🔍 测试 IMAP 连接...\n');
  
  if (!fs.existsSync(CONFIG_FILE)) {
    console.error('❌ 配置文件不存在，请先运行 ./scripts/setup-qq-email.js');
    process.exit(1);
  }
  
  const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
  
  const imap = new Imap({
    user: config.email.address,
    [REDACTED_SECRET],
    host: config.email.imap.host,
    port: config.email.imap.port,
    tls: config.email.imap.tls,
    tlsOptions: { servername: config.email.imap.host }
  });
  
  imap.once('ready', () => {
    console.log('✅ IMAP 连接成功！');
    console.log(`   邮箱：${config.email.address}`);
    console.log(`   服务器：${config.email.imap.host}:${config.email.imap.port}`);
    console.log('');
    imap.end();
    process.exit(0);
  });
  
  imap.once('error', (err) => {
    console.log('❌ 连接失败:', err.message);
    console.log('');
    console.log('请检查：');
    console.log('  1. 邮箱地址是否正确');
    console.log('  2. 授权码是否正确');
    console.log('  3. IMAP/SMTP 服务是否已开启');
    console.log('  4. 网络连接是否正常');
    console.log('');
    process.exit(1);
  });
  
  imap.connect();
}

main();
