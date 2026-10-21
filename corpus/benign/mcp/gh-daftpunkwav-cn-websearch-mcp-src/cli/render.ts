/**
 * @file cli/render
 * @description CLI output rendering: results, status, probe table, and config redaction.
 *
 * Responsibilities:
 * - Render search results as human-readable text (or raw JSON)
 * - Render provider status and the probe table
 * - Redact API keys when printing config snapshots so no code path ever prints a secret
 */

// Rendering layer: only "data -> text"; no network or config parsing. All output touching
// secrets must go through redactedConfig or echo only "configured or not".

import type { GatewayConfig, ProviderName } from '../config.js';
import type { ProbeRow } from '../probe.js';
import type { NormalizedSearchResult } from '../types.js';
import { stripControlChars } from '../errors.js';
import { truncate } from '../normalize.js';

/** Snippet cap for rendering: terminal readability first; full content via --json. */
const SNIPPET_MAX = 160;

/** Failure-note cap in the probe table: one readable column; the full summary is in --json. */
const PROBE_NOTE_MAX = 80;

/**
 * Secret redaction: echo only whether a key is set, never its contents.
 *
 * `providers.*.options` contributes its key names only. It is the one
 * free-form field in the config, and the schema offers nowhere else for an
 * operator to park a credential an adapter needs (a proxy key, for instance),
 * so a value there is as likely to be a secret as not — while both consumers
 * of this snapshot are output people paste into issues and CI logs. Which
 * options resolved is the part a status command actually answers for; the
 * values are not reproduced anywhere.
 */
export function redactedConfig(config: GatewayConfig): Record<string, unknown> {
  const providers: Record<string, unknown> = {};
  for (const [name, p] of Object.entries(config.providers)) {
    providers[name] = {
      enabled: p.enabled,
      priority: p.priority,
      baseUrl: p.baseUrl,
      model: p.model ?? null,
      apiKey: p.apiKey.trim() === '' ? '(unset)' : '(set)',
      timeoutMs: p.timeoutMs ?? null,
      // The comparator makes the order locale-aware and identical on every
      // runtime, where a bare sort() leaves it to whatever collation the
      // build happens to carry — resolveOrder in config.ts sorts the same way.
      options: p.options ? Object.keys(p.options).sort((a, b) => a.localeCompare(b)) : null,
    };
  }
  return {
    strategy: config.strategy,
    order: config.order,
    timeoutMs: config.timeoutMs,
    count: config.count,
    maxProviders: config.maxProviders,
    dedupe: config.dedupe,
    configFile: config.configFile ?? null,
    providers,
  };
}

/** Formats one search result as human-readable text. */
export function formatSearchResult(result: NormalizedSearchResult): string {
  const meta = result._meta;
  const sources = meta.providers?.length ? meta.providers.join(', ') : meta.provider;
  const lines: string[] = [
    `answered by: ${sources}  (${meta.total_latency_ms}ms total, ${result.results.length} result(s))`,
    '',
  ];
  result.results.forEach((item, i) => {
    const source = item.source && meta.providers && meta.providers.length > 1 ? `  [${item.source}]` : '';
    lines.push(`${i + 1}. ${item.title || '(untitled)'}${source}`);
    lines.push(`   ${item.url}`);
    if (item.snippet) lines.push(`   ${truncate(item.snippet, SNIPPET_MAX)}`);
    if (item.published_date) lines.push(`   published: ${item.published_date}`);
  });
  if (meta.answer) {
    lines.push('', 'synthesized answer:', meta.answer);
  }
  if (meta.attempts.length) {
    const trail = meta.attempts
      .map((a) => `${a.provider}:${a.status}(${a.latency_ms}ms)${a.error ? ` ${a.error}` : ''}`)
      .join(' | ');
    lines.push('', `attempts: ${trail}`);
  }
  return lines.join('\n');
}

/** Formats the effective config and provider status (redacted). */
export function formatStatus(config: GatewayConfig, chainNames: string[]): string {
  const inChain = new Set(chainNames);
  // Unlike the JSON surfaces, these two lines are written to the terminal
  // unescaped, and both values come from data the working directory supplies
  // (a config file field, or WEBSEARCH_CONFIG through a .env). A model name or
  // a path carrying an escape sequence would otherwise repaint or forge output
  // lines here — the same class errors.ts strips from upstream text.
  const configFile = stripControlChars(config.configFile ?? '(none)');
  const lines: string[] = [
    `strategy      : ${config.strategy}`,
    `order         : ${config.order.join(' -> ') || '(none)'}`,
    `count (default): ${config.count}`,
    `timeout/attempt: ${config.timeoutMs}ms`,
    `max providers : ${config.maxProviders}`,
    `dedupe        : ${config.dedupe ? 'on' : 'off'}`,
    `config file   : ${configFile}`,
    '',
    'provider   enabled  configured  in-chain  priority  model',
  ];
  for (const name of Object.keys(config.providers) as ProviderName[]) {
    const p = config.providers[name];
    const cells = [
      name.padEnd(10),
      (p.enabled ? 'yes' : 'no').padEnd(8),
      (p.apiKey.trim() !== '' ? 'yes' : 'no').padEnd(11),
      (inChain.has(name) ? 'yes' : 'no').padEnd(9),
      String(p.priority).padEnd(9),
      stripControlChars(p.model ?? '-'),
    ];
    lines.push(cells.join(' '));
  }
  if (!chainNames.length) {
    lines.push('', 'no provider is ready: set an API key (env or config file) to enable searching');
  }
  return lines.join('\n');
}

/** Formats the probe results table. */
export function formatProbeTable(rows: ProbeRow[]): string {
  const lines = ['provider   status  latency  results  note'];
  for (const r of rows) {
    lines.push(
      [
        r.provider.padEnd(10),
        (r.ok ? 'ok' : 'failed').padEnd(7),
        `${r.latency_ms}ms`.padEnd(8),
        String(r.results).padEnd(8),
        r.ok ? r.sample : truncate(r.error, PROBE_NOTE_MAX),
      ].join(' '),
    );
  }
  return lines.join('\n');
}
