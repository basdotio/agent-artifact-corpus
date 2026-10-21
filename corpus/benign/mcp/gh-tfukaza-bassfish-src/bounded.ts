import { randomUUID } from 'node:crypto';
import { BassfishError } from './domain.js';

export const pageBytes = 8192;
export const bytes = (value: unknown): number => Buffer.byteLength(JSON.stringify(value));
export function prefix(text: string, budget: number): string {
  let end = Math.min(text.length, Math.max(0, budget));
  while (Buffer.byteLength(text.slice(0, end)) > budget) end--;
  if (end && /[\uD800-\uDBFF]/.test(text[end - 1]!)) end--;
  return text.slice(0, end);
}

/** Short, owner-scoped cursors pin already captured pages, never a writer turn. */
export class ReplyPages {
  private readonly pending = new Map<
    string,
    { owner: string; pages: Record<string, unknown>[]; at: number; next?: string }
  >();
  close(owner: string): void {
    for (const [token, item] of this.pending) if (item.owner === owner) this.pending.delete(token);
  }
  capture(
    owner: string,
    base: Record<string, unknown>,
    rows: Array<{ section: string; value: unknown }>,
    tail: Record<string, unknown> = {},
  ): Record<string, unknown> {
    const pages: Record<string, unknown>[] = [];
    let page: Record<string, unknown> = { ...base };
    for (const row of rows) {
      const items = (page[row.section] as unknown[] | undefined) ?? [];
      const next = { ...page, [row.section]: [...items, row.value] };
      if (
        bytes(next) > pageBytes - 400 &&
        items.length + Object.keys(page).filter(k => Array.isArray(page[k])).length > 0
      ) {
        pages.push(page);
        page = { ...base };
      }
      const values = (page[row.section] as unknown[] | undefined) ?? [];
      if (bytes({ ...page, [row.section]: [...values, row.value] }) > pageBytes - 400)
        throw new BassfishError(
          'RESPONSE_TOO_LARGE',
          'Use a targeted paginated read for this entry.',
        );
      page[row.section] = [...values, row.value];
    }
    pages.push({ ...page, ...tail });
    if (pages.length === 1) return { nextCursor: null, ...pages[0] };
    this.prune();
    const token = randomUUID();
    this.pending.set(token, { owner, pages: pages.slice(1), at: Date.now() });
    return { ...pages[0], nextCursor: token };
  }
  read(owner: string, token: string): Record<string, unknown> {
    this.prune();
    const item = this.pending.get(token);
    if (!item || item.owner !== owner)
      throw new BassfishError(
        'INVALID_CURSOR',
        'Read cursor expired or belongs to another session.',
      );
    // A cursor is replayable: losing a response does not skip its page.
    const page = item.pages[0]!;
    let nextCursor: string | null = (page.nextCursor as string | null) ?? null;
    if (item.pages.length > 1) {
      nextCursor = item.next ??= randomUUID();
      if (!this.pending.has(nextCursor))
        this.pending.set(nextCursor, {
          owner: item.owner,
          at: item.at,
          pages: item.pages.slice(1),
        });
    }
    return { ...page, nextCursor };
  }
  private prune(): void {
    for (const [token, item] of this.pending)
      if (Date.now() - item.at > 3600000) this.pending.delete(token);
    while (this.pending.size > 10000) this.pending.delete(this.pending.keys().next().value!);
  }
}
