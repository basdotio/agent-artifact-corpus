import { Hono } from 'hono';
import {
  RecipeError,
  type RecipeInput,
  type RecipeRow,
  canonicalJson,
  fullRecipe,
  lintRecipeCode,
  listEntry,
  recipeSnapshotDigest,
  validateRecipeInput,
} from './recipe.ts';
import {
  type HumanAuthorization,
  type WorkspaceRole,
  employeeWorkspaceEnabled,
  hasFolderPermission,
  hasWorkspaceRole,
  resolveHumanAuthorization,
} from './workspace-authorization.ts';

export type Env = {
  DB: D1Database;
  // Bearer token. A wrangler secret. NEVER hardcoded, never shipped to a client.
  PANTRY_TOKEN?: string;
  // Optional fixed owner for single-tenant deploys; defaults to the token-derived owner.
  PANTRY_OWNER?: string;
  // Optional multi-owner map: a JSON object { "<bearer-token>": "<owner>" }. A
  // wrangler secret. Each token maps to its own owner for a shared multi-owner
  // deployment. When set, tokens here take precedence; PANTRY_TOKEN stays a fallback.
  PANTRY_TOKENS?: string;
  // Static-site binding. The SAME Worker serves the docs/landing site from
  // ./app/dist for any path the API does not own. Optional so the API logic
  // and its tests run unchanged without an assets binding present.
  APP_ASSETS?: Fetcher;
  PANTRY_SHARED_OWNER?: string;
  PANTRY_ACCESS_SHARE_ALL?: string;
  PANTRY_ACCESS_IDENTITY_HEADER?: string;
  PANTRY_ACCESS_ONLY?: string;
  // Local development only. When set, an unauthenticated request is treated as
  // this Access identity so the Operations UI can be exercised without an edge
  // session. It must never be configured on a deployed environment.
  PANTRY_DEV_ACCESS_IDENTITY?: string;
  PANTRY_EMPLOYEE_WORKSPACE_ENABLED?: string;
  PANTRY_EMPLOYEE_WORKSPACE_SLUG?: string;
  PANTRY_LOCAL_DEVELOPMENT?: string;
  PANTRY_AUTHORIZATION_POLICY_VERSION?: string;
};

// The API paths this Worker owns. Everything else falls through to the static
// site. Mirrors wrangler `assets.run_worker_first`.
function isApiPath(pathname: string): boolean {
  if (pathname === '/health' || pathname === '/recipes' || pathname.startsWith('/api/'))
    return true;
  if (pathname.startsWith('/recipes/')) return true;
  if (pathname.startsWith('/recipe/')) return true;
  return false;
}

type AgentScope = 'recipes:read' | 'recipes:write' | 'usage:report';
type AuthKind = 'access' | 'agent' | 'legacy';
type Vars = {
  owner: string;
  accessIdentity?: string;
  authKind?: AuthKind;
  agentScopes?: AgentScope[];
  workspaceAuthorization?: HumanAuthorization;
};

type AgentCredentialRow = {
  id: string;
  team_id: string;
  principal: string;
  owner_principal: string;
  scopes_json: string;
};

const agentScopes: AgentScope[] = ['recipes:read', 'recipes:write', 'usage:report'];

// Parse the optional PANTRY_TOKENS JSON map into [token, owner] pairs. Returns
// null when unset/empty/malformed so the single-token path remains the fallback.
function parseTokenMap(raw: string | undefined): Array<[string, string]> | null {
  if (!raw?.trim()) return null;
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>;
    const pairs = Object.entries(obj)
      .filter(([token, owner]) => token && typeof owner === 'string' && owner.trim())
      .map(([token, owner]) => [token, (owner as string).toLowerCase()] as [string, string]);
    return pairs.length ? pairs : null;
  } catch {
    return null;
  }
}

// Constant-time string compare. Avoids leaking token length/prefix via timing.
function timingSafeEqual(a: string, b: string): boolean {
  const enc = new TextEncoder();
  const ab = enc.encode(a);
  const bb = enc.encode(b);
  // Compare a fixed-length digest so length differences do not short-circuit.
  let diff = ab.length ^ bb.length;
  const len = Math.max(ab.length, bb.length);
  for (let i = 0; i < len; i++) {
    diff |= (ab[i] ?? 0) ^ (bb[i] ?? 0);
  }
  return diff === 0;
}

function sharedOwner(env: Env): string | null {
  const owner = env.PANTRY_SHARED_OWNER?.trim().toLowerCase();
  return owner && owner.length <= 128 ? owner : null;
}

function requireAccessIdentity(c: {
  get: <K extends keyof Vars>(key: K) => Vars[K];
  json: (object: unknown, status?: number) => Response;
}): Response | string {
  const identity = c.get('accessIdentity');
  return identity ? identity : c.json({ error: 'Cloudflare Access session required' }, 401);
}

function isSameOrigin(request: Request): boolean {
  const origin = request.headers.get('origin');
  return origin === null || origin === new URL(request.url).origin;
}

async function sha256(value: string): Promise<string> {
  const bytes = new Uint8Array(
    await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)),
  );
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function parseAgentScopes(value: unknown): AgentScope[] | null {
  if (!Array.isArray(value) || value.length === 0 || value.length > agentScopes.length) return null;
  const scopes = value.filter(
    (scope): scope is AgentScope =>
      typeof scope === 'string' && agentScopes.includes(scope as AgentScope),
  );
  return scopes.length === value.length && new Set(scopes).size === scopes.length ? scopes : null;
}

function agentScopeForRequest(request: Request): AgentScope | null {
  const pathname = new URL(request.url).pathname;
  if (request.method === 'GET' && (pathname === '/recipes' || pathname.startsWith('/recipe/')))
    return 'recipes:read';
  if (request.method === 'POST' && pathname === '/recipes') return 'recipes:write';
  if (request.method === 'POST' && pathname.endsWith('/attestations')) return 'recipes:write';
  if (request.method === 'DELETE' && pathname.startsWith('/recipe/')) return 'recipes:write';
  if (request.method === 'POST' && pathname.endsWith('/usage')) return 'usage:report';
  return null;
}

function isAgentManagementPath(pathname: string): boolean {
  return (
    pathname === '/api/session' ||
    pathname.startsWith('/api/') ||
    /\/approval(?:-diff)?s?$/.test(pathname)
  );
}

// Echo the request origin so browser/webview callers work, while never using
// the wildcard with credentials. Applied to EVERY response (learned from pulse).
function corsHeaders(origin: string | null): Record<string, string> {
  return {
    'access-control-allow-origin': origin ?? '*',
    'access-control-allow-methods': 'GET, POST, DELETE, OPTIONS',
    'access-control-allow-headers': 'authorization, content-type',
    'access-control-max-age': '86400',
    vary: 'origin',
  };
}

const app = new Hono<{ Bindings: Env; Variables: Vars }>();

// CORS on every response.
app.use('*', async (c, next) => {
  await next();
  const headers = corsHeaders(c.req.header('origin') ?? null);
  for (const [key, value] of Object.entries(headers)) c.header(key, value);
});

// Answer OPTIONS preflight with 204 BEFORE the auth gate (pulse lesson:
// browsers send preflight without the Authorization header).
app.options('*', (c) => {
  const headers = corsHeaders(c.req.header('origin') ?? null);
  return new Response(null, { status: 204, headers });
});

// Health is open (no auth) so uptime checks do not need the secret.
app.get('/health', (c) => c.json({ ok: true, service: 'pantry' }));

app.use('*', async (c, next) => {
  const pathname = new URL(c.req.url).pathname;
  const employeePath = pathname === '/api/session' || pathname.startsWith('/api/workspaces/');
  if (employeeWorkspaceEnabled(c.env) && employeePath) {
    if (!isSameOrigin(c.req.raw))
      return c.json({ error: 'management requests must be same-origin' }, 403);
    const resolved = await resolveHumanAuthorization(c.env.DB, c.env);
    if ('error' in resolved)
      return c.json({ error: resolved.error }, resolved.status as 401 | 403 | 503);
    c.set('owner', resolved.authorization.workspace.id);
    c.set('accessIdentity', resolved.authorization.actor.displayEmail ?? 'access-user');
    c.set('authKind', 'access');
    c.set('workspaceAuthorization', resolved.authorization);
    await next();
    return;
  }
  const accessHeader =
    c.env.PANTRY_ACCESS_IDENTITY_HEADER?.trim() || 'cf-access-authenticated-user-email';
  const accessIdentity =
    c.req.header(accessHeader)?.trim() || c.env.PANTRY_DEV_ACCESS_IDENTITY?.trim();
  if (c.env.PANTRY_ACCESS_SHARE_ALL === 'true' && accessIdentity) {
    const owner = sharedOwner(c.env);
    if (!owner) return c.json({ error: 'pantry shared owner is not configured' }, 503);
    if (!isSameOrigin(c.req.raw))
      return c.json({ error: 'management requests must be same-origin' }, 403);
    c.set('owner', owner);
    c.set('accessIdentity', accessIdentity);
    c.set('authKind', 'access');
    await next();
    return;
  }

  const header = c.req.header('authorization') ?? '';
  const presented = header.startsWith('Bearer ') ? header.slice('Bearer '.length) : '';
  if (presented) {
    const credential = await c.env.DB.prepare(
      'SELECT c.id, c.team_id, i.principal, i.owner_principal, c.scopes_json FROM agent_credentials c JOIN agent_identities i ON i.id = c.agent_identity_id WHERE c.credential_hash = ? AND c.revoked_at IS NULL AND i.revoked_at IS NULL',
    )
      .bind(await sha256(presented))
      .first<AgentCredentialRow>();
    if (credential) {
      let scopes: AgentScope[] | null = null;
      try {
        scopes = parseAgentScopes(JSON.parse(credential.scopes_json));
      } catch {
        scopes = null;
      }
      if (!scopes) return c.json({ error: 'invalid agent credential scopes' }, 403);
      c.set('owner', credential.owner_principal);
      c.set('authKind', 'agent');
      c.set('agentScopes', scopes);
      await next();
      return;
    }
  }

  if (c.env.PANTRY_ACCESS_ONLY === 'true') {
    return c.json({ error: 'Cloudflare Access session required' }, 401);
  }

  const single = c.env.PANTRY_TOKEN;
  const multi = parseTokenMap(c.env.PANTRY_TOKENS);
  let owner: string | null = null;
  if (multi) {
    for (const [token, mappedOwner] of multi) {
      if (presented && timingSafeEqual(presented, token)) owner = mappedOwner;
    }
  }
  if (owner === null && single && presented && timingSafeEqual(presented, single)) {
    owner = (c.env.PANTRY_OWNER ?? 'default').toLowerCase();
  }
  if (owner === null) {
    if (!single && !multi)
      return c.json(
        { error: 'pantry is not configured: agent credentials or explicit legacy tokens required' },
        503,
      );
    return c.json({ error: 'unauthorized' }, 401);
  }
  c.set('owner', owner);
  c.set('authKind', 'legacy');
  await next();
});

app.use('*', async (c, next) => {
  if (c.get('authKind') === 'agent') {
    const pathname = new URL(c.req.url).pathname;
    if (isAgentManagementPath(pathname))
      return c.json({ error: 'agent credentials cannot access management routes' }, 403);
    const requiredScope = agentScopeForRequest(c.req.raw);
    if (!requiredScope || !c.get('agentScopes')?.includes(requiredScope)) {
      return c.json({ error: 'agent credential scope does not permit this request' }, 403);
    }
  }
  await next();
});

function workspaceAuthorization(c: {
  get: <K extends keyof Vars>(key: K) => Vars[K];
  json: (object: unknown, status?: number) => Response;
}): HumanAuthorization | Response {
  const authorization = c.get('workspaceAuthorization');
  return authorization ?? c.json({ error: 'employee workspace authorization required' }, 403);
}

function workspaceSlugMatches(
  c: {
    req: { param: (name: string) => string };
    json: (object: unknown, status?: number) => Response;
  },
  authorization: HumanAuthorization,
): Response | null {
  return c.req.param('workspaceSlug') === authorization.workspace.slug
    ? null
    : c.json({ error: 'workspace does not match authenticated session' }, 403);
}

function handleError(error: unknown): Response {
  if (error instanceof RecipeError) {
    const status = error.code === 'NotFound' ? 404 : error.code === 'Conflict' ? 409 : 400;
    return Response.json({ error: error.message, code: error.code }, { status });
  }
  return Response.json({ error: 'internal error' }, { status: 500 });
}

type RecipeVersionRow = {
  version: number;
  created_at: string;
  capabilities_json: string;
};

type ApprovalRow = {
  id: string;
  owner: string;
  recipe_name: string;
  recipe_version: number;
  recipe_digest: string;
  action: string;
  reason: string | null;
  actor: string;
  source_code: string;
  capabilities_json: string;
  created_at: string;
  receipt_digest: string;
};

type RecipeSubjectRow = {
  owner: string;
  name: string;
  version: number;
  recipe_digest: string | null;
};

type RecipeAttestationRow = {
  owner: string;
  recipe_name: string;
  recipe_version: number;
  recipe_digest: string;
  witness_receipt_sha256: string;
  created_at: string;
};

type WorkspaceRecipeRow = RecipeRow & {
  workspace_id: string;
  folder_id: string;
  created_by_actor_id: string;
  updated_by_actor_id: string;
  legacy_owner: string;
  workspace_recipe_key: string;
  archived_at: string | null;
};

type WorkspaceRecipeVersionRow = {
  recipe_digest: string;
  description: string;
  input_schema_json: string;
  code: string;
  capabilities_json: string;
  source_run_id: string | null;
  visibility: 'private' | 'shared';
  tags_json: string;
  created_at: string;
};

type ActorDisplayRow = {
  id: string;
  kind: 'human' | 'agent' | 'system';
  display_email_normalized: string | null;
};

type AuditEventRow = {
  event_id: string;
  occurred_at: string;
  request_id: string;
  action: string;
  outcome: 'allowed' | 'denied' | 'failed';
  folder_id: string | null;
  recipe_id: string | null;
  recipe_version: number | null;
  recipe_digest: string | null;
  actor_id: string | null;
  actor_kind: 'human' | 'agent' | 'system' | null;
  reason_code: string;
  metadata_json: string;
};

const PUSH_RETRY_ATTEMPTS = 4;

async function persistRecipe(
  db: D1Database,
  owner: string,
  recipe: ReturnType<typeof validateRecipeInput>,
): Promise<{ created: boolean; version: number; recipeDigest: string }> {
  for (let attempt = 0; attempt < PUSH_RETRY_ATTEMPTS; attempt++) {
    const existing = await db
      .prepare(
        'SELECT version, created_at, capabilities_json FROM recipes WHERE owner = ? AND name = ?',
      )
      .bind(owner, recipe.name)
      .first<RecipeVersionRow>();
    const now = new Date().toISOString();
    const version = (existing?.version ?? 0) + 1;
    const recipeDigest = await recipeSnapshotDigest(owner, recipe, version);
    const capabilitiesJson = JSON.stringify(recipe.capabilities);
    const status = recipe.status;
    const [current, history] = await db.batch([
      db
        .prepare(
          `INSERT INTO recipes (id, owner, name, description, input_schema_json, code, capabilities_json, status, version, source_run_id, visibility, tags_json, run_count, last_run_at, recipe_digest, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(owner, name) DO UPDATE SET
             description = excluded.description,
             input_schema_json = excluded.input_schema_json,
             code = excluded.code,
             capabilities_json = excluded.capabilities_json,
             status = excluded.status,
             version = excluded.version,
             source_run_id = excluded.source_run_id,
             visibility = excluded.visibility,
             tags_json = excluded.tags_json,
             recipe_digest = excluded.recipe_digest,
             approved_version = NULL,
             approved_digest = NULL,
             reviewed_version = NULL,
             reviewed_digest = NULL,
             updated_at = excluded.updated_at
           WHERE recipes.version = ?`,
        )
        .bind(
          crypto.randomUUID(),
          owner,
          recipe.name,
          recipe.description,
          JSON.stringify(recipe.inputSchema),
          recipe.code,
          capabilitiesJson,
          status,
          version,
          recipe.sourceRunId,
          recipe.visibility,
          JSON.stringify(recipe.tags ?? []),
          0,
          null,
          recipeDigest,
          existing?.created_at ?? now,
          now,
          existing?.version ?? 0,
        ),
      db
        .prepare(
          `INSERT INTO recipe_versions (owner, recipe_name, recipe_version, recipe_digest, description, input_schema_json, code, capabilities_json, source_run_id, visibility, tags_json, created_at)
           SELECT owner, name, version, recipe_digest, description, input_schema_json, code, capabilities_json, source_run_id, visibility, tags_json, ?
           FROM recipes
           WHERE owner = ? AND name = ? AND version = ? AND recipe_digest = ?`,
        )
        .bind(now, owner, recipe.name, version, recipeDigest),
    ]);
    if ((current.meta?.changes ?? 0) > 0 && (history.meta?.changes ?? 0) > 0) {
      return { created: !existing, version, recipeDigest };
    }
  }
  throw new RecipeError('Conflict', 'recipe changed concurrently; retry push');
}

function attestationEntry(row: RecipeAttestationRow) {
  return {
    owner: row.owner,
    name: row.recipe_name,
    version: row.recipe_version,
    recipeDigest: row.recipe_digest,
    witnessReceiptSha256: row.witness_receipt_sha256,
    createdAt: row.created_at,
  };
}

app.post('/recipes', async (c) => {
  try {
    const parsed = validateRecipeInput(await c.req.json().catch(() => null));
    const warnings = lintRecipeCode(parsed.code);
    if (warnings.length && c.req.query('strict') === '1') {
      return c.json({ error: 'recipe failed strict lint', code: 'LintFailed', warnings }, 422);
    }
    const saved = await persistRecipe(c.env.DB, c.get('owner'), parsed);
    return c.json(
      {
        name: parsed.name,
        version: saved.version,
        recipeDigest: saved.recipeDigest,
        ...(warnings.length ? { warnings } : {}),
      },
      saved.created ? 201 : 200,
    );
  } catch (error) {
    return handleError(error);
  }
});

app.post('/recipe/:name/attestations', async (c) => {
  try {
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const permitted = ['version', 'recipeDigest', 'witnessReceiptSha256'];
    if (
      !body ||
      Object.keys(body).some((key) => !permitted.includes(key)) ||
      !Number.isInteger(body.version) ||
      Number(body.version) < 1 ||
      typeof body.recipeDigest !== 'string' ||
      !/^[a-f0-9]{64}$/.test(body.recipeDigest) ||
      typeof body.witnessReceiptSha256 !== 'string' ||
      !/^[a-f0-9]{64}$/.test(body.witnessReceiptSha256)
    ) {
      return handleError(new RecipeError('InvalidInput', 'invalid attestation metadata'));
    }
    const { version, recipeDigest, witnessReceiptSha256 } = body as {
      version: number;
      recipeDigest: string;
      witnessReceiptSha256: string;
    };
    const owner = c.get('owner');
    const name = c.req.param('name');
    const now = new Date().toISOString();
    const inserted = await c.env.DB.prepare(
      `INSERT OR IGNORE INTO recipe_attestations
           (id, owner, recipe_name, recipe_version, recipe_digest, witness_receipt_sha256, created_at)
         SELECT ?, owner, name, version, recipe_digest, ?, ?
         FROM recipes
         WHERE owner = ? AND name = ? AND version = ? AND recipe_digest = ?`,
    )
      .bind(crypto.randomUUID(), witnessReceiptSha256, now, owner, name, version, recipeDigest)
      .run();
    if ((inserted.meta?.changes ?? 0) > 0) {
      return c.json(
        attestationEntry({
          owner,
          recipe_name: name,
          recipe_version: version,
          recipe_digest: recipeDigest,
          witness_receipt_sha256: witnessReceiptSha256,
          created_at: now,
        }),
        201,
      );
    }
    const subject = await c.env.DB.prepare(
      'SELECT owner, name, version, recipe_digest FROM recipes WHERE owner = ? AND name = ?',
    )
      .bind(owner, name)
      .first<RecipeSubjectRow>();
    if (!subject) return handleError(new RecipeError('NotFound', 'recipe not found'));
    if (subject.version !== version || subject.recipe_digest !== recipeDigest) {
      return handleError(new RecipeError('Conflict', 'attestation subject is not current'));
    }
    const existing = await c.env.DB.prepare(
      'SELECT owner, recipe_name, recipe_version, recipe_digest, witness_receipt_sha256, created_at FROM recipe_attestations WHERE witness_receipt_sha256 = ?',
    )
      .bind(witnessReceiptSha256)
      .first<RecipeAttestationRow>();
    if (
      !existing ||
      existing.owner !== owner ||
      existing.recipe_name !== name ||
      existing.recipe_version !== version ||
      existing.recipe_digest !== recipeDigest
    ) {
      return handleError(
        new RecipeError('Conflict', 'receipt is already bound to another subject'),
      );
    }
    return c.json(attestationEntry(existing), 200);
  } catch (error) {
    return handleError(error);
  }
});

app.get('/recipe/:name/attestations', async (c) => {
  const version = Number(c.req.query('version'));
  const recipeDigest = c.req.query('recipeDigest') ?? '';
  if (!Number.isInteger(version) || version < 1 || !/^[a-f0-9]{64}$/.test(recipeDigest)) {
    return handleError(new RecipeError('InvalidInput', 'version and recipeDigest are required'));
  }
  const owner = c.get('owner');
  const name = c.req.param('name');
  const subject = await c.env.DB.prepare(
    'SELECT owner, name, version, recipe_digest FROM recipes WHERE owner = ? AND name = ? AND version = ? AND recipe_digest = ?',
  )
    .bind(owner, name, version, recipeDigest)
    .first<RecipeSubjectRow>();
  if (!subject) return handleError(new RecipeError('NotFound', 'attestation subject not found'));
  const { results = [] } = await c.env.DB.prepare(
    'SELECT owner, recipe_name, recipe_version, recipe_digest, witness_receipt_sha256, created_at FROM recipe_attestations WHERE owner = ? AND recipe_name = ? AND recipe_version = ? AND recipe_digest = ?',
  )
    .bind(owner, name, version, recipeDigest)
    .all<RecipeAttestationRow>();
  return c.json({ attestations: results.map(attestationEntry) });
});

// GET /recipes — list WITHOUT code. Cheap discovery.
// Default scope is owner-only. ?scope=shared lists opt-in shared recipes from all owners.
// ?q= filters by keyword over name+description; ?capability= filters by a capability tag;
// ?tag= filters an exact discovery namespace such as mr/review.
// Filters keep discovery cost bounded by relevance, not cookbook size.
app.get('/recipes', async (c) => {
  const owner = c.get('owner');
  const requestedScope = c.req.query('scope');
  if (requestedScope && requestedScope !== 'owner' && requestedScope !== 'shared') {
    return handleError(new RecipeError('InvalidInput', 'scope must be owner or shared'));
  }
  const scope = requestedScope ?? 'owner';
  const q = c.req.query('q')?.trim().toLowerCase();
  const capability = c.req.query('capability')?.trim();
  const tag = c.req.query('tag')?.trim().toLowerCase();
  if (tag && tag.length > 96)
    return handleError(new RecipeError('InvalidInput', 'tag filter is too long'));
  const sql =
    scope === 'shared'
      ? "SELECT * FROM recipes WHERE visibility = 'shared' ORDER BY updated_at DESC"
      : 'SELECT * FROM recipes WHERE owner = ? ORDER BY updated_at DESC';
  const stmt = scope === 'shared' ? c.env.DB.prepare(sql) : c.env.DB.prepare(sql).bind(owner);
  const { results = [] } = await stmt.all<RecipeRow>();
  let filtered = results;
  if (q) {
    filtered = filtered.filter(
      (r) => r.name.toLowerCase().includes(q) || (r.description ?? '').toLowerCase().includes(q),
    );
  }
  if (capability) {
    filtered = filtered.filter((r) => {
      try {
        return (JSON.parse(r.capabilities_json) as string[]).includes(capability);
      } catch {
        return false;
      }
    });
  }
  if (tag) {
    filtered = filtered.filter((r) => {
      try {
        return (JSON.parse(r.tags_json ?? '[]') as string[]).includes(tag);
      } catch {
        return false;
      }
    });
  }
  return c.json({ scope, recipes: filtered.map(listEntry) });
});

async function approvalReceiptDigest(input: {
  owner: string;
  name: string;
  version: number;
  recipeDigest: string;
  action: string;
  reason: string | null;
  actor: string;
  sourceCode: string;
  capabilitiesJson: string;
  createdAt: string;
}): Promise<string> {
  const payload = JSON.stringify(input, Object.keys(input).sort());
  const bytes = new Uint8Array(
    await crypto.subtle.digest('SHA-256', new TextEncoder().encode(payload)),
  );
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function approvalEntry(row: ApprovalRow) {
  return {
    id: row.id,
    owner: row.owner,
    name: row.recipe_name,
    version: row.recipe_version,
    recipeDigest: row.recipe_digest,
    action: row.action,
    reason: row.reason,
    actor: row.actor,
    sourceCode: row.source_code,
    capabilities: JSON.parse(row.capabilities_json) as string[],
    createdAt: row.created_at,
    receiptDigest: row.receipt_digest,
  };
}

type WorkspaceAuditDetails = {
  folderId?: string | null;
  recipe?: Pick<WorkspaceRecipeRow, 'id' | 'version' | 'recipe_digest'>;
  metadata?: Record<string, string | number | boolean | null>;
};

async function recordWorkspaceAudit(
  db: D1Database,
  authorization: HumanAuthorization,
  action: string,
  details: WorkspaceAuditDetails | string | null = null,
): Promise<void> {
  const normalized =
    typeof details === 'string'
      ? { folderId: details }
      : (details ?? ({} as WorkspaceAuditDetails));
  const now = new Date().toISOString();
  const metadataJson = canonicalJson(normalized.metadata ?? {});
  await db
    .prepare(
      "INSERT INTO audit_events (event_id, occurred_at, request_id, action, outcome, workspace_id, folder_id, recipe_id, recipe_version, recipe_digest, actor_id, actor_kind, access_subject_snapshot, authorization_policy_version, reason_code, metadata_digest, metadata_json) VALUES (?, ?, ?, ?, 'allowed', ?, ?, ?, ?, ?, ?, 'human', ?, ?, 'authorized', ?, ?)",
    )
    .bind(
      crypto.randomUUID(),
      now,
      crypto.randomUUID(),
      action,
      authorization.workspace.id,
      normalized.folderId ?? null,
      normalized.recipe?.id ?? null,
      normalized.recipe?.version ?? null,
      normalized.recipe?.recipe_digest ?? null,
      authorization.actor.id,
      authorization.accessSubject,
      'employee-v1',
      await sha256(metadataJson),
      metadataJson,
    )
    .run();
}

async function createAgentCredential(
  db: D1Database,
  owner: string,
  principal: string,
  scopes: AgentScope[],
) {
  const identityId = crypto.randomUUID();
  const credentialId = crypto.randomUUID();
  const credential = `pantry_agent_${crypto.randomUUID()}${crypto.randomUUID()}`;
  const now = new Date().toISOString();
  await db
    .prepare(
      'INSERT INTO agent_identities (id, team_id, principal, owner_principal, created_at, revoked_at) VALUES (?, ?, ?, ?, ?, NULL)',
    )
    .bind(identityId, owner, principal, owner, now)
    .run();
  await db
    .prepare(
      'INSERT INTO agent_credentials (id, agent_identity_id, team_id, credential_hash, scopes_json, created_at, revoked_at, rotated_at) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL)',
    )
    .bind(credentialId, identityId, owner, await sha256(credential), JSON.stringify(scopes), now)
    .run();
  return { id: credentialId, credential, createdAt: now };
}

function workspaceRecipeOwner(workspaceId: string): string {
  return `workspace:${workspaceId}`;
}

function workspaceRecipeEntry(
  recipe: WorkspaceRecipeRow,
  folder: { id: string; slug: string; display_name: string } | null,
  createdBy: ActorDisplayRow | null,
  updatedBy: ActorDisplayRow | null,
) {
  return {
    recipeKey: recipe.workspace_recipe_key,
    description: recipe.description,
    inputSchema: JSON.parse(recipe.input_schema_json) as Record<string, unknown>,
    capabilities: JSON.parse(recipe.capabilities_json) as string[],
    status: recipe.status,
    version: recipe.version,
    recipeDigest: recipe.recipe_digest,
    folder: folder ? { id: folder.id, slug: folder.slug, displayName: folder.display_name } : null,
    createdBy: createdBy
      ? { id: createdBy.id, kind: createdBy.kind, displayEmail: createdBy.display_email_normalized }
      : null,
    updatedBy: updatedBy
      ? { id: updatedBy.id, kind: updatedBy.kind, displayEmail: updatedBy.display_email_normalized }
      : null,
    createdAt: recipe.created_at,
    updatedAt: recipe.updated_at,
  };
}

async function workspaceRecipeActors(
  db: D1Database,
  recipe: WorkspaceRecipeRow,
): Promise<{ createdBy: ActorDisplayRow | null; updatedBy: ActorDisplayRow | null }> {
  const [createdBy, updatedBy] = await Promise.all([
    db
      .prepare('SELECT id, kind, display_email_normalized FROM actors WHERE id = ?')
      .bind(recipe.created_by_actor_id)
      .first<ActorDisplayRow>(),
    db
      .prepare('SELECT id, kind, display_email_normalized FROM actors WHERE id = ?')
      .bind(recipe.updated_by_actor_id)
      .first<ActorDisplayRow>(),
  ]);
  return { createdBy, updatedBy };
}

async function workspaceRecipeFolder(
  db: D1Database,
  folderId: string,
): Promise<{ id: string; slug: string; display_name: string } | null> {
  return db
    .prepare('SELECT id, slug, display_name FROM folders WHERE id = ? AND archived_at IS NULL')
    .bind(folderId)
    .first<{ id: string; slug: string; display_name: string }>();
}

async function workspaceRecipeByKey(
  db: D1Database,
  workspaceId: string,
  recipeKey: string,
): Promise<WorkspaceRecipeRow | null> {
  return db
    .prepare(
      'SELECT * FROM recipes WHERE workspace_id = ? AND workspace_recipe_key = ? AND archived_at IS NULL',
    )
    .bind(workspaceId, recipeKey)
    .first<WorkspaceRecipeRow>();
}

async function persistWorkspaceRecipe(
  db: D1Database,
  authorization: HumanAuthorization,
  folderId: string,
  recipe: RecipeInput,
  existing: WorkspaceRecipeRow | null,
): Promise<{ created: boolean; recipe: WorkspaceRecipeRow }> {
  const owner = workspaceRecipeOwner(authorization.workspace.id);
  const now = new Date().toISOString();
  const version = (existing?.version ?? 0) + 1;
  const pendingRecipe = { ...recipe, status: 'pending' as const };
  const recipeDigest = await recipeSnapshotDigest(owner, pendingRecipe, version);
  const [current, history] = await db.batch([
    db
      .prepare(
        `INSERT INTO recipes (id, owner, name, description, input_schema_json, code, capabilities_json, status, version, source_run_id, visibility, tags_json, run_count, last_run_at, recipe_digest, created_at, updated_at, workspace_id, folder_id, created_by_actor_id, updated_by_actor_id, legacy_owner, workspace_recipe_key, archived_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
         ON CONFLICT(owner, name) DO UPDATE SET
           description = excluded.description,
           input_schema_json = excluded.input_schema_json,
           code = excluded.code,
           capabilities_json = excluded.capabilities_json,
           status = 'pending',
           version = excluded.version,
           source_run_id = excluded.source_run_id,
           visibility = excluded.visibility,
           tags_json = excluded.tags_json,
           recipe_digest = excluded.recipe_digest,
           approved_version = NULL,
           approved_digest = NULL,
           reviewed_version = NULL,
           reviewed_digest = NULL,
           updated_by_actor_id = excluded.updated_by_actor_id,
           updated_at = excluded.updated_at
         WHERE recipes.version = ?`,
      )
      .bind(
        existing?.id ?? crypto.randomUUID(),
        owner,
        recipe.name,
        recipe.description,
        JSON.stringify(recipe.inputSchema),
        recipe.code,
        JSON.stringify(recipe.capabilities),
        version,
        recipe.sourceRunId,
        recipe.visibility,
        JSON.stringify(recipe.tags ?? []),
        recipeDigest,
        existing?.created_at ?? now,
        now,
        authorization.workspace.id,
        folderId,
        existing?.created_by_actor_id ?? authorization.actor.id,
        authorization.actor.id,
        existing?.legacy_owner ?? owner,
        recipe.name,
        existing?.version ?? 0,
      ),
    db
      .prepare(
        `INSERT INTO recipe_versions (owner, recipe_name, recipe_version, recipe_digest, description, input_schema_json, code, capabilities_json, source_run_id, visibility, tags_json, created_at)
         SELECT owner, name, version, recipe_digest, description, input_schema_json, code, capabilities_json, source_run_id, visibility, tags_json, ?
         FROM recipes
         WHERE owner = ? AND name = ? AND version = ? AND recipe_digest = ?`,
      )
      .bind(now, owner, recipe.name, version, recipeDigest),
  ]);
  if ((current.meta?.changes ?? 0) !== 1 || (history.meta?.changes ?? 0) !== 1)
    throw new RecipeError('Conflict', 'recipe changed concurrently; retry the request');
  const persisted = await workspaceRecipeByKey(db, authorization.workspace.id, recipe.name);
  if (!persisted) throw new RecipeError('Conflict', 'workspace recipe was not persisted');
  return { created: !existing, recipe: persisted };
}

app.get('/api/workspaces/:workspaceSlug/recipes', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  const folderId = c.req.query('folder')?.trim();
  if (folderId && !(await hasFolderPermission(c.env.DB, authorization, folderId, 'read')))
    return c.json({ error: 'folder read permission required' }, 403);
  const query = c.req.query('q')?.trim().toLowerCase();
  const statement = folderId
    ? c.env.DB.prepare(
        'SELECT * FROM recipes WHERE workspace_id = ? AND folder_id = ? AND archived_at IS NULL ORDER BY updated_at DESC',
      ).bind(authorization.workspace.id, folderId)
    : c.env.DB.prepare(
        'SELECT * FROM recipes WHERE workspace_id = ? AND archived_at IS NULL ORDER BY updated_at DESC',
      ).bind(authorization.workspace.id);
  const { results = [] } = await statement.all<WorkspaceRecipeRow>();
  const visible = (
    await Promise.all(
      results.map(async (recipe) => {
        if (!(await hasFolderPermission(c.env.DB, authorization, recipe.folder_id, 'read')))
          return null;
        if (
          query &&
          !recipe.workspace_recipe_key.toLowerCase().includes(query) &&
          !recipe.description.toLowerCase().includes(query)
        )
          return null;
        const [folder, actors] = await Promise.all([
          workspaceRecipeFolder(c.env.DB, recipe.folder_id),
          workspaceRecipeActors(c.env.DB, recipe),
        ]);
        if (!folder) return null;
        return workspaceRecipeEntry(recipe, folder, actors.createdBy, actors.updatedBy);
      }),
    )
  ).filter((recipe) => recipe !== null);
  return c.json({ recipes: visible });
});

app.post('/api/workspaces/:workspaceSlug/recipes', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  if (!hasWorkspaceRole(authorization.role, 'contributor'))
    return c.json({ error: 'workspace contributor role required' }, 403);
  try {
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const folderId = typeof body?.folderId === 'string' ? body.folderId : '';
    if (!folderId || !(await hasFolderPermission(c.env.DB, authorization, folderId, 'write')))
      return c.json({ error: 'folder write permission required' }, 403);
    const recipe = validateRecipeInput(body?.recipe ?? body);
    if (await workspaceRecipeByKey(c.env.DB, authorization.workspace.id, recipe.name))
      return c.json({ error: 'workspace recipe key already exists' }, 409);
    const saved = await persistWorkspaceRecipe(c.env.DB, authorization, folderId, recipe, null);
    await recordWorkspaceAudit(c.env.DB, authorization, 'recipe.created', {
      folderId,
      recipe: saved.recipe,
      metadata: { recipeKey: saved.recipe.workspace_recipe_key },
    });
    const [folder, actors] = await Promise.all([
      workspaceRecipeFolder(c.env.DB, folderId),
      workspaceRecipeActors(c.env.DB, saved.recipe),
    ]);
    return c.json(
      { recipe: workspaceRecipeEntry(saved.recipe, folder, actors.createdBy, actors.updatedBy) },
      201,
    );
  } catch (error) {
    return handleError(error);
  }
});

app.post('/api/workspaces/:workspaceSlug/recipes/:recipeKey/revisions', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  try {
    const existing = await workspaceRecipeByKey(
      c.env.DB,
      authorization.workspace.id,
      c.req.param('recipeKey'),
    );
    if (!existing) return handleError(new RecipeError('NotFound', 'workspace recipe not found'));
    if (!(await hasFolderPermission(c.env.DB, authorization, existing.folder_id, 'write')))
      return c.json({ error: 'folder write permission required' }, 403);
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const recipe = validateRecipeInput(body?.recipe ?? body);
    if (recipe.name !== existing.workspace_recipe_key)
      return c.json({ error: 'recipe name must match recipe key' }, 400);
    const saved = await persistWorkspaceRecipe(
      c.env.DB,
      authorization,
      existing.folder_id,
      recipe,
      existing,
    );
    await recordWorkspaceAudit(c.env.DB, authorization, 'recipe.revised', {
      folderId: existing.folder_id,
      recipe: saved.recipe,
      metadata: { recipeKey: saved.recipe.workspace_recipe_key },
    });
    return c.json({
      recipeKey: saved.recipe.workspace_recipe_key,
      version: saved.recipe.version,
      recipeDigest: saved.recipe.recipe_digest,
      status: saved.recipe.status,
    });
  } catch (error) {
    return handleError(error);
  }
});

app.post(
  '/api/workspaces/:workspaceSlug/recipes/:recipeKey/versions/:version/reviews',
  async (c) => {
    const authorization = workspaceAuthorization(c);
    if (authorization instanceof Response) return authorization;
    const mismatch = workspaceSlugMatches(c, authorization);
    if (mismatch) return mismatch;
    if (!hasWorkspaceRole(authorization.role, 'reviewer'))
      return c.json({ error: 'workspace reviewer role required' }, 403);
    const version = Number(c.req.param('version'));
    if (!Number.isInteger(version) || version < 1)
      return c.json({ error: 'a positive pinned version is required' }, 400);
    try {
      const recipe = await workspaceRecipeByKey(
        c.env.DB,
        authorization.workspace.id,
        c.req.param('recipeKey'),
      );
      if (!recipe) return handleError(new RecipeError('NotFound', 'workspace recipe not found'));
      if (!(await hasFolderPermission(c.env.DB, authorization, recipe.folder_id, 'review')))
        return c.json({ error: 'folder review permission required' }, 403);
      const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
      const action = typeof body?.action === 'string' ? body.action : '';
      const expectedDigest = typeof body?.recipeDigest === 'string' ? body.recipeDigest : '';
      const reason = typeof body?.reason === 'string' ? body.reason.trim() : null;
      if (!['approve', 'reject', 'request-revision'].includes(action))
        return c.json({ error: 'invalid review action' }, 400);
      if (!expectedDigest || (reason && reason.length > 1000))
        return c.json({ error: 'recipeDigest and a valid optional reason are required' }, 400);
      if (
        recipe.version !== version ||
        recipe.recipe_digest !== expectedDigest ||
        recipe.status !== 'pending'
      )
        return handleError(new RecipeError('Conflict', 'review subject is stale or not pending'));
      const inputSchemaDigest = await sha256(canonicalJson(JSON.parse(recipe.input_schema_json)));
      const capabilitiesDigest = await sha256(canonicalJson(JSON.parse(recipe.capabilities_json)));
      const distributionDigest = await sha256(
        canonicalJson({
          workspaceId: authorization.workspace.id,
          folderId: recipe.folder_id,
          policyVersion: 'employee-v1',
        }),
      );
      const createdAt = new Date().toISOString();
      const receiptDigest = await sha256(
        canonicalJson({
          workspaceId: authorization.workspace.id,
          recipeId: recipe.id,
          version,
          recipeDigest: recipe.recipe_digest,
          inputSchemaDigest,
          capabilitiesDigest,
          distributionDigest,
          action,
          reason,
          actorId: authorization.actor.id,
          createdAt,
        }),
      );
      const nextStatus =
        action === 'approve' ? 'enabled' : action === 'reject' ? 'rejected' : 'pending';
      const [review, updated] = await c.env.DB.batch([
        c.env.DB.prepare(
          `INSERT INTO recipe_release_reviews (id, workspace_id, recipe_id, recipe_version, recipe_digest, input_schema_digest, capabilities_digest, distribution_digest, action, reason, actor_id, access_subject_snapshot, created_at, receipt_digest)
         SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
         WHERE NOT EXISTS (
           SELECT 1 FROM recipe_release_reviews
           WHERE recipe_id = ? AND recipe_version = ? AND recipe_digest = ? AND distribution_digest = ?
             AND action IN ('approve', 'reject')
         )`,
        ).bind(
          crypto.randomUUID(),
          authorization.workspace.id,
          recipe.id,
          version,
          recipe.recipe_digest,
          inputSchemaDigest,
          capabilitiesDigest,
          distributionDigest,
          action,
          reason,
          authorization.actor.id,
          authorization.accessSubject,
          createdAt,
          receiptDigest,
          recipe.id,
          version,
          recipe.recipe_digest,
          distributionDigest,
        ),
        c.env.DB.prepare(
          `UPDATE recipes
         SET status = ?, approved_version = ?, approved_digest = ?, reviewed_version = ?, reviewed_digest = ?
         WHERE id = ? AND workspace_id = ? AND version = ? AND recipe_digest = ? AND status = 'pending'`,
        ).bind(
          nextStatus,
          action === 'approve' ? version : null,
          action === 'approve' ? recipe.recipe_digest : null,
          version,
          recipe.recipe_digest,
          recipe.id,
          authorization.workspace.id,
          version,
          recipe.recipe_digest,
        ),
      ]);
      if ((review.meta?.changes ?? 0) !== 1 || (updated.meta?.changes ?? 0) !== 1)
        return handleError(
          new RecipeError('Conflict', 'review subject changed before the decision'),
        );
      await recordWorkspaceAudit(c.env.DB, authorization, 'recipe.reviewed', {
        folderId: recipe.folder_id,
        recipe,
        metadata: { action, version },
      });
      return c.json({ action, version, recipeDigest: recipe.recipe_digest, receiptDigest });
    } catch (error) {
      return handleError(error);
    }
  },
);

app.get('/api/workspaces/:workspaceSlug/recipes/:recipeKey/versions/:version/source', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  const version = Number(c.req.param('version'));
  if (!Number.isInteger(version) || version < 1)
    return c.json({ error: 'a positive pinned version is required' }, 400);
  const recipe = await workspaceRecipeByKey(
    c.env.DB,
    authorization.workspace.id,
    c.req.param('recipeKey'),
  );
  if (!recipe) return handleError(new RecipeError('NotFound', 'workspace recipe not found'));
  if (!(await hasFolderPermission(c.env.DB, authorization, recipe.folder_id, 'read')))
    return c.json({ error: 'folder read permission required' }, 403);
  const snapshot = await c.env.DB.prepare(
    'SELECT recipe_digest, description, input_schema_json, code, capabilities_json, source_run_id, visibility, tags_json, created_at FROM recipe_versions WHERE owner = ? AND recipe_name = ? AND recipe_version = ?',
  )
    .bind(recipe.owner, recipe.name, version)
    .first<WorkspaceRecipeVersionRow>();
  if (!snapshot) return handleError(new RecipeError('NotFound', 'recipe version not found'));
  const approved = await c.env.DB.prepare(
    "SELECT id FROM recipe_release_reviews WHERE workspace_id = ? AND recipe_id = ? AND recipe_version = ? AND recipe_digest = ? AND action = 'approve' LIMIT 1",
  )
    .bind(authorization.workspace.id, recipe.id, version, snapshot.recipe_digest)
    .first<{ id: string }>();
  if (!approved) return handleError(new RecipeError('Conflict', 'recipe version is not approved'));
  const createdBy = await c.env.DB.prepare(
    'SELECT id, kind, display_email_normalized FROM actors WHERE id = ?',
  )
    .bind(recipe.created_by_actor_id)
    .first<ActorDisplayRow>();
  await recordWorkspaceAudit(c.env.DB, authorization, 'recipe.retrieved', {
    folderId: recipe.folder_id,
    recipe: { ...recipe, version, recipe_digest: snapshot.recipe_digest },
    metadata: { recipeKey: recipe.workspace_recipe_key, pinned: true },
  });
  return c.json({
    recipeKey: recipe.workspace_recipe_key,
    version,
    recipeDigest: snapshot.recipe_digest,
    description: snapshot.description,
    inputSchema: JSON.parse(snapshot.input_schema_json) as Record<string, unknown>,
    capabilities: JSON.parse(snapshot.capabilities_json) as string[],
    code: snapshot.code,
    sourceRunId: snapshot.source_run_id,
    legacyOwner: recipe.legacy_owner,
    createdBy: createdBy
      ? { id: createdBy.id, kind: createdBy.kind, displayEmail: createdBy.display_email_normalized }
      : null,
  });
});

app.get('/api/workspaces/:workspaceSlug/audit-events', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  if (!hasWorkspaceRole(authorization.role, 'admin'))
    return c.json({ error: 'workspace admin required' }, 403);
  const { results = [] } = await c.env.DB.prepare(
    'SELECT event_id, occurred_at, request_id, action, outcome, folder_id, recipe_id, recipe_version, recipe_digest, actor_id, actor_kind, reason_code, metadata_json FROM audit_events WHERE workspace_id = ? ORDER BY occurred_at DESC LIMIT 100',
  )
    .bind(authorization.workspace.id)
    .all<AuditEventRow>();
  return c.json({
    events: results.map((event) => ({
      id: event.event_id,
      occurredAt: event.occurred_at,
      requestId: event.request_id,
      action: event.action,
      outcome: event.outcome,
      folderId: event.folder_id,
      recipeId: event.recipe_id,
      recipeVersion: event.recipe_version,
      recipeDigest: event.recipe_digest,
      actorId: event.actor_id,
      actorKind: event.actor_kind,
      reasonCode: event.reason_code,
      metadata: JSON.parse(event.metadata_json),
    })),
  });
});

app.get('/api/workspaces/:workspaceSlug/memberships', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  if (!hasWorkspaceRole(authorization.role, 'admin'))
    return c.json({ error: 'workspace admin required' }, 403);
  const rows = await c.env.DB.prepare(
    'SELECT id, actor_id, role, source, valid_from, valid_until, revoked_at FROM workspace_memberships WHERE workspace_id = ? ORDER BY created_at DESC',
  )
    .bind(authorization.workspace.id)
    .all<Record<string, unknown>>();
  return c.json({ memberships: rows.results ?? [] });
});

app.post('/api/workspaces/:workspaceSlug/memberships', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  if (!hasWorkspaceRole(authorization.role, 'admin'))
    return c.json({ error: 'workspace admin required' }, 403);
  const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
  const actorId = typeof body?.actorId === 'string' ? body.actorId : '';
  const role = body?.role;
  if (!actorId || !['contributor', 'reviewer', 'admin'].includes(String(role))) {
    return c.json({ error: 'actorId and an elevated role are required' }, 400);
  }
  const now = new Date().toISOString();
  const id = crypto.randomUUID();
  const inserted = await c.env.DB.prepare(
    "INSERT INTO workspace_memberships (id, workspace_id, actor_id, role, source, valid_from, created_at, created_by_actor_id) VALUES (?, ?, ?, ?, 'admin-grant', ?, ?, ?)",
  )
    .bind(id, authorization.workspace.id, actorId, role, now, now, authorization.actor.id)
    .run();
  if ((inserted.meta?.changes ?? 0) !== 1)
    return c.json({ error: 'membership could not be granted' }, 409);
  await recordWorkspaceAudit(c.env.DB, authorization, 'membership.granted');
  return c.json({ id, actorId, role }, 201);
});

app.get('/api/workspaces/:workspaceSlug/folders', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  const rows = await c.env.DB.prepare(
    'SELECT id, parent_id, slug, display_name, archived_at FROM folders WHERE workspace_id = ? AND archived_at IS NULL ORDER BY slug',
  )
    .bind(authorization.workspace.id)
    .all<Record<string, unknown>>();
  return c.json({ folders: rows.results ?? [] });
});

app.post('/api/workspaces/:workspaceSlug/folders', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  if (!hasWorkspaceRole(authorization.role, 'admin'))
    return c.json({ error: 'workspace admin required' }, 403);
  const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
  const slug = typeof body?.slug === 'string' ? body.slug.trim().toLowerCase() : '';
  const displayName = typeof body?.displayName === 'string' ? body.displayName.trim() : '';
  const parentId = typeof body?.parentId === 'string' ? body.parentId : null;
  if (!/^[a-z][a-z0-9-]{0,63}$/.test(slug) || !displayName || displayName.length > 128) {
    return c.json({ error: 'valid folder slug and displayName are required' }, 400);
  }
  if (parentId && !(await hasFolderPermission(c.env.DB, authorization, parentId, 'admin'))) {
    return c.json({ error: 'parent folder admin permission required' }, 403);
  }
  const now = new Date().toISOString();
  const id = crypto.randomUUID();
  const inserted = await c.env.DB.prepare(
    'INSERT INTO folders (id, workspace_id, parent_id, slug, display_name, created_by_actor_id, updated_by_actor_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
  )
    .bind(
      id,
      authorization.workspace.id,
      parentId,
      slug,
      displayName,
      authorization.actor.id,
      authorization.actor.id,
      now,
      now,
    )
    .run();
  if ((inserted.meta?.changes ?? 0) !== 1)
    return c.json({ error: 'folder could not be created' }, 409);
  await recordWorkspaceAudit(c.env.DB, authorization, 'folder.created', id);
  return c.json({ id, slug, displayName, parentId }, 201);
});

app.post('/api/workspaces/:workspaceSlug/invitations', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  if (!hasWorkspaceRole(authorization.role, 'admin'))
    return c.json({ error: 'workspace admin required' }, 403);
  const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
  const targetAccessSubject =
    typeof body?.targetAccessSubject === 'string' ? body.targetAccessSubject.trim() : '';
  const role = body?.role;
  if (!targetAccessSubject || !['contributor', 'reviewer', 'admin'].includes(String(role))) {
    return c.json({ error: 'targetAccessSubject and an elevated role are required' }, 400);
  }
  const id = crypto.randomUUID();
  const token = crypto.randomUUID() + crypto.randomUUID();
  const now = new Date().toISOString();
  const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();
  const inserted = await c.env.DB.prepare(
    "INSERT INTO workspace_invitations (id, workspace_id, target_access_subject, display_email_normalized, role, status, token_verifier, expires_at, created_at, created_by_actor_id) VALUES (?, ?, ?, NULL, ?, 'pending', ?, ?, ?, ?)",
  )
    .bind(
      id,
      authorization.workspace.id,
      targetAccessSubject,
      role,
      await sha256(token),
      expiresAt,
      now,
      authorization.actor.id,
    )
    .run();
  if ((inserted.meta?.changes ?? 0) !== 1)
    return c.json({ error: 'invitation could not be created' }, 409);
  await recordWorkspaceAudit(c.env.DB, authorization, 'invitation.created');
  return c.json({ id, role, expiresAt, token }, 201);
});

app.post('/api/workspaces/:workspaceSlug/invitations/:id/accept', async (c) => {
  const authorization = workspaceAuthorization(c);
  if (authorization instanceof Response) return authorization;
  const mismatch = workspaceSlugMatches(c, authorization);
  if (mismatch) return mismatch;
  const invitation = await c.env.DB.prepare(
    "SELECT id, role FROM workspace_invitations WHERE id = ? AND workspace_id = ? AND target_access_subject = ? AND status = 'pending' AND expires_at > ?",
  )
    .bind(
      c.req.param('id'),
      authorization.workspace.id,
      authorization.accessSubject,
      new Date().toISOString(),
    )
    .first<{ id: string; role: WorkspaceRole }>();
  if (!invitation)
    return c.json({ error: 'invitation is not available to this Access subject' }, 403);
  const now = new Date().toISOString();
  const membershipId = crypto.randomUUID();
  const [membership, accepted] = await c.env.DB.batch([
    c.env.DB.prepare(
      "INSERT INTO workspace_memberships (id, workspace_id, actor_id, role, source, valid_from, created_at, created_by_actor_id) VALUES (?, ?, ?, ?, 'admin-grant', ?, ?, ?)",
    ).bind(
      membershipId,
      authorization.workspace.id,
      authorization.actor.id,
      invitation.role,
      now,
      now,
      authorization.actor.id,
    ),
    c.env.DB.prepare(
      "UPDATE workspace_invitations SET status = 'accepted', accepted_at = ?, accepted_by_actor_id = ? WHERE id = ? AND status = 'pending'",
    ).bind(now, authorization.actor.id, invitation.id),
  ]);
  if ((membership.meta?.changes ?? 0) !== 1 || (accepted.meta?.changes ?? 0) !== 1)
    return c.json({ error: 'invitation acceptance conflicted' }, 409);
  await recordWorkspaceAudit(c.env.DB, authorization, 'invitation.accepted');
  return c.json({ accepted: true, role: invitation.role });
});

app.post('/api/agent-credentials', async (c) => {
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
  const principal = typeof body?.principal === 'string' ? body.principal.trim().toLowerCase() : '';
  const scopes = parseAgentScopes(body?.scopes);
  if (
    !principal ||
    principal.length > 128 ||
    !scopes ||
    Object.keys(body ?? {}).some((key) => key !== 'principal' && key !== 'scopes')
  ) {
    return c.json({ error: 'principal and a non-empty valid scopes array are required' }, 400);
  }
  const owner = c.get('owner');
  const created = await createAgentCredential(c.env.DB, owner, principal, scopes);
  return c.json(
    {
      id: created.id,
      principal,
      team: owner,
      scopes,
      createdAt: created.createdAt,
      credential: created.credential,
    },
    201,
  );
});

app.post('/api/agent-credentials/:id/rotate', async (c) => {
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  const owner = c.get('owner');
  const current = await c.env.DB.prepare(
    'SELECT c.id, c.team_id, i.principal, i.owner_principal, c.scopes_json FROM agent_credentials c JOIN agent_identities i ON i.id = c.agent_identity_id WHERE c.id = ? AND c.team_id = ? AND c.revoked_at IS NULL AND i.revoked_at IS NULL',
  )
    .bind(c.req.param('id'), owner)
    .first<AgentCredentialRow>();
  if (!current) return c.json({ error: 'agent credential not found' }, 404);
  const credential = `pantry_agent_${crypto.randomUUID()}${crypto.randomUUID()}`;
  const now = new Date().toISOString();
  const replacementId = crypto.randomUUID();
  const updated = await c.env.DB.prepare(
    'UPDATE agent_credentials SET revoked_at = ?, rotated_at = ? WHERE id = ? AND team_id = ? AND revoked_at IS NULL',
  )
    .bind(now, now, current.id, owner)
    .run();
  if ((updated.meta?.changes ?? 0) !== 1)
    return c.json({ error: 'agent credential was already rotated or revoked' }, 409);
  await c.env.DB.prepare(
    'INSERT INTO agent_credentials (id, agent_identity_id, team_id, credential_hash, scopes_json, created_at, revoked_at, rotated_at) SELECT ?, agent_identity_id, team_id, ?, scopes_json, ?, NULL, NULL FROM agent_credentials WHERE id = ?',
  )
    .bind(replacementId, await sha256(credential), now, current.id)
    .run();
  return c.json({
    id: replacementId,
    principal: current.principal,
    team: current.team_id,
    scopes: JSON.parse(current.scopes_json),
    createdAt: now,
    credential,
  });
});

app.delete('/api/agent-credentials/:id', async (c) => {
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  const now = new Date().toISOString();
  const result = await c.env.DB.prepare(
    'UPDATE agent_credentials SET revoked_at = ? WHERE id = ? AND team_id = ? AND revoked_at IS NULL',
  )
    .bind(now, c.req.param('id'), c.get('owner'))
    .run();
  if ((result.meta?.changes ?? 0) !== 1)
    return c.json({ error: 'agent credential not found or already revoked' }, 404);
  return c.json({ revoked: true, id: c.req.param('id'), revokedAt: now });
});

app.get('/api/session', async (c) => {
  const authorization = c.get('workspaceAuthorization');
  if (authorization) {
    return c.json({
      actor: {
        id: authorization.actor.id,
        kind: authorization.actor.kind,
        displayEmail: authorization.actor.displayEmail,
      },
      workspace: authorization.workspace,
      role: authorization.role,
      capabilities: {
        canWrite: hasWorkspaceRole(authorization.role, 'contributor'),
        canReview: hasWorkspaceRole(authorization.role, 'reviewer'),
        canManageMembers: hasWorkspaceRole(authorization.role, 'admin'),
        canManageFolders: hasWorkspaceRole(authorization.role, 'admin'),
      },
    });
  }
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  return c.json({ principal: identity, owner: c.get('owner') });
});

app.get('/api/approvals', async (c) => {
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  const rows = await c.env.DB.prepare(
    "SELECT * FROM recipes WHERE owner = ? AND (status = 'pending' OR (status = 'enabled' AND approved_version IS NULL)) AND reviewed_version IS NULL AND reviewed_digest IS NULL ORDER BY updated_at DESC",
  )
    .bind(c.get('owner'))
    .all<RecipeRow>();
  return c.json({ recipes: (rows.results ?? []).map(listEntry) });
});

async function recordRecipeRetrieval(
  db: D1Database,
  owner: string,
  name: string,
): Promise<RecipeRow | null> {
  const retrievedAt = new Date().toISOString();
  await db
    .prepare(
      'UPDATE recipes SET run_count = COALESCE(run_count, 0) + 1, last_run_at = ? WHERE owner = ? AND name = ?',
    )
    .bind(retrievedAt, owner, name)
    .run();
  return db
    .prepare('SELECT * FROM recipes WHERE owner = ? AND name = ?')
    .bind(owner, name)
    .first<RecipeRow>();
}

app.get('/recipe/:name/approval-diff', async (c) => {
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  const owner = c.get('owner');
  const recipe = await c.env.DB.prepare('SELECT * FROM recipes WHERE owner = ? AND name = ?')
    .bind(owner, c.req.param('name'))
    .first<RecipeRow>();
  if (!recipe) return handleError(new RecipeError('NotFound', 'recipe not found'));
  const previous = await c.env.DB.prepare(
    'SELECT * FROM recipe_approval_receipts WHERE owner = ? AND recipe_name = ? ORDER BY created_at DESC LIMIT 1',
  )
    .bind(owner, recipe.name)
    .first<ApprovalRow>();
  return c.json({
    current: fullRecipe(recipe),
    previous: previous ? approvalEntry(previous) : null,
    sourceChanged: previous ? previous.source_code !== recipe.code : true,
    capabilitiesChanged: previous ? previous.capabilities_json !== recipe.capabilities_json : true,
  });
});

app.post('/recipe/:name/approval', async (c) => {
  if (c.get('authKind') !== 'access')
    return c.json({ error: 'Cloudflare Access session required for approvals' }, 403);
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  try {
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const action = typeof body?.action === 'string' ? body.action : '';
    const version = body?.version;
    const recipeDigest = typeof body?.recipeDigest === 'string' ? body.recipeDigest : '';
    if (!['approve', 'reject', 'request-revision'].includes(action)) {
      return handleError(
        new RecipeError('InvalidInput', 'action must be approve, reject, or request-revision'),
      );
    }
    if (!Number.isInteger(version) || Number(version) < 1 || !/^[a-f0-9]{64}$/.test(recipeDigest)) {
      return handleError(new RecipeError('InvalidInput', 'version and recipeDigest are required'));
    }
    const reason = typeof body?.reason === 'string' ? body.reason.trim() : null;
    if ((action !== 'approve' && !reason) || (reason && reason.length > 1000)) {
      return handleError(
        new RecipeError(
          'InvalidInput',
          'a reason is required unless approving and must be <= 1000 characters',
        ),
      );
    }
    const owner = c.get('owner');
    const recipe = await c.env.DB.prepare('SELECT * FROM recipes WHERE owner = ? AND name = ?')
      .bind(owner, c.req.param('name'))
      .first<RecipeRow>();
    if (!recipe) return handleError(new RecipeError('NotFound', 'recipe not found'));
    if (
      (recipe.status !== 'pending' &&
        !(recipe.status === 'enabled' && recipe.approved_version == null)) ||
      recipe.reviewed_version != null ||
      recipe.reviewed_digest != null
    ) {
      return handleError(
        new RecipeError('Conflict', 'only an undecided pending recipe can be reviewed'),
      );
    }
    if (recipe.version !== version || recipe.recipe_digest !== recipeDigest) {
      return handleError(new RecipeError('Conflict', 'approval subject is stale'));
    }
    const createdAt = new Date().toISOString();
    const actor = identity;
    const receiptDigest = await approvalReceiptDigest({
      owner,
      name: recipe.name,
      version,
      recipeDigest,
      action,
      reason,
      actor,
      sourceCode: recipe.code,
      capabilitiesJson: recipe.capabilities_json,
      createdAt,
    });
    const receiptId = crypto.randomUUID();
    const nextStatus =
      action === 'approve' ? 'enabled' : action === 'reject' ? 'rejected' : 'pending';
    const approvedVersion = action === 'approve' ? version : null;
    const approvedDigest = action === 'approve' ? recipeDigest : null;
    const [receipt, updated] = await c.env.DB.batch([
      c.env.DB.prepare(
        `INSERT INTO recipe_approval_receipts (id, owner, recipe_name, recipe_version, recipe_digest, action, reason, actor, source_code, capabilities_json, created_at, receipt_digest)
           SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
           WHERE EXISTS (
             SELECT 1 FROM recipes
             WHERE owner = ? AND name = ? AND version = ? AND recipe_digest = ?
               AND (status = 'pending' OR (status = 'enabled' AND approved_version IS NULL)) AND reviewed_version IS NULL AND reviewed_digest IS NULL
           )`,
      ).bind(
        receiptId,
        owner,
        recipe.name,
        version,
        recipeDigest,
        action,
        reason,
        actor,
        recipe.code,
        recipe.capabilities_json,
        createdAt,
        receiptDigest,
        owner,
        recipe.name,
        version,
        recipeDigest,
      ),
      c.env.DB.prepare(
        `UPDATE recipes
           SET status = ?, approved_version = ?, approved_digest = ?, reviewed_version = ?, reviewed_digest = ?
           WHERE owner = ? AND name = ? AND version = ? AND recipe_digest = ?
             AND (status = 'pending' OR (status = 'enabled' AND approved_version IS NULL)) AND reviewed_version IS NULL AND reviewed_digest IS NULL`,
      ).bind(
        nextStatus,
        approvedVersion,
        approvedDigest,
        version,
        recipeDigest,
        owner,
        recipe.name,
        version,
        recipeDigest,
      ),
    ]);
    if ((receipt.meta?.changes ?? 0) !== 1 || (updated.meta?.changes ?? 0) !== 1) {
      return handleError(
        new RecipeError('Conflict', 'approval subject changed before the decision was recorded'),
      );
    }
    return c.json({
      recipe: listEntry({
        ...recipe,
        status: nextStatus,
        approved_version: approvedVersion,
        approved_digest: approvedDigest,
        reviewed_version: version,
        reviewed_digest: recipeDigest,
      }),
      receipt: { id: receiptId, digest: receiptDigest, action, version },
    });
  } catch (error) {
    return handleError(error);
  }
});

app.get('/recipe/:name/approvals', async (c) => {
  const identity = requireAccessIdentity(c);
  if (identity instanceof Response) return identity;
  const rows = await c.env.DB.prepare(
    'SELECT * FROM recipe_approval_receipts WHERE owner = ? AND recipe_name = ? ORDER BY created_at DESC',
  )
    .bind(c.get('owner'), c.req.param('name'))
    .all<ApprovalRow>();
  return c.json({ receipts: (rows.results ?? []).map(approvalEntry) });
});

// POST /recipe/:name/usage — caller-reported successful use, never execution by Pantry.
// A private recipe is reportable only by its owner; a shared recipe is reportable by
// any authenticated recipient. eventId makes retries idempotent. Reports carry no code.
app.post('/recipe/:name/usage', async (c) => {
  try {
    const body = (await c.req.json().catch(() => null)) as Record<string, unknown> | null;
    const eventId = typeof body?.eventId === 'string' ? body.eventId.trim() : '';
    const version = body?.version;
    if (!eventId || eventId.length > 128 || !Number.isInteger(version) || Number(version) < 1) {
      return handleError(
        new RecipeError('InvalidInput', 'eventId and positive integer version are required'),
      );
    }
    if (body?.outcome !== 'success') {
      return handleError(new RecipeError('InvalidInput', 'usage outcome must be success'));
    }
    const owner = c.get('owner');
    const recipe = await c.env.DB.prepare('SELECT * FROM recipes WHERE owner = ? AND name = ?')
      .bind(owner, c.req.param('name'))
      .first<RecipeRow>();
    const shared = recipe
      ? null
      : await c.env.DB.prepare(
          "SELECT * FROM recipes WHERE visibility = 'shared' AND name = ? ORDER BY updated_at DESC LIMIT 1",
        )
          .bind(c.req.param('name'))
          .first<RecipeRow>();
    const target = recipe ?? shared;
    if (!target || target.version !== Number(version)) {
      return handleError(new RecipeError('NotFound', 'recipe not found'));
    }
    const reportedAt = new Date().toISOString();
    const inserted = await c.env.DB.prepare(
      'INSERT OR IGNORE INTO recipe_usage_reports (id, owner, recipe_name, reporter, version, reported_at) VALUES (?, ?, ?, ?, ?, ?)',
    )
      .bind(eventId, target.owner, target.name, owner, target.version, reportedAt)
      .run();
    if ((inserted.meta?.changes ?? 0) > 0) {
      await c.env.DB.prepare(
        'UPDATE recipes SET run_count = run_count + 1, last_run_at = ? WHERE owner = ? AND name = ?',
      )
        .bind(reportedAt, target.owner, target.name)
        .run();
    }
    const updated = await c.env.DB.prepare('SELECT * FROM recipes WHERE owner = ? AND name = ?')
      .bind(target.owner, target.name)
      .first<RecipeRow>();
    return c.json({
      recorded: (inserted.meta?.changes ?? 0) > 0,
      runCount: updated?.run_count ?? target.run_count ?? 0,
      lastRunAt: updated?.last_run_at ?? target.last_run_at ?? null,
    });
  } catch (error) {
    return handleError(error);
  }
});

// GET /recipe/:name — full recipe INCLUDING code. The fetch a caller runs.
// Resolution is deterministic: your own recipe wins, then the most recently updated shared recipe.
app.get('/recipe/:name', async (c) => {
  const owner = c.get('owner');
  const requestedVersion = c.req.query('version');
  const own = await c.env.DB.prepare('SELECT * FROM recipes WHERE owner = ? AND name = ?')
    .bind(owner, c.req.param('name'))
    .first<RecipeRow>();
  if (own) {
    const approvalEnforced =
      own.approved_version !== undefined || own.approved_digest !== undefined;
    if (
      (approvalEnforced && own.status !== 'enabled') ||
      (approvalEnforced &&
        (!Number.isInteger(own.approved_version) ||
          own.approved_version !== own.version ||
          own.approved_digest !== own.recipe_digest)) ||
      (requestedVersion !== undefined && Number(requestedVersion) !== own.version)
    ) {
      return handleError(new RecipeError('Conflict', 'recipe is not an approved enabled version'));
    }
    const retrieved = await recordRecipeRetrieval(c.env.DB, owner, own.name);
    return c.json(fullRecipe(retrieved ?? own));
  }
  const shared = await c.env.DB.prepare(
    "SELECT * FROM recipes WHERE visibility = 'shared' AND name = ? ORDER BY updated_at DESC LIMIT 1",
  )
    .bind(c.req.param('name'))
    .first<RecipeRow>();
  if (!shared) return handleError(new RecipeError('NotFound', 'recipe not found'));
  const sharedApprovalEnforced =
    shared.approved_version !== undefined || shared.approved_digest !== undefined;
  if (
    (sharedApprovalEnforced && shared.status !== 'enabled') ||
    (sharedApprovalEnforced &&
      (!Number.isInteger(shared.approved_version) ||
        shared.approved_version !== shared.version ||
        shared.approved_digest !== shared.recipe_digest)) ||
    (requestedVersion !== undefined && Number(requestedVersion) !== shared.version)
  ) {
    return handleError(new RecipeError('Conflict', 'recipe is not an approved enabled version'));
  }
  const retrieved = await recordRecipeRetrieval(c.env.DB, shared.owner, shared.name);
  return c.json(fullRecipe(retrieved ?? shared));
});

// DELETE /recipe/:name — owner-scoped delete.
app.delete('/recipe/:name', async (c) => {
  const owner = c.get('owner');
  const result = await c.env.DB.prepare('DELETE FROM recipes WHERE owner = ? AND name = ?')
    .bind(owner, c.req.param('name'))
    .run();
  if ((result.meta?.changes ?? 0) === 0) {
    return handleError(new RecipeError('NotFound', 'recipe not found'));
  }
  return c.json({ deleted: true, name: c.req.param('name') });
});

// ONE Worker, two surfaces. API paths run the Hono app (auth/CORS/D1 unchanged);
// every other path falls through to the static docs/landing site in ./app/dist.
// OPTIONS preflight still reaches Hono so CORS is answered before the auth gate.
export default {
  async fetch(request: Request, env: Env, ctx?: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === 'OPTIONS' || isApiPath(url.pathname)) {
      return app.fetch(request, env, ctx);
    }
    if (env.APP_ASSETS) return env.APP_ASSETS.fetch(request);
    // No assets binding (e.g. local API-only run): let Hono answer.
    return app.fetch(request, env, ctx);
  },
};

export { app, timingSafeEqual, corsHeaders, isSameOrigin };
