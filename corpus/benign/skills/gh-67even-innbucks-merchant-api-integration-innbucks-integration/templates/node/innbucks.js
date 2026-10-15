// InnBucks Merchant API client. Node.js 18+ (built-in fetch). Amounts are integer cents.
const cfg = {
  baseUrl: (process.env.INNBUCKS_BASE_URL || '').replace(/\/+$/, ''),
  apiKey: process.env.INNBUCKS_API_KEY,
  username: process.env.INNBUCKS_USERNAME,
  password: process.env.INNBUCKS_PASSWORD,
  environment: process.env.INNBUCKS_ENV || 'test',
  tokenTtlMs: Number(process.env.INNBUCKS_TOKEN_TTL || 840) * 1000,
};

let token = null;
let tokenAt = 0;
export let lastTraceId = null;

export class InnBucksError extends Error {
  constructor(message, { response = {}, traceId = null, httpStatus = null } = {}) {
    super(message);
    Object.assign(this, { response, traceId, httpStatus });
  }
}

async function request(method, path, body, bearer) {
  const headers = { 'X-Api-Key': cfg.apiKey, Accept: 'application/json' };
  if (bearer) headers.Authorization = `Bearer ${bearer}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const res = await fetch(cfg.baseUrl + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(30_000),
  });
  lastTraceId = res.headers.get('x-trace-id');
  const text = await res.text();
  let json = {};
  try { json = text ? JSON.parse(text) : {}; } catch { json = { raw: text }; }
  return { status: res.status, json };
}

export async function login(fresh = false) {
  if (!fresh && token && Date.now() - tokenAt < cfg.tokenTtlMs) return token;
  const { status, json } = await request('POST', '/auth/third-party',
    { username: cfg.username, password: cfg.password });
  if (!ok(json) || !json.accessToken) {
    throw new InnBucksError(`InnBucks login failed: ${message(json)}`,
      { response: json, traceId: lastTraceId, httpStatus: status });
  }
  token = json.accessToken;
  tokenAt = Date.now();
  return token;
}

async function send(method, path, body) {
  let res = await request(method, path, body, await login());
  if (res.status === 401) res = await request(method, path, body, await login(true)); // retry once
  if (res.status >= 400) {
    throw new InnBucksError(`InnBucks HTTP ${res.status}: ${message(res.json)}`,
      { response: res.json, traceId: lastTraceId, httpStatus: res.status });
  }
  return res.json;
}

function cents(amount) {
  if (!Number.isInteger(amount) || amount <= 0) {
    throw new TypeError('Amounts are positive integers in cents: 450 = 4.50');
  }
  return amount;
}

function currency(c) {
  const up = String(c).toUpperCase();
  if (!['USD', 'ZWG'].includes(up)) throw new TypeError('currency must be USD or ZWG');
  return up;
}

// ---- codes ---------------------------------------------------------------

export function generateCode({ amount, currency: cur = 'USD', reference, narration, type = 'PAYMENT' }) {
  if (!['PAYMENT', 'WITHDRAWAL'].includes(type)) throw new TypeError('type must be PAYMENT or WITHDRAWAL');
  return send('POST', '/api/code/generate',
    { reference, narration, currency: currency(cur), amount: cents(amount), type });
}

export function inquireCode(code, reference) {
  return send('POST', '/api/code/inquiry', reference ? { reference, code } : { code });
}

// ---- agent services ----------------------------------------------------

export function linkedAccount(msisdn, cur = 'USD') {
  return send('GET', `/api/v1/account/msisdn/${encodeURIComponent(msisdn)}/details?currency=${currency(cur)}`);
}

export function deposit({ destinationAccount, amount, currency: cur, reference, narration, type }) {
  const body = { reference, currency: currency(cur), amount: cents(amount), narration, destinationAccount };
  if (type) body.type = type;
  return send('POST', '/api/transaction/deposit', body);
}

export function depositInquiry({ accountNumber, originalReference, inquiryReference }) {
  return send('POST', '/bank/api/transaction/inquiry', {
    accountNumber,
    participantReference: inquiryReference,
    originalParticipantReference: originalReference,
  });
}

export function reverseDeposit({ destinationAccount, amount, currency: cur, originalReference, reversalReference }) {
  return send('POST', '/api/transaction/reversal/v2', {
    amount: cents(amount),
    currency: currency(cur),
    type: 'CREDIT',
    destinationAccount,
    participantReference: reversalReference,
    originalParticipantReference: originalReference,
  });
}

export function bankChange({ msisdn, amount, currency: cur = 'USD', reference, narration }) {
  if (currency(cur) === 'USD' && cents(amount) > 500) throw new RangeError('Bank change is limited to 500 cents (US$5.00)');
  return send('POST', '/api/transaction/bankChange',
    { reference, currency: currency(cur), amount, narration, destinationMsisdn: msisdn });
}

export function utilityPayment({ provider, product, destinationAccount, amount, currency: cur, reference, narration = '', additionalData = {} }) {
  return send('POST', '/api/utility/provider/payment', {
    provider, providerProduct: product, amount: cents(amount), currency: currency(cur),
    reference, narration, destinationAccount, additionalData,
  });
}

export function statement({ accountNumber, currency: cur, start, end }) {
  return send('POST', '/api/account/fullStatement',
    { accountNumber, currency: currency(cur), startDateTime: start, endDateTime: end });
}

// ---- helpers ---------------------------------------------------------------

export function ok(body) {
  return ['00', '000'].includes(body?.responseCode);
}

export function message(body) {
  return body?.responseMsg ?? body?.responseDescription ?? 'no message';
}

/** 'new' | 'claimed' | 'paid' | 'expired' | 'timed_out' | null */
export function codeStatus(body) {
  const s = String(body?.status ?? '').toLowerCase().replace(/[\s_-]+/g, '');
  return { new: 'new', claimed: 'claimed', paid: 'paid', expired: 'expired', timedout: 'timed_out' }[s] ?? null;
}

export const isPaid = (body) => ok(body) && ['claimed', 'paid'].includes(codeStatus(body));
export const isFinal = (body) => ok(body) && ['claimed', 'paid', 'expired', 'timed_out'].includes(codeStatus(body));

export function deepLink(code) {
  const scheme = cfg.environment === 'production' ? 'com.innbucks.customer' : 'zw.co.innbucksnova.test';
  return `${scheme}://purchase?paymentToken=${encodeURIComponent(code)}`;
}

export function qrDataUri(body) {
  const qr = body?.qrCode;
  if (!qr) return null;
  return qr.startsWith('data:') ? qr : `data:image/png;base64,${qr}`;
}

/** Check a code every intervalMs (30 s by default) until final, or give up after maxMs. */
export async function waitForCode(code, { intervalMs = 30_000, maxMs = 11 * 60_000 } = {}) {
  const started = Date.now();
  for (;;) {
    await new Promise((r) => setTimeout(r, intervalMs));
    let body = {};
    try { body = await inquireCode(code); } catch { /* try again at the next check */ }
    if (isFinal(body)) return body;
    if (Date.now() - started >= maxMs) return { ...body, status: body.status ?? null, unknown: true };
  }
}
