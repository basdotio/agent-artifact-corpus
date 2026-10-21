import fs from 'node:fs';
import path from 'node:path';

function bad(message) { throw new Error(`Invalid precheck test plan: ${message}`); }
function object(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || ![Object.prototype, null].includes(Object.getPrototypeOf(value))) bad(`${label} must be an object`);
  const actual = Reflect.ownKeys(value);
  if (actual.length !== keys.length || actual.some(k => !keys.includes(k))) bad(`${label} has unexpected or missing fields`);
  if (actual.some(k => !Object.hasOwn(Object.getOwnPropertyDescriptor(value, k), 'value'))) bad(`${label} must contain data fields`);
}
function string(value, label) { if (typeof value !== 'string' || !value.trim() || /[\u0000-\u001f\u007f]/u.test(value)) bad(`${label} must be a nonempty plain string`); }
function array(value, label) { if (!Array.isArray(value)) bad(`${label} must be an array`); }
function safePath(value, cloneRoot, { required = false, file = false } = {}) {
  string(value, 'path');
  if (value.includes('\\') || value.includes(':') || value.startsWith('/') || /[;&|<>`$]/u.test(value) || value.split('/').some(p => !p || p === '.' || p === '..' || p.toLowerCase() === '.git' || /[. ]$/u.test(p) || /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/iu.test(p))) bad('unsafe repository path');
  if (!cloneRoot) return;
  const root = path.resolve(cloneRoot);
  if (!fs.lstatSync(root).isDirectory() || fs.lstatSync(root).isSymbolicLink()) bad('clone root must be a regular directory');
  let current = root;
  const pieces = value.split('/');
  for (let i = 0; i < pieces.length; i++) {
    current = path.join(current, pieces[i]);
    let stat;
    try { stat = fs.lstatSync(current); } catch (error) { if (error.code !== 'ENOENT' || required) bad('selected path is missing or unreadable'); return; }
    if (stat.isSymbolicLink()) bad('selected path is a link');
    if (i < pieces.length - 1 && !stat.isDirectory()) bad('path parent is not a directory');
    if (i === pieces.length - 1 && (file ? !stat.isFile() : !(stat.isFile() || stat.isDirectory()))) bad('selected path has unsafe type');
  }
}

function testArgs(command, cloneRoot) {
  const args = command.args;
  let index;
  if (command.tool === 'python') {
    if (command.parser !== 'pytest' || args[0] !== '-m' || args[1] !== 'pytest') bad('Python tests must invoke -m pytest with pytest parser');
    index = 2;
  } else if (command.tool === 'node') {
    if (command.parser !== 'node' || args[0] !== '--test') bad('Node tests must invoke --test with node parser');
    index = 1;
  } else bad('test tool must be python or node');
  for (; index < args.length; index++) {
    const arg = args[index];
    if (command.tool === 'python' && ['-k', '-m', '--ignore', '--ignore-glob', '--deselect'].includes(arg)) {
      const value = args[++index]; string(value, 'pytest option value');
      if (arg === '--ignore') safePath(value, cloneRoot, { required: true });
      else if (arg === '--deselect') safePath(value.split('::')[0], cloneRoot, { required: true });
      else if (arg === '--ignore-glob' && /[\\:;&|<>`$]/u.test(value)) bad('unsafe ignore pattern');
      continue;
    }
    if (command.tool === 'python' && (/^-(?:q+|v+|x|s)$/u.test(arg) || ['--disable-warnings', '--strict-markers', '--strict-config'].includes(arg) || /^--(?:tb=(?:auto|long|short|line|native|no)|maxfail=[1-9][0-9]*|durations=[0-9]+|color=(?:yes|no|auto))$/u.test(arg))) continue;
    if (command.tool === 'node' && (arg === '--test-reporter=tap' || /^--test-(?:concurrency|timeout)=[1-9][0-9]*$/u.test(arg) || /^--test-(?:name-pattern|skip-pattern)=.+$/u.test(arg))) continue;
    if (arg.startsWith('-')) bad('unsupported test option');
    safePath(command.tool === 'python' ? arg.split('::')[0] : arg, cloneRoot, { required: true });
  }
}

function checkNpmLock(cloneRoot) {
  if (!cloneRoot) return;
  safePath('package.json', cloneRoot, { required: true, file: true });
  safePath('package-lock.json', cloneRoot, { required: true, file: true });
  let pkg, lock;
  try { pkg = JSON.parse(fs.readFileSync(path.join(cloneRoot, 'package.json'), 'utf8')); lock = JSON.parse(fs.readFileSync(path.join(cloneRoot, 'package-lock.json'), 'utf8')); } catch { bad('unreadable npm manifest or lockfile'); }
  if (!pkg || typeof pkg !== 'object' || ![2, 3].includes(lock?.lockfileVersion) || !lock.packages || !lock.packages['']) bad('npm lockfile must use version 2 or 3 with root package');
  const root = lock.packages[''];
  const normalized = value => JSON.stringify(Object.fromEntries(Object.entries(value ?? {}).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)));
  for (const key of ['name', 'version']) if (Object.hasOwn(pkg, key) && root[key] !== pkg[key]) bad('stale npm lockfile identity');
  for (const key of ['dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies']) if (normalized(pkg[key]) !== normalized(root[key])) bad('stale npm lockfile dependencies');
}

function setupArgs(command, cloneRoot) {
  const args = command.args;
  if (command.tool === 'npm') {
    if (args.length !== 4 || args[0] !== 'ci' || new Set(args.slice(1)).size !== 3 || args.slice(1).some(a => !['--ignore-scripts', '--no-audit', '--no-fund'].includes(a))) bad('npm setup permits locked ci --ignore-scripts --no-audit --no-fund only');
    checkNpmLock(cloneRoot); return;
  }
  if (command.tool !== 'python' || args[0] !== '-m' || args[1] !== 'pip' || args[2] !== 'install') bad('setup must use locked npm ci or python -m pip install');
  let targets = 0;
  for (let i = 3; i < args.length; i++) {
    const arg = args[i];
    if (['--no-input', '--disable-pip-version-check', '--no-cache-dir'].includes(arg)) continue;
    if (['-r', '--requirement'].includes(arg)) { safePath(args[++i], cloneRoot, { required: true, file: true }); targets++; continue; }
    if (arg === '.' || /^\.\[[a-zA-Z0-9_-]+(?:,[a-zA-Z0-9_-]+)*\]$/u.test(arg)) { targets++; continue; }
    bad('unsupported pip argument or installation target');
  }
  if (!targets) bad('pip setup has no declared target');
}

export function validateTestPlan(plan, { cloneRoot } = {}) {
  object(plan, ['schema', 'mockedServices', 'declaredSkips', 'commands'], 'plan');
  if (plan.schema !== 'portfolio-test-plan-v1') bad('unknown schema');
  array(plan.mockedServices, 'mockedServices'); array(plan.declaredSkips, 'declaredSkips'); array(plan.commands, 'commands');
  if (!plan.commands.length) bad('commands cannot be empty');
  const services = new Set(), commands = new Map(), outputs = new Set();
  for (const service of plan.mockedServices) {
    object(service, ['service', 'method', 'fixtures'], 'mocked service'); string(service.service, 'service'); string(service.method, 'method'); array(service.fixtures, 'fixtures');
    if (services.has(service.service) || !service.fixtures.length || new Set(service.fixtures).size !== service.fixtures.length) bad('duplicate service or empty/duplicate fixtures');
    services.add(service.service);
    for (const fixture of service.fixtures) safePath(fixture, cloneRoot, { required: true, file: true });
  }
  let sawTest = false;
  for (const command of plan.commands) {
    object(command, command?.phase === 'test' ? ['id', 'phase', 'tool', 'args', 'timeoutSeconds', 'outputs', 'parser'] : ['id', 'phase', 'tool', 'args', 'timeoutSeconds', 'outputs'], 'command');
    if (typeof command.id !== 'string' || !/^[a-z][a-z0-9-]{0,63}$/u.test(command.id) || commands.has(command.id)) bad('invalid or duplicate command id');
    if (!['setup', 'test'].includes(command.phase) || !['python', 'node', 'npm'].includes(command.tool)) bad('invalid phase or tool');
    if (command.phase === 'setup' && sawTest) bad('setup must precede test commands');
    if (!Number.isSafeInteger(command.timeoutSeconds) || command.timeoutSeconds < 1) bad('timeoutSeconds must be a positive safe integer');
    array(command.args, 'args'); for (const arg of command.args) string(arg, 'argument'); array(command.outputs, 'outputs');
    for (const output of command.outputs) {
      object(output, ['path', 'context'], 'output'); safePath(output.path, cloneRoot, { file: true });
      if (!['text', 'json', 'ci-log'].includes(output.context) || outputs.has(output.path.toLowerCase())) bad('invalid output context or duplicate path');
      outputs.add(output.path.toLowerCase());
    }
    if (command.phase === 'test') { sawTest = true; testArgs(command, cloneRoot); } else setupArgs(command, cloneRoot);
    commands.set(command.id, command);
  }
  if (!sawTest) bad('at least one test command is required');
  const skips = new Set();
  for (const skip of plan.declaredSkips) {
    object(skip, ['commandId', 'testId', 'reason'], 'declared skip'); for (const key of ['commandId', 'testId', 'reason']) string(skip[key], key);
    const command = commands.get(skip.commandId); if (!command || command.phase !== 'test') bad('skip references unknown test command');
    if (command.parser === 'node') {
      let id; try { id = JSON.parse(skip.testId); } catch { bad('invalid canonical Node skip id'); }
      if (!Array.isArray(id) || id.length !== 2 || !Array.isArray(id[0]) || !id[0].length || !Array.isArray(id[1]) || id[0].length !== id[1].length || id[0].some(n => !Number.isSafeInteger(n) || n < 1) || id[1].some(n => typeof n !== 'string' || !n) || JSON.stringify(id) !== skip.testId) bad('invalid canonical Node skip id');
    }
    const pair = JSON.stringify([skip.commandId, skip.testId]); if (skips.has(pair)) bad('duplicate declared skip'); skips.add(pair);
  }
  return JSON.parse(JSON.stringify(plan));
}
