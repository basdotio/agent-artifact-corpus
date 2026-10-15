// Capture REPL: keeps logged-in browser pages alive between steps so states built in step N are still there in N+1.
//   MANUAL_CONFIG=<ws>/manual.json node repl.mjs            (listens on 127.0.0.1:9555)
//   curl -s -H "x-repl-token: $(cat <ws>/.repl-token)" --data-binary @<ws>/steps/10-x.js localhost:9555
// Each POST body runs as an async function body with { P, session, shot, aria, cap, slide }:
//   P       — plain object that persists across calls (pages, helpers from steps/00-lib.js)
//   aria    — aria snapshot of `main`: read it to find role/name locators before writing marks
//   slide() — upsert a manifest.json entry by its `shot` name
import http from 'http';
import { randomBytes } from 'crypto';
import { writeFileSync, rmSync } from 'fs';
import path from 'path';
import * as cap from './cap.mjs';
import { upsertSlide } from './manifest.mjs';

const P = {};
const MANIFEST = path.join(cap.WS, 'manifest.json');
const aria = async (page, sel = 'main') => page.locator(sel).first().ariaSnapshot();
const slide = (o) => upsertSlide(MANIFEST, o);
const AsyncFunction = (async () => {}).constructor;
const PORT = Number(process.env.MANUAL_REPL_PORT ?? 9555);
// This server runs arbitrary code with a logged-in browser in reach, so loopback alone is not enough: any local
// process or a page in the browser could POST to it. Require a per-run token, written 0600 into the workspace.
const TOKEN = randomBytes(24).toString('hex');
const TOKEN_FILE = path.join(cap.WS, '.repl-token');
writeFileSync(TOKEN_FILE, TOKEN, { mode: 0o600 });
process.on('exit', () => rmSync(TOKEN_FILE, { force: true }));
process.on('SIGINT', () => process.exit(130));
http.createServer(async (req, res) => {
  if (req.method !== 'POST' || req.headers['x-repl-token'] !== TOKEN) { res.statusCode = 403; return res.end('forbidden'); }
  let body = ''; for await (const c of req) body += c;
  try {
    const fn = new AsyncFunction('P', 'session', 'shot', 'aria', 'cap', 'slide', body);
    const r = await fn(P, cap.session, cap.shot, aria, cap, slide);
    res.end(typeof r === 'string' ? r : (JSON.stringify(r, null, 1) ?? 'ok'));
  } catch (e) { res.end('ERR ' + (e.stack || e)); }
}).listen(PORT, '127.0.0.1', () => console.log(`repl on ${PORT} (workspace ${cap.WS})`));
