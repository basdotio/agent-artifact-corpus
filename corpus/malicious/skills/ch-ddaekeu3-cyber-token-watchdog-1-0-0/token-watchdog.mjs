#!/usr/bin/env node
// token-watchdog.mjs — OpenClaw 비용 감시 데몬 (세션 jsonl 직접 읽기 방식)
// 실행: node ~/.openclaw/workspace/token-watchdog.mjs [--task <설명>] [--estimate <달러>]

import { execSync } from 'child_process';
import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync, readdirSync, openSync, writeSync, closeSync } from 'fs';
import { join } from 'path';

// ── 설정 ──────────────────────────────────────────────────────
const HOME = process.env.HOME;
const CONFIG = {
  pollIntervalMs:   30_000,
  thresholdMultiplier: 2.0,
  telegramTarget:  '8616468733',
  sessionsDir:     join(HOME, '.openclaw', 'agents', 'main', 'sessions'),
  logDir:          join(HOME, '.openclaw', 'workspace', 'memory'),
  logFile:         'token-watchdog.log',
  stateFile:       'token-watchdog-state.json',
  idleTimeoutMs:   600_000,   // 10분 변화 없으면 완료 판단
};

// ── 비용 예상 알고리즘 (달러 기준) ──────────────────────────────
const COMPLEXITY_KEYWORDS = {
  high:   ['debug', 'fix bug', 'refactor', 'migration', 'multi-file', 'architecture',
           '디버깅', '리팩토링', '마이그레이션', '버그', 'complex', 'integration', 'security', 'performance'],
  medium: ['implement', 'create', 'build', 'add feature', 'update',
           '구현', '생성', '추가', '업데이트', 'test', 'deploy'],
  low:    ['read', 'check', 'list', 'status', 'help', 'explain',
           '확인', '조회', '검색', '설명', 'search', 'query'],
};

const COST_ESTIMATES = {
  high:    0.50,
  medium:  0.15,
  low:     0.10,
  default: 0.30,
};

function estimateCost(taskDescription) {
  if (!taskDescription) return COST_ESTIMATES.default;
  const lower = taskDescription.toLowerCase();
  const len   = taskDescription.length;

  for (const [level, keywords] of Object.entries(COMPLEXITY_KEYWORDS)) {
    for (const kw of keywords) {
      if (lower.includes(kw)) {
        let est = COST_ESTIMATES[level];
        if (len > 500)      est *= 2.0;
        else if (len > 200) est *= 1.5;
        return Math.round(est * 10000) / 10000;
      }
    }
  }
  if (taskDescription.length > 300) return COST_ESTIMATES.medium;
  return COST_ESTIMATES.default;
}

// ── 세션 파일 감지 ─────────────────────────────────────────────
function findLatestSession() {
  if (!existsSync(CONFIG.sessionsDir)) return null;

  let latest = null;
  let latestMtime = 0;

  for (const fname of readdirSync(CONFIG.sessionsDir)) {
    // 활성 세션만: .jsonl 확장자, deleted/reset 제외
    if (!fname.endsWith('.jsonl')) continue;

    const fpath = join(CONFIG.sessionsDir, fname);
    try {
      const { mtimeMs } = statSync(fpath);
      if (mtimeMs > latestMtime) {
        latestMtime = mtimeMs;
        latest = fpath;
      }
    } catch { /* skip */ }
  }
  return latest;
}

// ── jsonl 증분 읽기 + usage 합산 ───────────────────────────────
function readNewUsage(sessionPath, baselineBytes) {
  let totalCost   = 0;
  let totalInput  = 0;
  let totalOutput = 0;
  let totalCache  = 0;

  try {
    const stat = statSync(sessionPath);
    if (stat.size <= baselineBytes) return { totalCost, totalInput, totalOutput, totalCache, currentBytes: baselineBytes };

    const buf = Buffer.alloc(stat.size - baselineBytes);
    const fd  = openSync(sessionPath, 'r');
    const bytesRead = require('fs').readSync(fd, buf, 0, buf.length, baselineBytes);
    require('fs').closeSync(fd);

    const chunk = buf.slice(0, bytesRead).toString('utf8');
    const lines = chunk.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const obj = JSON.parse(trimmed);
        const usage = obj?.message?.usage;
        if (!usage) continue;

        totalCost   += usage.cost?.total    || 0;
        totalInput  += usage.input          || 0;
        totalOutput += usage.output         || 0;
        totalCache  += (usage.cacheRead || 0) + (usage.cacheWrite || 0);
      } catch { /* malformed line — skip */ }
    }

    return { totalCost, totalInput, totalOutput, totalCache, currentBytes: stat.size };
  } catch (err) {
    log(`[ERROR] jsonl 읽기 실패: ${err.message}`);
    return { totalCost, totalInput, totalOutput, totalCache, currentBytes: baselineBytes };
  }
}

// ── OpenClaw 유틸리티 ──────────────────────────────────────────
function sendTelegramAlert(message) {
  try {
    execSync(
      `openclaw message send --channel telegram --target ${CONFIG.telegramTarget} -m ${shellEscape(message)}`,
      { encoding: 'utf8', timeout: 15_000 }
    );
    log('[ALERT] Telegram 전송 완료');
  } catch (err) {
    log(`[ERROR] Telegram 전송 실패: ${err.message}`);
  }
}

function pauseAgent() {
  try {
    execSync(
      `openclaw agent -m ${shellEscape('⚠️ 비용 예산 초과로 작업을 일시정지합니다. 지금까지 시도한 접근법을 요약하고 다른 방법을 제안해주세요. 같은 방법을 반복하지 마세요.')} --timeout 30`,
      { encoding: 'utf8', timeout: 35_000 }
    );
  } catch { /* 타임아웃 무시 — 메시지 전달이 목적 */ }
}

// ── 유틸리티 ───────────────────────────────────────────────────
function shellEscape(s) {
  return `'${s.replace(/'/g, "'\\''")}'`;
}

function log(msg) {
  const ts   = new Date().toISOString();
  const line = `${ts} ${msg}\n`;
  process.stderr.write(line);

  if (!existsSync(CONFIG.logDir)) mkdirSync(CONFIG.logDir, { recursive: true });
  const logPath = join(CONFIG.logDir, CONFIG.logFile);
  try {
    const fd = openSync(logPath, 'a');
    writeSync(fd, line);
    closeSync(fd);
  } catch { /* best-effort */ }
}

function loadState() {
  const p = join(CONFIG.logDir, CONFIG.stateFile);
  if (existsSync(p)) {
    try { return JSON.parse(readFileSync(p, 'utf8')); } catch { /* fall through */ }
  }
  return { lastCost: 0, lastCheckTime: Date.now() };
}

function saveState(state) {
  writeFileSync(join(CONFIG.logDir, CONFIG.stateFile), JSON.stringify(state, null, 2));
}

// ── 메인 ──────────────────────────────────────────────────────
async function main() {
  const args = process.argv.slice(2);
  let manualEstimate  = null;
  let taskDescription = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--estimate' && args[i + 1]) {
      manualEstimate = parseFloat(args[++i]);
    } else if (args[i] === '--task' && args[i + 1]) {
      taskDescription = args[++i];
    } else if (args[i] === '--help') {
      console.log(`
token-watchdog.mjs — OpenClaw 비용 감시 데몬

사용법:
  node token-watchdog.mjs [옵션]

옵션:
  --task <설명>       작업 설명 (자동 비용 예상)
  --estimate <달러>   수동 예상 비용 ($단위, 자동 예상 무시)
  --help              도움말

예시:
  node token-watchdog.mjs --task "Fix login bug"
  node token-watchdog.mjs --estimate 0.5 --task "Complex refactoring"
  node token-watchdog.mjs   # 기본 $0.30 예상
`);
      process.exit(0);
    }
  }

  const estimate = manualEstimate ?? estimateCost(taskDescription);

  // 세션 파일 감지
  const sessionPath = findLatestSession();
  if (!sessionPath) {
    log('[FATAL] 활성 세션 파일을 찾을 수 없습니다.');
    log(`[FATAL] 확인 경로: ${CONFIG.sessionsDir}`);
    process.exit(1);
  }

  // 시작 시점 바이트 기록
  const baselineBytes = statSync(sessionPath).size;

  log('[START] Token Watchdog 시작 (비용 기준 모드)');
  log(`[SESSION] ${sessionPath}`);
  log(`[CONFIG] 작업: ${taskDescription || '(미지정)'}`);
  log(`[CONFIG] 예상 비용: $${estimate.toFixed(4)}`);
  log(`[CONFIG] 경고 임계값: $${(estimate * CONFIG.thresholdMultiplier).toFixed(4)} (${CONFIG.thresholdMultiplier}x)`);
  log(`[CONFIG] 기준 오프셋: ${baselineBytes.toLocaleString()} bytes`);

  sendTelegramAlert(
    `🔍 Token Watchdog 시작\n` +
    `📋 작업: ${taskDescription || '미지정'}\n` +
    `💰 예상 비용: $${estimate.toFixed(4)}\n` +
    `⚠️ 경고 임계값: $${(estimate * CONFIG.thresholdMultiplier).toFixed(4)}`
  );

  let alertSent = false;
  let consecutiveErrors = 0;
  let lastKnownBytes = baselineBytes;

  const interval = setInterval(() => {
    const { totalCost, totalInput, totalOutput, totalCache, currentBytes } =
      readNewUsage(sessionPath, baselineBytes);

    if (currentBytes === lastKnownBytes && currentBytes > baselineBytes) {
      // 파일 크기 변화 없음 — 에러 아님
    }

    if (totalCost === 0 && currentBytes === baselineBytes) {
      consecutiveErrors++;
      if (consecutiveErrors >= 10) {
        log('[WARN] 10회 연속 변화 없음. 세션이 활성인지 확인하세요.');
        consecutiveErrors = 0;
      }
      return;
    }
    consecutiveErrors = 0;
    lastKnownBytes = currentBytes;

    const ratio = estimate > 0 ? totalCost / estimate : 0;

    log(
      `[MONITOR] 비용: $${totalCost.toFixed(4)} / $${estimate.toFixed(4)} ` +
      `(${(ratio * 100).toFixed(1)}%) | in:${totalInput} out:${totalOutput} cache:${totalCache}`
    );

    // 2x 임계값 초과
    if (ratio >= CONFIG.thresholdMultiplier && !alertSent) {
      alertSent = true;

      const alertMsg =
        `🚨 비용 예산 초과 경고!\n\n` +
        `예상 $${estimate.toFixed(4)}이었는데 현재 $${totalCost.toFixed(4)} 소비 중.\n` +
        `비율: ${(ratio * 100).toFixed(0)}% (${CONFIG.thresholdMultiplier}x 초과)\n\n` +
        `계속할까요?\n` +
        `→ Telegram에서 "계속" 또는 "중지" 입력`;

      log(`[ALERT] 2x 초과! $${totalCost.toFixed(4)} > $${(estimate * CONFIG.thresholdMultiplier).toFixed(4)}`);
      sendTelegramAlert(alertMsg);
      pauseAgent();
      log('[PAUSED] 에이전트 일시정지 요청 전송. 사용자 응답 대기 중...');

      // 3x 초과 시 자동 종료
      setTimeout(() => {
        const recheck = readNewUsage(sessionPath, baselineBytes);
        if (recheck.totalCost > estimate * 3) {
          sendTelegramAlert(
            `🛑 비용 3x 초과! ($${recheck.totalCost.toFixed(4)})\n` +
            `자동 감시 종료. 에이전트를 수동으로 중지하세요:\n` +
            `openclaw agent -m "작업을 즉시 중단하고 진행 상황을 저장하세요."`
          );
          clearInterval(interval);
          process.exit(2);
        }
      }, 120_000);
    }

    // 완료 감지 (10분간 비용 변화 없으면)
    const state = loadState();
    if (totalCost === state.lastCost && Date.now() - state.lastCheckTime > CONFIG.idleTimeoutMs) {
      log('[DONE] 10분간 비용 변화 없음. 작업 완료로 판단.');
      sendTelegramAlert(
        `✅ Token Watchdog 완료\n` +
        `총 비용: $${totalCost.toFixed(4)}\n` +
        `예상 대비: ${(ratio * 100).toFixed(0)}%`
      );
      clearInterval(interval);
      process.exit(0);
    }

    state.lastCheckTime = (totalCost !== state.lastCost) ? Date.now() : state.lastCheckTime;
    state.lastCost = totalCost;
    saveState(state);

  }, CONFIG.pollIntervalMs);

  for (const sig of ['SIGINT', 'SIGTERM']) {
    process.on(sig, () => {
      log(`[STOP] ${sig} 수신. 감시 종료.`);
      clearInterval(interval);
      process.exit(0);
    });
  }

  log('[RUNNING] 모니터링 중... (Ctrl+C로 종료)');
}

main().catch(err => {
  log(`[FATAL] ${err.message}`);
  process.exit(1);
});
