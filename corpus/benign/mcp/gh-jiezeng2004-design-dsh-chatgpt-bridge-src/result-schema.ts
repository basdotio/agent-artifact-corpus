/**
 * Standardized Result Schema & Credential-Safe Introspection.
 * Produces structured, token-efficient summaries without parsing giant assistant texts.
 */
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type { GoalRecord } from './goal-control.js';
import { foldRevisionHistory, goalCardLabel } from './goal-control.js';
import { isTerminalStatus } from './goal.js';
import type { BridgeStatus } from './status.js';
import { foldGoalFacts, type LooseEvent, type ToolFact } from './goal-facts.js';
import { containsSecret } from './redact.js';

export interface ResultSchema {
  status: BridgeStatus;
  goal: {
    goal_id: string;
    revision: number;
    workspace: string;
    started_at?: string;
    finished_at?: string;
    card: string;
    revision_history_folded: boolean;
    revision_history: Array<{
      revision: number;
      previous_revision?: number;
      revision_reason: string;
      created_at: string;
    }>;
  };
  tests: {
    total: number;
    pass: number;
    fail: number;
    skip: number;
    suites: string[];
    evidence_ids: string[];
  };
  changes: {
    changed_files: string[];
    commits: string[];
    tags: string[];
    working_tree?: string;
  };
  artifacts: Array<{
    path: string;
    name?: string;
    hash?: string;
    size?: number;
  }>;
  remote: {
    push_verified?: boolean;
    npm_verified?: boolean;
    github_verified?: boolean;
    details?: string;
  };
  security: {
    secret_leak_check: boolean;
    credential_refs: string[];
    approval_summary?: Record<string, unknown>;
  };
  warnings: string[];
  provenance: {
    session_id: string;
    goal_id: string;
    originating_step?: string;
  };
}

export interface CredentialStatus {
  credentialAvailable: boolean;
  credentialRef: string;
  credentialSource: 'env' | 'credentials_store' | 'runtime' | 'none';
}

const ENV_CREDENTIAL_REFS = [
  'NUBE_API_KEY',
  'DEEPSEEK_API_KEY',
  'OPENAI_API_KEY',
  'ANTHROPIC_API_KEY',
  'DSH_API_KEY',
] as const;

const STORE_NAMED_REFS = new Set<string>(ENV_CREDENTIAL_REFS);
const YAML_KEY = /^([A-Za-z_][\w.-]*)\s*:/;
const SOURCE_RANK: Record<CredentialStatus['credentialSource'], number> = {
  env: 0,
  credentials_store: 1,
  runtime: 2,
  none: 3,
};

const PASS_COUNT_REGEX = /(?:✔|PASS|\bpass(?:ed)?\b)[:\s]*(\d+)/i;
const FAIL_COUNT_REGEX = /(?:✖|FAIL|\bfail(?:ed)?\b)[:\s]*(\d+)/i;
const SKIP_COUNT_REGEX = /(?:ℹ|SKIP|\bskip(?:ped)?\b)[:\s]*(\d+)/i;
const COMMIT_BRACKET = /\[(?:[^\]]+?\s)?([0-9a-f]{7,40})\]/i;
const COMMIT_WORD = /\bcommit\s+([0-9a-f]{7,40})\b/i;
const TAG_COMMAND = /\bgit\s+tag(?:\s+(?:-a|--annotate))?\s+['"]?([^\s'"]+)/i;
const TAG_CREATED = /\b(?:created tag|tag)\s+['"]?([vV]?\d[\w.+-]*)['"]?/i;
const ARTIFACT_FILE = /([^\s"'\\]+\.(?:tgz|tar\.gz|zip|whl))\b/i;
const ARTIFACT_NOTICE = /filename:\s+(\S+\.(?:tgz|tar\.gz|zip))/i;
const SHA_HASH = /\b(?:sha256|sha-256|hash)[:\s=]+([0-9a-f]{32,64})\b/i;
const SIZE_BYTES = /\b(\d+)\s*(?:bytes|B)\b/;
const SIZE_NOTICE = /package size:\s+(\d+(?:\.\d+)?)\s*([kKmMgG])i?B/i;
const SECRET_PATH = /(?:^|[/\\])(?:\.env(?:\..+)?|\.credentials(?:\.ya?ml)?|credentials\.ya?ml|id_rsa|id_ed25519)$/i;

function unique(values: string[]): string[] {
  return [...new Set(values.filter((item) => item.trim() !== ''))];
}

/** Parse test results from tool execution facts. */
function extractTestMetrics(facts: ReturnType<typeof foldGoalFacts>): {
  total: number;
  pass: number;
  fail: number;
  skip: number;
  suites: string[];
} {
  let pass = 0;
  let fail = 0;
  let skip = 0;
  const suites: string[] = [];

  for (const tool of facts.tools) {
    if (tool.command && /\b(?:test|jest|vitest|mocha|node\s+--test)\b/i.test(tool.command)) {
      suites.push(tool.command.trim());
      const text = tool.resultText ?? '';
      const passMatch = text.match(PASS_COUNT_REGEX);
      if (passMatch) pass = Math.max(pass, parseInt(passMatch[1] ?? '0', 10));
      const failMatch = text.match(FAIL_COUNT_REGEX);
      if (failMatch) fail = Math.max(fail, parseInt(failMatch[1] ?? '0', 10));
      const skipMatch = text.match(SKIP_COUNT_REGEX);
      if (skipMatch) skip = Math.max(skip, parseInt(skipMatch[1] ?? '0', 10));

      if (tool.ok && pass === 0 && fail === 0) {
        pass = 1;
      }
    }
  }

  const total = pass + fail + skip;
  return { total, pass, fail, skip, suites };
}

/** Collect all changed files from tool events across turns. */
function collectAllChangedFiles(events: readonly LooseEvent[]): string[] {
  const seen = new Set<string>();
  const paths: string[] = [];
  const EDIT_TOOL_NAMES = new Set([
    'write', 'edit', 'str_replace', 'insert', 'replace', 'apply_patch', 'str-replace-editor',
    'rename', 'move', 'delete', 'rm', 'cp', 'mv',
  ]);
  const PATH_ARG_KEYS = ['file_path', 'path', 'filepath', 'old_path', 'new_path', 'src', 'dest', 'old_file', 'new_file'];

  for (const event of events) {
    if (event.type !== 'tool/call') continue;
    const data = event.data as Record<string, unknown> | undefined;
    if (!data || typeof data.name !== 'string' || !EDIT_TOOL_NAMES.has(data.name)) continue;
    try {
      const args = typeof data.arguments === 'string' ? JSON.parse(data.arguments) : data.arguments;
      if (args && typeof args === 'object') {
        for (const key of PATH_ARG_KEYS) {
          const val = (args as Record<string, unknown>)[key];
          if (typeof val === 'string' && val.trim() !== '' && !seen.has(val)) {
            seen.add(val);
            paths.push(val);
          }
        }
      }
    } catch {
      // ignore
    }
  }
  return paths;
}

export function extractCommitShas(text: string): string[] {
  const out: string[] = [];
  const bracket = text.match(COMMIT_BRACKET);
  if (bracket?.[1]) out.push(bracket[1]);
  const word = text.match(COMMIT_WORD);
  if (word?.[1]) out.push(word[1]);
  return unique(out);
}

export function extractTagNames(command?: string, resultText?: string): string[] {
  const out: string[] = [];
  if (command) {
    const fromCmd = command.match(TAG_COMMAND);
    if (fromCmd?.[1] && fromCmd[1] !== '-a' && fromCmd[1] !== '--annotate') out.push(fromCmd[1]);
  }
  if (resultText) {
    const fromResult = resultText.match(TAG_CREATED);
    if (fromResult?.[1]) out.push(fromResult[1]);
  }
  return unique(out);
}

function parseSize(text: string): number | undefined {
  const notice = text.match(SIZE_NOTICE);
  if (notice) {
    const n = Number(notice[1]);
    const unit = (notice[2] ?? 'k').toLowerCase();
    const mul = unit === 'g' ? 1024 * 1024 * 1024 : unit === 'm' ? 1024 * 1024 : 1024;
    return Math.round(n * mul);
  }
  const bytes = text.match(SIZE_BYTES);
  if (bytes) return parseInt(bytes[1] ?? '0', 10);
  return undefined;
}

export function extractArtifacts(tools: readonly ToolFact[]): ResultSchema['artifacts'] {
  const seen = new Set<string>();
  const artifacts: ResultSchema['artifacts'] = [];
  const add = (path: string, extra?: { hash?: string; size?: number }) => {
    const trimmed = path.trim().replace(/\\/g, '/');
    if (trimmed === '' || seen.has(trimmed)) return;
    seen.add(trimmed);
    const name = trimmed.split('/').pop();
    artifacts.push({
      path: trimmed,
      ...(name === undefined ? {} : { name }),
      ...(extra?.hash === undefined ? {} : { hash: extra.hash }),
      ...(extra?.size === undefined ? {} : { size: extra.size }),
    });
  };

  for (const tool of tools) {
    if (!tool.ok) continue;
    const text = `${tool.command ?? ''}\n${tool.resultText ?? ''}\n${tool.filePath ?? ''}`;
    const hash = text.match(SHA_HASH)?.[1];
    const size = parseSize(text);
    const extra = { ...(hash === undefined ? {} : { hash }), ...(size === undefined ? {} : { size }) };
    const notice = (tool.resultText ?? '').match(ARTIFACT_NOTICE);
    if (notice?.[1]) add(notice[1], extra);
    const file = text.match(ARTIFACT_FILE);
    if (file?.[1]) add(file[1], extra);
    if (tool.filePath && ARTIFACT_FILE.test(tool.filePath)) add(tool.filePath, extra);
  }
  return artifacts;
}

function collectCredentialKeysFromYaml(text: string): string[] {
  const keys: string[] = [];
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (trimmed === '' || trimmed.startsWith('#')) continue;
    const match = trimmed.match(YAML_KEY);
    if (match?.[1]) keys.push(match[1]);
  }
  return keys;
}

function upsertCredential(
  byRef: Map<string, CredentialStatus>,
  ref: string,
  source: CredentialStatus['credentialSource'],
  available: boolean,
): void {
  if (!available) return;
  const next: CredentialStatus = { credentialAvailable: true, credentialRef: ref, credentialSource: source };
  const existing = byRef.get(ref);
  if (existing === undefined || SOURCE_RANK[source] < SOURCE_RANK[existing.credentialSource]) {
    byRef.set(ref, next);
  }
}

/** Inspect availability of provider credentials without returning secret values. */
export function inspectCredentials(input: {
  env?: Record<string, string | undefined>;
  dshHome?: string;
  runtimeKeyConfigured?: boolean;
}): CredentialStatus[] {
  const byRef = new Map<string, CredentialStatus>();
  const env = input.env ?? {};

  for (const ref of ENV_CREDENTIAL_REFS) {
    const value = env[ref];
    upsertCredential(byRef, ref, 'env', typeof value === 'string' && value.trim() !== '');
  }

  const home = input.dshHome?.trim() ?? '';
  if (home !== '') {
    const candidates = [
      join(home, 'credentials.yaml'),
      join(home, '.credentials.yaml'),
      join(home, 'credentials.yml'),
      join(home, '.credentials.yml'),
    ];
    for (const file of candidates) {
      if (!existsSync(file)) continue;
      let text = '';
      try {
        text = readFileSync(file, 'utf8');
      } catch {
        continue;
      }
      const keys = collectCredentialKeysFromYaml(text);
      let named = false;
      for (const key of keys) {
        if (STORE_NAMED_REFS.has(key)) {
          upsertCredential(byRef, key, 'credentials_store', true);
          named = true;
        }
      }
      if (!named && keys.length > 0) {
        upsertCredential(byRef, 'PROVIDER_API_KEY', 'credentials_store', true);
      }
    }
  }

  if (input.runtimeKeyConfigured === true) {
    upsertCredential(byRef, 'RUNTIME_API_KEY', 'runtime', true);
  }

  const results = [...byRef.values()];
  if (results.length === 0) {
    return [{ credentialAvailable: false, credentialRef: 'PROVIDER_API_KEY', credentialSource: 'none' }];
  }
  return results;
}

function scanSecretLeak(facts: ReturnType<typeof foldGoalFacts>, changedFiles: string[]): {
  clean: boolean;
  warnings: string[];
} {
  const warnings: string[] = [];
  for (const tool of facts.tools) {
    const text = `${tool.command ?? ''}\n${tool.resultText ?? ''}`;
    if (containsSecret(text)) {
      warnings.push('Secret-shaped material was present in a tool result and redacted from the wire.');
      break;
    }
  }
  for (const path of changedFiles) {
    if (SECRET_PATH.test(path)) {
      warnings.push(`Secret-named file was written: ${path}. Value is not included.`);
    }
  }
  return { clean: warnings.length === 0, warnings };
}

/** Construct standardized ResultSchema from goal record and session events. */
export function buildResultSchema(input: {
  sessionId: string;
  record?: GoalRecord;
  events?: readonly LooseEvent[];
  status: BridgeStatus;
  workspace: string;
  evidenceIds?: string[];
  warnings?: string[];
  credentialRefs?: string[];
  originatingStep?: string;
  approvalSummary?: Record<string, unknown>;
}): ResultSchema {
  const events = input.events ?? [];
  const facts = foldGoalFacts(events);
  const metrics = extractTestMetrics(facts);
  const changedFiles = collectAllChangedFiles(events);

  const commits: string[] = [];
  const tags: string[] = [];
  let pushVerified = false;
  let npmVerified = false;
  let githubVerified = false;
  let lastStep: string | undefined;

  for (const tool of facts.tools) {
    if (!tool.ok) continue;
    lastStep = tool.kinds.find((kind) => kind !== 'unknown') ?? tool.callId;
    if (tool.kinds.includes('git_push')) pushVerified = true;
    if (tool.kinds.includes('npm_publish')) npmVerified = true;
    if (tool.kinds.includes('github_release')) githubVerified = true;
    if (tool.kinds.includes('git_tag') || (tool.command && TAG_COMMAND.test(tool.command))) {
      tags.push(...extractTagNames(tool.command, tool.resultText));
    }
    if (tool.command && /\bgit\s+commit\b/i.test(tool.command)) {
      const shas = extractCommitShas(tool.resultText ?? '');
      if (shas.length > 0) commits.push(...shas);
      else commits.push('local-commit');
    }
  }

  const leak = scanSecretLeak(facts, changedFiles);
  const history = input.record === undefined ? [] : foldRevisionHistory(input.record);
  const warnings = unique([...(input.warnings ?? []), ...leak.warnings]);

  return {
    status: input.status,
    goal: {
      goal_id: input.record?.goal_id ?? `goal-${input.sessionId}`,
      revision: input.record?.revision ?? 1,
      workspace: input.workspace,
      started_at: input.record?.created_at,
      ...(isTerminalStatus(input.status) ? { finished_at: new Date().toISOString() } : {}),
      card: goalCardLabel({ revision: input.record?.revision ?? 1 }),
      revision_history_folded: history.length > 1,
      revision_history: history,
    },
    tests: {
      ...metrics,
      evidence_ids: input.evidenceIds ?? [],
    },
    changes: {
      changed_files: changedFiles,
      commits: unique(commits),
      tags: unique(tags),
      working_tree: changedFiles.length > 0 ? 'modified' : 'clean',
    },
    artifacts: extractArtifacts(facts.tools),
    remote: {
      push_verified: pushVerified,
      npm_verified: npmVerified,
      github_verified: githubVerified,
    },
    security: {
      secret_leak_check: leak.clean,
      credential_refs: input.credentialRefs ?? [],
      ...(input.approvalSummary === undefined ? {} : { approval_summary: input.approvalSummary }),
    },
    warnings,
    provenance: {
      session_id: input.sessionId,
      goal_id: input.record?.goal_id ?? `goal-${input.sessionId}`,
      ...(input.originatingStep === undefined && lastStep === undefined
        ? {}
        : { originating_step: input.originatingStep ?? lastStep }),
    },
  };
}
