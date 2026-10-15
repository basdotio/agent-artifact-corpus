// Minimal obs-websocket v5 client.  OBS_WS_PASSWORD=... node obs.js <Request> '<json>' [<Request> '<json>' ...]
// Requests run in order; each response prints as one JSON line.
const crypto = require('crypto');
let WS = globalThis.WebSocket;
if (!WS) {
  try { WS = require('ws'); } catch (e) {
    console.error('Needs Node 22+ (built-in WebSocket) or `npm i ws` next to this script.'); process.exit(1);
  }
}
const url = process.env.OBS_WS_URL || 'ws://127.0.0.1:4455';
const pass = process.env.OBS_WS_PASSWORD || '';
const reqs = [];
for (let i = 2; i < process.argv.length; i += 2) reqs.push([process.argv[i], JSON.parse(process.argv[i + 1] || '{}')]);
const sha = s => crypto.createHash('sha256').update(s).digest('base64');
const ws = new WS(url);
let next = 0;
const send = () => {
  if (next >= reqs.length) return ws.close();
  const [t, d] = reqs[next];
  ws.send(JSON.stringify({ op: 6, d: { requestType: t, requestId: String(next), requestData: d } }));
};
ws.onmessage = ev => {
  const m = JSON.parse(typeof ev.data === 'string' ? ev.data : ev.data.toString());
  if (m.op === 0) {
    const d = { rpcVersion: 1, eventSubscriptions: 0 };
    if (m.d.authentication) d.authentication = sha(sha(pass + m.d.authentication.salt) + m.d.authentication.challenge);
    ws.send(JSON.stringify({ op: 1, d }));
  } else if (m.op === 2) send();
  else if (m.op === 7) {
    console.log(JSON.stringify({ req: m.d.requestType, status: m.d.requestStatus, data: m.d.responseData }));
    next++; send();
  }
};
ws.onerror = e => { console.error('OBS websocket error:', e.message || e); process.exit(1); };
ws.onclose = ev => {
  if (next < reqs.length) {
    console.error(`OBS closed the connection (code ${ev.code}${ev.code === 4009 ? ': wrong OBS_WS_PASSWORD' : ''}).`);
    process.exit(1);
  }
};
