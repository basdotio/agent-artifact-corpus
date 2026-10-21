import { createHmac } from 'node:crypto';
import { z } from 'zod';

/**
 * A TOTP seed is an optional, user-supplied second-factor credential.  It is
 * kept separate from the password record and is only ever used in the local
 * authorization window.  No code or seed is sent to an LMS API.
 */
export const TotpRecordSchema = z.object({
  version: z.literal(1),
  secret: z.string().regex(/^[A-Z2-7]{16,128}$/),
  algorithm: z.enum(['SHA1', 'SHA256', 'SHA512']),
  digits: z.union([z.literal(6), z.literal(8)]),
  period: z.union([z.literal(15), z.literal(30), z.literal(60)]),
}).strict();
export type TotpRecord = z.infer<typeof TotpRecordSchema>;

const base32 = /^[A-Z2-7]+=*$/;

/** Accept a raw seed or an otpauth:// URI copied from an authenticator setup. */
export function parseTotpSecret(input: string): Omit<TotpRecord, 'version'> {
  let value = input.trim();
  let algorithm: TotpRecord['algorithm'] = 'SHA1';
  let digits: TotpRecord['digits'] = 6;
  let period: TotpRecord['period'] = 30;
  if (value.toLowerCase().startsWith('otpauth://')) {
    const uri = new URL(value);
    if (uri.protocol !== 'otpauth:' || uri.hostname.toLowerCase() !== 'totp' || uri.searchParams.has('counter')) throw new Error('Only TOTP otpauth URIs are supported.');
    value = uri.searchParams.get('secret') ?? '';
    const rawAlgorithm = (uri.searchParams.get('algorithm') ?? 'SHA1').toUpperCase();
    const rawDigits = Number(uri.searchParams.get('digits') ?? '6');
    const rawPeriod = Number(uri.searchParams.get('period') ?? '30');
    if (!['SHA1', 'SHA256', 'SHA512'].includes(rawAlgorithm) || ![6, 8].includes(rawDigits) || ![15, 30, 60].includes(rawPeriod)) throw new Error('Unsupported TOTP parameters.');
    algorithm = rawAlgorithm as TotpRecord['algorithm']; digits = rawDigits as TotpRecord['digits']; period = rawPeriod as TotpRecord['period'];
  }
  const secret = value.replace(/[\s-]/g, '').replace(/=+$/g, '').toUpperCase();
  if (!base32.test(`${secret}=`) || secret.length < 16 || secret.length > 128 || secret.length % 8 === 1) throw new Error('The TOTP seed must be a valid Base32 secret.');
  return { secret, algorithm, digits, period };
}

function decodeBase32(value: string): Buffer {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = 0; let buffer = 0; const bytes: number[] = [];
  for (const char of value) {
    const n = alphabet.indexOf(char);
    if (n < 0) throw new Error('Invalid Base32 secret.');
    buffer = (buffer << 5) | n; bits += 5;
    if (bits >= 8) { bits -= 8; bytes.push((buffer >>> bits) & 0xff); }
  }
  return Buffer.from(bytes);
}

export function totpCode(record: TotpRecord, now = Date.now()): string {
  const counter = Math.floor(now / 1000 / record.period);
  const message = Buffer.alloc(8); message.writeBigUInt64BE(BigInt(counter));
  const digest = createHmac(record.algorithm.toLowerCase(), decodeBase32(record.secret)).update(message).digest();
  const offset = digest[digest.length - 1]! & 0x0f;
  const binary = ((digest[offset]! & 0x7f) << 24) | (digest[offset + 1]! << 16) | (digest[offset + 2]! << 8) | digest[offset + 3]!;
  return String(binary % (10 ** record.digits)).padStart(record.digits, '0');
}
