/* Guarded TypeScript v2 MCP stdio server for the additive frozen matrix. */
const crypto = require('node:crypto');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const {
  McpServer, inputRequired, acceptedContent, createRequestStateCodec,
  fromJsonSchema,
} = require('@modelcontextprotocol/server');
const { serveStdio } = require('@modelcontextprotocol/server/stdio');

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}
function positive(name) {
  const value = Number(required(name));
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be positive finite`);
  return value;
}
const settings = {
  db: required('WIRE_SERVER_DB'), backend: required('WIRE_BACKEND_ID'),
  principal: required('WIRE_PRINCIPAL'), now: Number(required('WIRE_CLOCK_EPOCH')),
  authorityTtl: positive('WIRE_AUTHORITY_TTL'),
  replayTtl: positive('WIRE_REPLAY_RETENTION_TTL'),
  sdkTtl: positive('WIRE_REQUEST_STATE_TTL'),
  stateKey: Buffer.from(required('WIRE_STATE_KEY_HEX'), 'hex'),
  fingerprintKey: Buffer.from(required('WIRE_FINGERPRINT_KEY_HEX'), 'hex'),
  fault: process.env.WIRE_FAULT || '',
};
if (!Number.isInteger(settings.now) || !Number.isFinite(settings.now)) throw new Error('clock must be finite integer');
if (settings.stateKey.length < 32 || settings.fingerprintKey.length < 32) throw new Error('keys must be at least 32 bytes');
Date.now = () => settings.now * 1000;
const codec = createRequestStateCodec({
  key: settings.stateKey, ttlSeconds: settings.sdkTtl,
  bind: () => settings.principal,
});

const bridgeScript = path.join(__dirname, 'typescript_guarded_bridge.py');
function bridge(value) {
  const allowed = [
    'PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'SYSTEMROOT', 'PYTHONPATH', 'COVERAGE_PROCESS_CONFIG',
    'WIRE_SERVER_DB', 'WIRE_BACKEND_ID', 'WIRE_PRINCIPAL', 'WIRE_CLOCK_EPOCH',
    'WIRE_FINGERPRINT_KEY_HEX', 'WIRE_FAULT',
  ];
  const env = Object.fromEntries(allowed.filter(name => process.env[name] !== undefined).map(name => [name, process.env[name]]));
  const child = spawnSync('python3', [bridgeScript], {
    input: JSON.stringify(value), encoding: 'utf8', env, timeout: 8000, maxBuffer: 131072,
  });
  if (child.error || child.status !== 0) {
    const lastLine = (child.stderr || '').trim().split('\n').at(-1) || '';
    throw new Error(`bridge machinery failure: ${child.error?.message || child.status}; ${lastLine.slice(0, 160)}`);
  }
  let parsed;
  try { parsed = JSON.parse(child.stdout); } catch { throw new Error('bridge returned invalid JSON'); }
  if (!parsed || typeof parsed !== 'object') throw new Error('bridge returned invalid response');
  if (!parsed.ok) {
    const classes = {
      OperationConflict: 'operation_conflict',
      OperationAuthorityExpired: 'operation_authority_expired',
      OperationRetentionExpired: 'operation_retention_expired',
      OperationInProgress: 'operation_in_progress',
      ValueError: 'invalid_application_request',
      TypeError: 'invalid_application_request',
    };
    throw new Error(classes[parsed.error] || 'bridge_error');
  }
  return parsed.result;
}

const server = new McpServer(
  { name: 'typescript-guarded-wire-reference', version: '0.0.1' },
  { capabilities: { tools: {} }, requestState: { verify: codec.verify } },
);

// Ensure the shared SQLite schema exists before separate workers reach their barrier.
// This read-only lookup creates no operation or effect row.
bridge({ op: 'status', operation_id: '__startup__' });

server.registerTool('get_operation_status', {
  inputSchema: fromJsonSchema({
    type: 'object', properties: { operation_id: { type: 'string' } }, required: ['operation_id'],
  }),
}, async ({ operation_id }) => {
  if (typeof operation_id !== 'string' || !operation_id) throw new Error('operation_id required');
  const status = bridge({ op: 'status', operation_id });
  return { content: [{ type: 'text', text: JSON.stringify(status) }], structuredContent: status };
});

server.registerTool('create_guarded_issue', {
  inputSchema: fromJsonSchema({
    type: 'object',
    properties: {
      operation_id: { type: 'string' }, title: { type: 'string' },
      mode: { type: 'string', enum: ['atomic', 'partial'] },
    },
    required: ['operation_id', 'title'],
  }),
}, async ({ operation_id, title, mode }, ctx) => {
  if (typeof operation_id !== 'string' || !operation_id || typeof title !== 'string' || !title) {
    throw new Error('operation_id and title required');
  }
  mode = mode || 'atomic';
  const responses = ctx.mcpReq.inputResponses;
  if (responses === undefined) {
    if (ctx.mcpReq.requestState() !== undefined) throw new Error('requestState without input responses');
    const state = {
      v: 1, operation_id, title, mode, nonce: crypto.randomBytes(16).toString('hex'),
      issued_at: settings.now, authority_expires_at: settings.now + settings.authorityTtl,
      replay_expires_at: settings.now + settings.replayTtl,
    };
    return inputRequired({
      inputRequests: { body: inputRequired.elicit({
        message: `Body for ${title}?`,
        requestedSchema: { type: 'object', properties: { body: { type: 'string' } }, required: ['body'] },
      }) },
      requestState: await codec.mint(state, ctx),
    });
  }
  const state = ctx.mcpReq.requestState();
  if (state === undefined) throw new Error('unsupported continuation: input responses require requestState');
  if (state.operation_id !== operation_id || state.title !== title || state.mode !== mode) {
    throw new Error('requestState arguments mismatch');
  }
  if (!responses || typeof responses !== 'object' || Array.isArray(responses)) {
    throw new Error('invalid input responses');
  }
  if (!Object.hasOwn(responses, 'body') || responses.body === null) {
    if (settings.now >= state.authority_expires_at) throw new Error('operation_authority_expired');
    return inputRequired({
      inputRequests: { body: inputRequired.elicit({
        message: `Body for ${title}?`,
        requestedSchema: { type: 'object', properties: { body: { type: 'string' } }, required: ['body'] },
      }) },
      requestState: await codec.mint(state, ctx),
    });
  }
  const accepted = acceptedContent(responses, 'body');
  const bodyResponse = responses.body;
  const content = bodyResponse?.content;
  if (!accepted || typeof accepted.body !== 'string' || !bodyResponse ||
      typeof bodyResponse !== 'object' || Array.isArray(bodyResponse) ||
      !Object.hasOwn(bodyResponse, 'action') || !Object.hasOwn(bodyResponse, 'content') ||
      bodyResponse.action !== 'accept' ||
      !content || typeof content !== 'object' || Array.isArray(content) ||
      typeof content.body !== 'string') {
    throw new Error('body response must be accepted text');
  }
  const body = accepted.body;
  const result = bridge({
    op: 'apply', operation_id, title, mode, body, state,
    responses: { body: { _meta: null, action: 'accept', content: { body } } },
  });
  if (settings.fault === 'drop-after-commit' && result.replayed === false) process.exit(70);
  return { content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result };
});

serveStdio(() => server);
