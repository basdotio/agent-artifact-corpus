/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import fs from 'node:fs';

import {debug} from './third_party/index.js';
import type {ToolErrorCode} from './ToolError.js';

const mcpDebugNamespace = 'mcp:log';

const namespacesToEnable = [
  mcpDebugNamespace,
  ...(process.env['DEBUG'] ? [process.env['DEBUG']] : []),
];

const REDACTED = '[REDACTED]';
const SENSITIVE_KEYS = new Set([
  'authorization',
  'proxyauthorization',
  'cookie',
  'setcookie',
  'password',
  'passwd',
  'secret',
  'token',
  'accesstoken',
  'refreshtoken',
  'apikey',
  'clientsecret',
  'requestbody',
  'responsebody',
  'body',
  'headers',
  'function',
  'expression',
  'condition',
  'query',
  'urlfilter',
  'text',
  'localfilepath',
  'outputfile',
  'filepath',
]);

function redactUrl(raw: string): string {
  try {
    const url = new URL(raw);
    if (url.username || url.password) {
      url.username = REDACTED;
      url.password = '';
    }
    for (const key of [...url.searchParams.keys()]) {
      url.searchParams.set(key, REDACTED);
    }
    if (url.hash) {
      url.hash = REDACTED;
    }
    url.pathname = url.pathname.replace(
      /(\/devtools\/browser\/)[^/]+/i,
      `$1${REDACTED}`,
    );
    return url.toString();
  } catch {
    return raw;
  }
}

function redactString(value: string): string {
  return value
    .replace(/\b(?:https?|wss?|ftp):\/\/[^\s"'<>]+/gi, redactUrl)
    .replace(/\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]+/gi, `$1 ${REDACTED}`)
    .replace(
      /([?&](?:access_token|refresh_token|token|api_key|apikey|key|secret|password|auth|sig|signature|x-amz-[^=]+)=)[^&#\s]*/gi,
      `$1${REDACTED}`,
    )
    .replace(/(\/devtools\/browser\/)[^/\s"'<>]+/gi, `$1${REDACTED}`)
    .replace(
      /((?:Local file access|symbolic link|local file output|localFilePath)[^:\n]*:\s*)[^\s]+/gi,
      `$1[REDACTED_PATH]`,
    )
    .replace(
      /(\b(?:open|stat|lstat|realpath|scandir|access|mkdir|unlink|rename|readlink|chmod|truncate)\s+)[`'"]?(?:[a-z]:[\\/]|\/)[^`'"\n]+[`'"]?/gi,
      `$1[REDACTED_PATH]`,
    );
}

export function redactLogValue(value: unknown): unknown {
  if (typeof value === 'string') {
    return redactString(value);
  }
  if (Array.isArray(value)) {
    return value.map(redactLogValue);
  }
  if (value && typeof value === 'object') {
    const output: Record<string, unknown> = {};
    for (const [key, item] of Object.entries(value)) {
      const normalizedKey = key.replace(/[-_]/g, '').toLowerCase();
      output[key] = SENSITIVE_KEYS.has(normalizedKey)
        ? REDACTED
        : redactLogValue(item);
    }
    return output;
  }
  return value;
}

export function formatLogValue(value: unknown): string {
  return JSON.stringify(redactLogValue(value), null, 2);
}

export function formatToolErrorLog(
  toolName: string,
  error: {code: ToolErrorCode; retryable: boolean},
): string {
  return `${toolName} error: code=${error.code} retryable=${error.retryable}`;
}

const defaultDebugLog = debug.log.bind(debug);
debug.log = (...chunks: unknown[]) => {
  defaultDebugLog(...chunks.map(chunk => redactString(String(chunk))));
};

export function saveLogsToFile(fileName: string): fs.WriteStream {
  // Enable overrides everything so we need to add them
  debug.enable(namespacesToEnable.join(','));

  let fd: number | undefined;
  try {
    fd = fs.openSync(
      fileName,
      fs.constants.O_APPEND |
        fs.constants.O_CREAT |
        fs.constants.O_WRONLY |
        fs.constants.O_NOFOLLOW |
        fs.constants.O_NONBLOCK,
      0o600,
    );
    if (!fs.fstatSync(fd).isFile()) {
      throw new Error(`Log destination is not a regular file: ${fileName}`);
    }
    fs.fchmodSync(fd, 0o600);
  } catch (error) {
    if (fd !== undefined) {
      fs.closeSync(fd);
    }
    throw error;
  }
  const logFile = fs.createWriteStream(fileName, {
    fd,
    flags: 'a',
    autoClose: true,
  });
  debug.log = function (...chunks: unknown[]) {
    logFile.write(
      `${chunks.map(chunk => redactString(String(chunk))).join(' ')}\n`,
    );
  };
  logFile.on('error', function (error) {
    console.error(`Error when opening/writing to log file: ${error.message}`);
    logFile.end();
    process.exit(1);
  });
  return logFile;
}

export function warnAboutUnsafeDebugLogging(): void {
  const debugPatterns = process.env['DEBUG']?.split(/[\s,]+/) ?? [];
  if (
    debugPatterns.some(
      pattern =>
        pattern === '*' ||
        /^pw(?::|\*)/i.test(pattern) ||
        pattern.toLowerCase().includes('pw:protocol'),
    )
  ) {
    console.error(
      'Security warning: DEBUG enables Patchright protocol logging, which can expose page content, cookies, script source, and CDP credentials. Use DEBUG=mcp:* for js-reverse-mcp diagnostics.',
    );
  }
}

export const logger = debug(mcpDebugNamespace);
