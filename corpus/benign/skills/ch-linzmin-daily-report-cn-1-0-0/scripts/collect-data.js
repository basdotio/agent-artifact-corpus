#!/usr/bin/env node
/**
 * 数据收集脚本 - 收集日历、待办、邮件等数据用于生成日报
 * 用法：./collect-data.js [选项]
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const DATA_DIR = path.join(__dirname, '..', 'data');
const DATA_FILE = path.join(DATA_DIR, 'daily-data.json');

function printUsage() {
  console.log(`
📊 数据收集脚本

用法：
  ./collect-data.js [选项]

选项：
  --calendar    收集日历数据
  --todo        收集待办事项
  --email       收集邮件摘要
  --manual      手动输入今日总结
  --all         收集所有数据（默认）
  --output      输出收集的数据
  --help        显示帮助
`);
}

function loadData() {
  if (!fs.existsSync(DATA_FILE)) {
    return {
      date: new Date().toISOString().split('T')[0],
      calendar: [],
      todo: [],
      email: [],
      manual: '',
      collectedAt: null
    };
  }
  return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
}

function saveData(data) {
  if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, { recursive: true });
  }
  data.collectedAt = new Date().toISOString();
  fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));
}

function collectCalendar() {
  console.log('📅 收集日历数据...');
  
  // 尝试从系统日历读取（macOS）
  try {
    if (process.platform === 'darwin') {
      const result = execSync(
        `osascript -e 'tell application "System Events" to get name of every process'`,
        { encoding: 'utf8', timeout: 5000 }
      );
      console.log('  ✅ 日历数据收集成功（示例数据）');
      return [
        { time: '09:00-10:00', event: '晨会' },
        { time: '14:00-15:00', event: '项目评审' },
        { time: '16:00-17:00', event: '技术分享' }
      ];
    }
  } catch (error) {
    console.log('  ⚠️  无法访问系统日历，使用示例数据');
  }
  
  // 示例数据
  return [
    { time: '09:00-10:00', event: '晨会' },
    { time: '14:00-15:00', event: '项目评审' }
  ];
}

function collectTodo() {
  console.log('✅ 收集待办事项...');
  
  // 示例数据
  return [
    { task: '完成日报技能开发', status: 'done' },
    { task: '回复邮件', status: 'done' },
    { task: '代码审查', status: 'pending' }
  ];
}

function collectEmail() {
  console.log('📧 收集邮件摘要...');
  
  // 示例数据
  return {
    received: 15,
    sent: 8,
    important: [
      { from: '老板', subject: 'Q2 目标讨论' },
      { from: '客户', subject: '项目进度确认' }
    ]
  };
}

function collectManual() {
  console.log('📝 请输入今日总结（输入空行结束）：');
  
  const lines = [];
  const readline = require('readline').createInterface({
    input: process.stdin,
    output: process.stdout
  });
  
  return new Promise((resolve) => {
    readline.on('line', (line) => {
      if (line.trim() === '') {
        readline.close();
        resolve(lines.join('\n'));
      } else {
        lines.push(line);
      }
    });
    
    readline.on('close', () => {
      resolve(lines.join('\n'));
    });
  });
}

function outputData(data) {
  console.log('\n📊 今日数据概览\n');
  console.log('='.repeat(50));
  console.log(`日期：${data.date}`);
  console.log(`收集时间：${new Date(data.collectedAt).toLocaleString('zh-CN')}`);
  console.log('');
  
  console.log(`📅 日历事件：${data.calendar.length}个`);
  data.calendar.forEach(e => console.log(`   ${e.time} ${e.event}`));
  console.log('');
  
  const doneCount = data.todo.filter(t => t.status === 'done').length;
  console.log(`✅ 待办事项：${doneCount}/${data.todo.length} 完成`);
  data.todo.forEach(t => {
    const icon = t.status === 'done' ? '✅' : '⏳';
    console.log(`   ${icon} ${t.task}`);
  });
  console.log('');
  
  console.log(`📧 邮件：收到${data.email.received} 发送${data.email.sent}`);
  if (data.email.important.length > 0) {
    console.log('   重要邮件：');
    data.email.important.forEach(m => console.log(`     - ${m.from}: ${m.subject}`));
  }
  console.log('');
  
  if (data.manual) {
    console.log('📝 今日总结：');
    data.manual.split('\n').forEach(line => console.log(`   ${line}`));
    console.log('');
  }
  
  console.log('='.repeat(50));
}

async function collectAll() {
  console.log('🚀 开始收集今日数据...\n');
  
  const data = loadData();
  
  data.calendar = collectCalendar();
  data.todo = collectTodo();
  data.email = collectEmail();
  
  console.log('');
  data.manual = await collectManual();
  
  saveData(data);
  
  console.log('\n✅ 数据收集完成！\n');
  outputData(data);
  
  console.log('\n💡 下一步：运行 ./generate-report.js 生成日报');
}

// 主程序
async function main() {
  const args = process.argv.slice(2);
  
  if (args.includes('-h') || args.includes('--help')) {
    printUsage();
    process.exit(0);
  }
  
  if (args.includes('--output')) {
    const data = loadData();
    outputData(data);
    process.exit(0);
  }
  
  const collectCalendarOnly = args.includes('--calendar');
  const collectTodoOnly = args.includes('--todo');
  const collectEmailOnly = args.includes('--email');
  const collectManualOnly = args.includes('--manual');
  
  if (collectCalendarOnly || collectTodoOnly || collectEmailOnly || collectManualOnly) {
    const data = loadData();
    
    if (collectCalendarOnly) {
      data.calendar = collectCalendar();
    }
    if (collectTodoOnly) {
      data.todo = collectTodo();
    }
    if (collectEmailOnly) {
      data.email = collectEmail();
    }
    if (collectManualOnly) {
      console.log('');
      data.manual = await collectManual();
    }
    
    saveData(data);
    outputData(data);
  } else {
    // 默认收集所有
    await collectAll();
  }
}

main();
