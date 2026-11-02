#!/usr/bin/env node
/**
 * 定时生成日报（由 cron 调用）
 * 用法：./auto-report.js [时间]
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SCRIPT_DIR = __dirname;
const LOG_FILE = path.join(__dirname, '..', 'auto-report.log');

function log(message) {
  const timestamp = new Date().toLocaleString('zh-CN');
  const logLine = `[${timestamp}] ${message}\n`;
  console.log(logLine);
  fs.appendFileSync(LOG_FILE, logLine);
}

function main() {
  log('开始自动生成日报...');
  
  try {
    // 1. 收集数据（使用示例数据，不交互式）
    log('收集数据...');
    execSync(`node ${SCRIPT_DIR}/collect-data.js --all`, {
      encoding: 'utf8',
      stdio: 'pipe',
      env: { ...process.env, AUTO_MODE: 'true' }
    });
    
    // 2. 生成报告
    log('生成报告...');
    execSync(`node ${SCRIPT_DIR}/generate-report.js --save --preview`, {
      encoding: 'utf8',
      stdio: 'inherit'
    });
    
    // 3. 发送微信（可选，需要用户确认）
    // log('发送微信...');
    // execSync(`node ${SCRIPT_DIR}/send-report.js`, {
    //   encoding: 'utf8',
    //   stdio: 'inherit'
    // });
    
    log('✅ 日报生成完成');
    
  } catch (error) {
    log(`❌ 错误：${error.message}`);
  }
}

main();
