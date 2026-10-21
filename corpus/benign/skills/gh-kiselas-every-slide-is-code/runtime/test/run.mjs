// Runs every runtime/test/*.test.mjs with node:test. A directory argument to `node --test` behaves differently
// across Node versions (18/20 walk it and would also run browser.check.mjs), so the files are listed here.
// Usage: node runtime/test/run.mjs [extra node --test flags]
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const files = fs.readdirSync(here).filter(f => f.endsWith('.test.mjs')).sort().map(f => path.join(here, f));
if (!files.length) { console.error('no *.test.mjs files in ' + here); process.exit(1); }
const r = spawnSync(process.execPath, ['--test', ...process.argv.slice(2), ...files], { stdio: 'inherit' });
process.exit(r.status ?? 1);
