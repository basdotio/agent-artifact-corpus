import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { validateTestPlan } from './portfolio-plan.mjs';
import { parseNodeTap, parsePytestReport, parseStrictJson } from './portfolio-parsers.mjs';
import { createChildEnvironment, runOwnedProcess } from './portfolio-runtime.mjs';

const root = path.resolve(fileURLToPath(new URL('../../', import.meta.url)));
const fail = (message) => { throw new Error(`CI evidence refused: ${message}`); };
function regularFile(filename) {
  let current = path.parse(path.resolve(filename)).root;
  const relative = path.relative(current, path.resolve(filename));
  for (const piece of relative.split(path.sep)) {
    current = path.join(current, piece);
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink()) fail('selected file is a link');
  }
  if (!fs.statSync(filename).isFile()) fail('selected path must be a regular file');
}
function ownedDirectory(relative) {
  let current = root;
  for (const piece of relative.split('/')) {
    if (!piece || piece === '.' || piece === '..') fail('unsafe output directory');
    current = path.join(current, piece);
    if (!fs.existsSync(current)) fs.mkdirSync(current);
    const stat = fs.lstatSync(current);
    if (stat.isSymbolicLink() || !stat.isDirectory()) fail('owned output directory is linked or invalid');
  }
  return current;
}
function canonicalTests(value) {
  const sorted = (item) => Array.isArray(item) ? item.map(sorted) : item && typeof item === 'object'
    ? Object.fromEntries(Object.keys(item).sort().map((key) => [key, sorted(item[key])])) : item;
  return `${JSON.stringify(sorted(value), null, 2)}\n`;
}

async function main() {
  const argv = process.argv.slice(2);
  const id = argv.shift();
  if (!/^[a-z][a-z0-9-]{0,63}$/.test(id ?? '')) fail('invalid command ID');
  const outputRoot = ownedDirectory(`.portfolio-ci/${id}`);
  const oldResult = path.join(outputRoot, 'result.json');
  if (fs.existsSync(oldResult)) { regularFile(oldResult); fs.rmSync(oldResult); }
  let python;
  if (argv.length) {
    if (argv.length !== 2 || argv[0] !== '--python') fail('unsupported helper arguments');
    python = path.resolve(root, argv[1]); regularFile(python);
  }
  const planFile = fileURLToPath(new URL('./portfolio-tests.json', import.meta.url));
  regularFile(planFile);
  const planBytes = fs.readFileSync(planFile);
  const plan = validateTestPlan(parseStrictJson(planBytes), { cloneRoot: root });
  const command = plan.commands.find((item) => item.id === id);
  if (!command) fail('unknown declared command');
  const environmentRoot = ownedDirectory(`.portfolio-ci/${id}/environment`);
  const env = createChildEnvironment(environmentRoot);
  let executable, args;
  if (command.tool === 'python') {
    if (!python) fail('selected Python runtime missing');
    executable = python;
    if (command.phase === 'setup') args = command.args;
    else {
      const hook = fileURLToPath(new URL('./portfolio_pytest.py', import.meta.url)); regularFile(hook);
      args = [hook, path.join(outputRoot, 'pytest-report.json'), ...command.args.slice(2)];
      fs.rmSync(path.join(outputRoot, 'pytest-report.json'), { force: true });
    }
  } else if (command.tool === 'node') {
    executable = process.execPath;
    args = ['--test', '--test-reporter=tap', ...command.args.slice(1).filter((arg) => arg !== '--test-reporter=tap')];
  } else {
    executable = process.execPath;
    const npm = process.platform === 'win32' ? path.join(path.dirname(executable), 'node_modules/npm/bin/npm-cli.js')
      : path.join(path.dirname(path.dirname(executable)), 'lib/node_modules/npm/bin/npm-cli.js');
    regularFile(npm); args = [npm, ...command.args];
  }
  const receipt = await runOwnedProcess(executable, args, { cwd: root, env, timeoutSeconds: command.timeoutSeconds });
  fs.writeFileSync(path.join(outputRoot, 'stdout.log'), receipt.stdout);
  fs.writeFileSync(path.join(outputRoot, 'stderr.log'), receipt.stderr);
  // Forward complete bytes to the hosted log. A leak in either stream remains
  // visible to the release CI-log scanner; there is no redaction or truncation.
  process.stdout.write(receipt.stdout); process.stderr.write(receipt.stderr);
  if (receipt.timedOut || !receipt.terminationVerified || receipt.error || receipt.exitCode !== 0) fail('command failed or its owned timeout tree was not verified');
  const outputs = [];
  validateTestPlan(plan, { cloneRoot: root });
  for (const output of command.outputs) {
    const filename = path.join(root, ...output.path.split('/')); regularFile(filename);
    const bytes = fs.readFileSync(filename);
    const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    if (text.includes('\0')) fail('retained output is not supported text');
    if (output.context === 'json') parseStrictJson(text);
    outputs.push({ path: output.path, context: output.context, sha256: createHash('sha256').update(bytes).digest('hex') });
    process.stdout.write(`\nDeclared ${output.context} output: ${output.path}\n`);
    process.stdout.write(bytes);
  }
  let summary = { pass: 0, skip: 0, fail: 0, tests: [] };
  if (command.phase === 'test') {
    summary = command.parser === 'node'
      ? parseNodeTap(new TextDecoder('utf-8', { fatal: true }).decode(receipt.stdout))
      : parsePytestReport(fs.readFileSync(path.join(outputRoot, 'pytest-report.json')));
    if (command.parser === 'node') {
      for (const record of summary.tests) {
        const [ordinals, names] = JSON.parse(record.testId);
        if (ordinals.length !== 1 || names.length !== 1) continue;
        const candidate = path.resolve(root, names[0]);
        const relative = path.relative(root, candidate);
        if (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative)
          && /\.(?:[cm]?[jt]sx?)$/i.test(candidate) && fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
          fail('implicit Node file result does not prove registered tests');
        }
      }
    }
    if (summary.fail || !summary.pass) fail('test failure or zero passing tests');
    const expected = plan.declaredSkips.filter((skip) => skip.commandId === id).map((skip) => skip.testId).sort();
    const actual = summary.tests.filter((record) => record.outcome === 'skip').map((record) => record.testId).sort();
    if (JSON.stringify(expected) !== JSON.stringify(actual)) fail('observed skip IDs differ from the exact declared skips');
  }
  const result = { schema: 'portfolio-ci-result-v1', commandId: id,
    manifestTestsSha256: createHash('sha256').update(canonicalTests(plan)).digest('hex'),
    exitCode: receipt.exitCode, timeoutSeconds: command.timeoutSeconds, outputs, ...summary };
  fs.writeFileSync(path.join(outputRoot, 'result.json'), `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`\nCI evidence ${JSON.stringify(result)}\n`);
}

main().catch((error) => {
  // No source file contents or argument values enter helper failure details.
  process.stderr.write(`\n${error.message.startsWith('CI evidence refused:') || error.message.startsWith('Invalid precheck')
    ? error.message : 'CI evidence refused: unreadable or invalid declared input/output'}\n`);
  process.exitCode = 1;
});
