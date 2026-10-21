import fs from "node:fs";
import path from "node:path";
import {spawn,spawnSync} from "node:child_process";
import {windowsJobInvocation} from "./portfolio-winjob.mjs";
import {parseStrictJson} from "./portfolio-parsers.mjs";
// Pinned Git configuration for child processes; paths live in this command's owned HOME.
const PINNED_CONFIG = Object.freeze([
  ['core.autocrlf', 'false'], ['core.safecrlf', 'false'], ['core.fsmonitor', 'false'],
  ['core.longpaths', 'true'], ['commit.gpgsign', 'false'], ['tag.gpgsign', 'false'],
  ['credential.helper', ''], ['init.defaultBranch', 'main'],
  ['protocol.allow', 'never'], ['protocol.file.allow', 'always'],
]);
function isolatedGitEnv(base) {
  const root = fs.mkdtempSync(path.join(base.HOME, 'git-isolation-'));
  const globalConfig = path.join(root, 'empty-global.gitconfig');
  const hooksDir = path.join(root, 'empty-hooks');
  const templateDir = path.join(root, 'empty-template');
  fs.writeFileSync(globalConfig, ''); fs.mkdirSync(hooksDir); fs.mkdirSync(templateDir);
  const env = {};
  for (const [key, value] of Object.entries(base)) if (!key.toUpperCase().startsWith('GIT_')) env[key] = value;
  const cfg = [...PINNED_CONFIG, ['core.hooksPath', hooksDir], ['init.templateDir', templateDir]];
  env.GIT_CONFIG_NOSYSTEM = '1'; env.GIT_CONFIG_GLOBAL = globalConfig;
  env.GIT_TERMINAL_PROMPT = '0'; env.GIT_NO_REPLACE_OBJECTS = '1';
  env.GIT_CONFIG_COUNT = String(cfg.length);
  cfg.forEach(([key, value], i) => { env[`GIT_CONFIG_KEY_${i}`] = key; env[`GIT_CONFIG_VALUE_${i}`] = value; });
  return env;
}
export function createChildEnvironment(root, base = process.env) {
  const env = {};
  const allowed = new Set(['PATH', 'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'COMSPEC', 'PATHEXT', 'LANG', 'LC_ALL']);
  for (const [key, value] of Object.entries(base)) if (allowed.has(key.toUpperCase()) && typeof value === 'string') env[key.toUpperCase()] = value;
  const folders = { HOME: 'home', USERPROFILE: 'home', APPDATA: 'appdata', LOCALAPPDATA: 'localappdata',
    TEMP: 'temp', TMP: 'temp', TMPDIR: 'temp', PIP_CACHE_DIR: 'pip-cache', NPM_CONFIG_CACHE: 'npm-cache' };
  for (const [key, rel] of Object.entries(folders)) {
    env[key] = path.join(root, rel);
    fs.mkdirSync(env[key], { recursive: true });
  }
  for (const [key, rel] of Object.entries({ NPM_CONFIG_USERCONFIG: 'npm-user.conf', NPM_CONFIG_GLOBALCONFIG: 'npm-global.conf' })) {
    env[key] = path.join(root, rel); fs.writeFileSync(env[key], '');
  }
  env.PIP_CONFIG_FILE = process.platform === 'win32' ? 'NUL' : '/dev/null';
  env.PYTHONNOUSERSITE = '1'; env.PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1';
  env.PIP_DISABLE_PIP_VERSION_CHECK = '1'; env.PIP_NO_INPUT = '1';
  env.NPM_CONFIG_IGNORE_SCRIPTS = 'true'; env.NPM_CONFIG_AUDIT = 'false'; env.NPM_CONFIG_FUND = 'false';
  // Apply these pins to setup/test descendants too, not only the runner's clone commands.
  return isolatedGitEnv(env);
}

function isAlive(pid) {
  try { process.kill(pid, 0); return true; } catch (e) { if (e.code === 'ESRCH') return false; throw e; }
}

export async function runOwnedProcess(executable, args, { cwd, env, timeoutSeconds, maxBytes = 32 * 1024 * 1024 }) {
  if (process.platform !== 'win32') throw new Error('verified process-tree ownership currently needs a Windows host');
  if (!path.isAbsolute(executable) || !Number.isSafeInteger(timeoutSeconds) || timeoutSeconds <= 0) throw new Error('invalid bounded process invocation');
  return new Promise((resolve, reject) => {
    let job;
    job = windowsJobInvocation(executable, args, { cwd, env, timeoutSeconds });
    const child = spawn(job.executable, job.args, { cwd, env, shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    const out = [], err = []; let bytes = 0, timedOut = false, controlError = null, stopped = false;
    let tracked = child.pid ? [child.pid] : [];
    const stop = () => {
      if (stopped || !child.pid) return;
      stopped = true;
      try {
          const r = spawnSync(path.join(env.SYSTEMROOT, 'System32', 'taskkill.exe'), ['/PID', String(child.pid), '/T', '/F'],
            { env, windowsHide: true, timeout: 10000 });
          if (r.error || r.status !== 0) throw new Error('owned process-tree termination failed');
          // taskkill reports each terminated PID. Unreadable/localized output cannot prove termination.
          tracked = [...new Set([...r.stdout.toString().matchAll(/process with PID\s+(\d+)\b/g)].map((m) => Number(m[1])))];
          if (!tracked.includes(child.pid)) throw new Error('unreadable owned process-tree termination receipt');
      } catch (e) { controlError = e; try { child.kill('SIGKILL'); } catch { /* failure stays failed */ } }
    };
    const capture = (list) => (chunk) => {
      bytes += chunk.length;
      if (bytes > maxBytes) { controlError = new Error('command output exceeded the retained-evidence limit'); stop(); }
      else list.push(chunk);
    };
    child.stdout.on('data', capture(out)); child.stderr.on('data', capture(err));
    const started = performance.now(); let graceTimer;
    const timer = setInterval(() => {
      if (!timedOut && performance.now() - started >= timeoutSeconds * 1000) {
        timedOut = true;
        try { fs.writeFileSync(job.cancel, 'stop'); graceTimer = setTimeout(stop, 3000); }
        catch { controlError = new Error('owned job cancellation could not be requested'); stop(); }
      }
    }, Math.min(100, timeoutSeconds * 1000));
    child.once('error', (e) => { clearInterval(timer); clearTimeout(graceTimer); try { job?.cleanup(); } catch { /* no successful receipt */ } reject(new Error(`command could not start (${e.code || 'error'})`)); });
    child.once('close', (code, signal) => {
      clearInterval(timer); clearTimeout(graceTimer);
      let terminationVerified = !controlError;
      if (stopped) {
        try {
          terminationVerified &&= tracked.every((pid) => !isAlive(pid));
        } catch { terminationVerified = false; }
      }
      if (job && !stopped) {
        try {
          const receipt = parseStrictJson(fs.readFileSync(job.receipt));
          if (!Number.isInteger(receipt.ExitCode) || typeof receipt.TimedOut !== 'boolean' || receipt.TerminationVerified !== true) throw new Error('invalid owned Windows job receipt');
          code = receipt.ExitCode; timedOut ||= receipt.TimedOut; terminationVerified &&= receipt.TerminationVerified;
        } catch { terminationVerified = false; controlError = new Error('owned Windows job completion could not be verified'); }
      }
      try { job?.cleanup(); } catch { terminationVerified = false; controlError = new Error('owned Windows job cleanup failed'); }
      resolve({ exitCode: code ?? -1, signal, stdout: Buffer.concat(out), stderr: Buffer.concat(err), timedOut,
        terminationVerified, error: controlError ? controlError.message : null });
    });
  });
}
