/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

export interface ConsoleMessageData {
  consoleMessageStableId: number;
  type?: string;
  message?: string;
  argCount?: number;
  args?: string[];
}

const CONSOLE_ARG_SIZE_LIMIT = 2000;
const CONSOLE_MESSAGE_SIZE_LIMIT = 1000;

// The short format for a console message, based on a previous format.
export function formatConsoleEventShort(msg: ConsoleMessageData): string {
  return `msgid=${msg.consoleMessageStableId} [${msg.type}] ${getSizeLimitedString(msg.message ?? '', CONSOLE_MESSAGE_SIZE_LIMIT)} (${msg.argCount ?? msg.args?.length ?? 0} args)`;
}

function getArgs(msg: ConsoleMessageData) {
  const args = [...(msg.args ?? [])];

  // If there is no text, the first argument serves as text (see formatMessage).
  if (!msg.message) {
    args.shift();
  }

  return args;
}

// The verbose format for a console message, including all details.
export function formatConsoleEventVerbose(msg: ConsoleMessageData): string {
  const result = [
    `ID: ${msg.consoleMessageStableId}`,
    `Message: ${msg.type}> ${getSizeLimitedString(msg.message ?? '', CONSOLE_MESSAGE_SIZE_LIMIT)}`,
    formatArgs(msg),
  ].filter(line => !!line);
  return result.join('\n');
}

export function formatConsoleArgValue(arg: unknown): string {
  const value = typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
  return getSizeLimitedString(value, CONSOLE_ARG_SIZE_LIMIT);
}

function getSizeLimitedString(text: string, sizeLimit: number): string {
  if (text.length > sizeLimit) {
    return `${text.slice(0, sizeLimit)}... <truncated ${text.length - sizeLimit} chars>`;
  }
  return text;
}

function formatArgs(consoleData: ConsoleMessageData): string {
  const args = getArgs(consoleData);

  if (!args.length) {
    return '';
  }

  const result = ['### Arguments'];

  for (const [key, arg] of args.entries()) {
    result.push(
      `Arg #${key}: ${getSizeLimitedString(String(arg), CONSOLE_ARG_SIZE_LIMIT)}`,
    );
  }

  return result.join('\n');
}
