function bad(message) { throw new Error(`Invalid precheck test output: ${message}`); }
function exact(value, keys, label) {
  if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).length !== keys.length || Object.keys(value).some(k => !keys.includes(k))) bad(`${label} has unexpected or missing fields`);
}
function finish(tests, expected) {
  const ids = new Set(), counts = { pass: 0, skip: 0, fail: 0 };
  for (const record of tests) {
    exact(record, ['testId', 'outcome'], 'test record');
    if (typeof record.testId !== 'string' || !record.testId || /[\u0000\r\n]/u.test(record.testId) || ids.has(record.testId) || typeof record.outcome !== 'string' || !Object.hasOwn(counts, record.outcome)) bad('invalid or duplicate test record');
    ids.add(record.testId); counts[record.outcome]++;
  }
  for (const key of ['pass', 'skip', 'fail']) if (!Number.isSafeInteger(expected[key]) || expected[key] < 0 || expected[key] !== counts[key]) bad('contradictory test counts');
  if (!counts.pass) bad('zero passing tests');
  return { ...counts, tests };
}

function rejectDuplicateJsonKeys(text) {
  // JSON.parse has already checked syntax. Tokenize strings as whole tokens so
  // braces and escaped keys inside strings cannot confuse the object stack.
  const contexts = [], tokens = /"(?:\\.|[^"\\])*"|[{}\[\]]/gu;
  for (const match of text.matchAll(tokens)) {
    const token = match[0];
    if (token === '{') contexts.push(new Set());
    else if (token === '[') contexts.push(null);
    else if (token === '}' || token === ']') contexts.pop();
    else if (/^\s*:/u.test(text.slice(match.index + token.length))) {
      const keys = contexts.at(-1), key = JSON.parse(token);
      if (!keys || keys.has(key)) bad('duplicate JSON field');
      keys.add(key);
    }
  }
}

export function parseStrictJson(bytes) {
  try {
    const text = typeof bytes === 'string' ? bytes : new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    const value = JSON.parse(text); rejectDuplicateJsonKeys(text); return value;
  } catch { bad('unreadable or ambiguous JSON'); }
}

export function parsePytestReport(bytes) {
  let report;
  try { report = parseStrictJson(bytes); } catch { bad('unreadable pytest report'); }
  exact(report, ['schema', 'tests', 'pass', 'skip', 'fail'], 'pytest report');
  if (report.schema !== 'portfolio-pytest-report-v1' || !Array.isArray(report.tests)) bad('unknown pytest report schema');
  return finish(report.tests, report);
}

// Node's built-in TAP has one result and details type for each subtest. Parent
// ordinals arrive after their children, so IDs are assigned only after parsing.
export function parseNodeTap(text) {
  if (typeof text !== 'string') bad('missing TAP header');
  text = text.replace(/\r\n/g, '\n');
  if (!text.startsWith('TAP version 13\n') || text.includes('\u0000')) bad('missing TAP header');
  const root = { indent: -4, children: [], plan: null }, stack = [root], all = [], totals = new Map();
  let details = null, lastResult = null;
  for (const raw of text.replace(/\r\n/g, '\n').split('\n').slice(1)) {
    if (!raw.trim()) continue;
    const spaces = raw.match(/^ */u)[0].length, line = raw.slice(spaces);
    if (details) {
      if (spaces < details.indent) bad('structural record inside unterminated TAP details');
      if (spaces === details.indent && line === '...') { if (!details.node.type) bad('missing TAP details type'); details = null; continue; }
      if (spaces === details.indent && /^type:/u.test(line)) {
        if (details.node.type) bad('duplicate TAP details type');
        const match = /^type: '(test|suite)'$/u.exec(line); if (!match) bad('unknown TAP details type'); details.node.type = match[1];
      }
      continue;
    }
    if (line === '---') {
      if (!lastResult || lastResult.type || spaces !== lastResult.indent + 2) bad('orphan TAP details');
      details = { node: lastResult, indent: spaces }; continue;
    }
    const sub = /^# Subtest: (.+)$/u.exec(line);
    if (sub) {
      if (spaces % 4) bad('invalid TAP subtest indentation');
      while (stack.at(-1).indent >= spaces) { if (!stack.at(-1).result) bad('unfinished TAP subtest'); stack.pop(); }
      const parent = stack.at(-1);
      if (spaces !== parent.indent + 4 || parent.plan !== null) bad('invalid TAP subtest parent');
      const node = { name: sub[1], indent: spaces, parent, children: [], result: null, type: null, plan: null };
      parent.children.push(node); all.push(node); stack.push(node); lastResult = null; continue;
    }
    const result = /^(not ok|ok) ([1-9][0-9]*) - (.*)$/u.exec(line);
    if (result) {
      while (stack.at(-1).indent > spaces) { if (!stack.at(-1).result) bad('unfinished nested TAP subtest'); stack.pop(); }
      const node = stack.at(-1);
      if (node === root || node.indent !== spaces || node.result) bad('unexpected or duplicate TAP result');
      const marker = /(?<!\\) # (SKIP|TODO)(?: (.*))?$/u.exec(result[3]);
      const name = marker ? result[3].slice(0, marker.index) : result[3];
      if (name !== node.name || marker?.[1] === 'TODO') bad('ambiguous TAP name or unsupported TODO');
      const ordinal = Number(result[2]);
      if (!Number.isSafeInteger(ordinal) || ordinal !== node.parent.children.indexOf(node) + 1) bad('invalid or duplicate TAP ordinal');
      if (node.children.length && node.plan === null) bad('missing nested TAP plan');
      if (result[1] === 'not ok' && marker) bad('contradictory TAP skip result');
      node.ordinal = ordinal; node.result = marker ? 'skip' : result[1] === 'ok' ? 'pass' : 'fail'; lastResult = node; continue;
    }
    const plan = /^1\.\.([0-9]+)$/u.exec(line);
    if (plan) {
      while (stack.at(-1).indent >= spaces) { if (!stack.at(-1).result) bad('unfinished TAP subtest before plan'); stack.pop(); }
      const parent = stack.at(-1);
      if (parent.indent + 4 !== spaces || parent.plan !== null || Number(plan[1]) !== parent.children.length) bad('contradictory or duplicate TAP plan');
      parent.plan = Number(plan[1]); lastResult = null; continue;
    }
    const summary = /^# (tests|suites|pass|fail|cancelled|skipped|todo) ([0-9]+)$/u.exec(line);
    if (summary) {
      if (spaces || root.plan === null || totals.has(summary[1])) bad('invalid or duplicate TAP summary');
      const value = Number(summary[2]); if (!Number.isSafeInteger(value)) bad('invalid TAP count'); totals.set(summary[1], value); continue;
    }
    if (/^# duration_ms [0-9]+(?:\.[0-9]+)?$/u.test(line) && spaces === 0 && root.plan !== null) continue;
    // Built-in reporter forwards console output as TAP comments. Anything else
    // would make the structural stream ambiguous and is rejected.
    if (line.startsWith('# ') && !/^# (?:tests|suites|pass|fail|cancelled|skipped|todo)\b/u.test(line)) continue;
    bad('unknown TAP record');
  }
  if (details || root.plan === null || all.some(n => !n.result || !n.type)) bad('incomplete TAP report');
  if (totals.size !== 7 || totals.get('cancelled') !== 0 || totals.get('todo') !== 0) bad('missing counts or unsupported cancelled/todo tests');
  const tests = [];
  for (const node of all) {
    if (node.type === 'suite') {
      if (node.result !== 'pass' || node.children.some(n => n.result === 'fail')) bad('nonpassing or contradictory suite');
      continue;
    }
    const chain = []; for (let p = node; p !== root; p = p.parent) chain.unshift(p);
    tests.push({ testId: JSON.stringify([chain.map(p => p.ordinal), chain.map(p => p.name)]), outcome: node.result });
  }
  if (totals.get('tests') !== tests.length || totals.get('suites') !== all.filter(n => n.type === 'suite').length) bad('contradictory tests or suites count');
  return finish(tests, { pass: totals.get('pass'), skip: totals.get('skipped'), fail: totals.get('fail') });
}
