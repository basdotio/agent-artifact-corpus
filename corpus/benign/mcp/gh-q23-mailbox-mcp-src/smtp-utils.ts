import type { ReplyContext } from "./types";

function normalizeAddressKey(address: string): string {
  return address.trim().toLowerCase();
}

export function dedupeAddresses(
  addresses: string[],
  excluded: string[] = []
): string[] {
  const seen = new Set(excluded.map(normalizeAddressKey));
  const result: string[] = [];

  for (const address of addresses) {
    const trimmed = address.trim();
    if (!trimmed) {
      continue;
    }

    const key = normalizeAddressKey(trimmed);
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    result.push(trimmed);
  }

  return result;
}

export function resolveSenderAddress(
  inputFrom: string | undefined,
  mailboxUser: string
): string {
  for (const candidate of [inputFrom, mailboxUser]) {
    if (candidate && candidate.trim()) {
      return candidate.trim();
    }
  }

  throw new Error("Unable to determine sender address");
}

export function normalizeReplySubject(subject: string): string {
  const trimmed = subject.trim() || "(no subject)";
  return /^re:\s*/i.test(trimmed) ? trimmed : `Re: ${trimmed}`;
}

export function buildReplyRecipients(
  context: ReplyContext,
  mailboxUser: string,
  replyAll: boolean
): { to: string[]; cc: string[] } {
  const primary = dedupeAddresses(
    context.replyTo.length > 0 ? context.replyTo : context.from,
    [mailboxUser]
  );

  if (primary.length === 0) {
    throw new Error("Original message does not contain a reply recipient");
  }

  if (!replyAll) {
    return { to: primary, cc: [] };
  }

  const cc = dedupeAddresses(
    [...context.to, ...context.cc],
    [mailboxUser, ...primary]
  );

  return { to: primary, cc };
}

export function buildReplyThreadHeaders(
  context: ReplyContext
): { inReplyTo?: string; references?: string } {
  const references = Array.from(
    new Set([...context.references, context.messageId].filter(Boolean))
  ) as string[];

  return {
    inReplyTo: context.messageId || context.inReplyTo,
    references: references.length > 0 ? references.join(" ") : undefined,
  };
}
