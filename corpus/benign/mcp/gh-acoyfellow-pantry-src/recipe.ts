// The recipe model and its validation.
//
// Mirrored from my-ax/src/saved-recipes.ts so a recipe authored in my-ax and a
// recipe pushed to pantry are the same shape. pantry stores and hands these
// back; it never runs the `code`.

export const RECIPE_STATUSES = [
  'pending',
  'enabled',
  'disabled',
  'rejected',
  'superseded',
] as const;
export type RecipeStatus = (typeof RECIPE_STATUSES)[number];
export const RECIPE_VISIBILITIES = ['private', 'shared'] as const;
export type RecipeVisibility = (typeof RECIPE_VISIBILITIES)[number];

// The stored row, as it lives in D1.
export type RecipeRow = {
  id: string;
  owner: string;
  name: string;
  description: string;
  input_schema_json: string;
  code: string;
  capabilities_json: string;
  status: RecipeStatus;
  version: number;
  source_run_id: string | null;
  visibility?: RecipeVisibility;
  tags_json?: string;
  run_count?: number;
  last_run_at?: string | null;
  recipe_digest?: string | null;
  approved_version?: number | null;
  approved_digest?: string | null;
  reviewed_version?: number | null;
  reviewed_digest?: string | null;
  workspace_id?: string | null;
  folder_id?: string | null;
  created_by_actor_id?: string | null;
  updated_by_actor_id?: string | null;
  legacy_owner?: string | null;
  workspace_recipe_key?: string | null;
  archived_at?: string | null;
  created_at: string;
  updated_at: string;
};

// The validated input a caller pushes.
// `code` is executable JavaScript text that pantry only stores and returns.
// The demo runner accepts these authoring shapes: a bare function body that
// reads `ctx`, `export default (input, ctx) => ...` / `export default function`,
// or `module.exports = (input, ctx) => ...`. Exported callables receive
// `(ctx.input, ctx)`. This is a convenience contract, not a sandbox.
export type RecipeInput = {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
  code: string;
  capabilities: string[];
  sourceRunId: string | null;
  status: RecipeStatus;
  visibility?: RecipeVisibility;
  tags?: string[];
};

export class RecipeError extends Error {
  constructor(
    public code: 'InvalidInput' | 'NotFound' | 'Conflict',
    message: string,
  ) {
    super(message);
    this.name = 'RecipeError';
  }
}

// Capability tags. Either a scoped namespace (workspace.*/machine.*/cloudbox.*)
// or a generic free tag (e.g. `text.transform`). A recipe must declare at least
// one so the caller can decide whether the script is safe to run.
const SCOPED_CAPABILITY = /^(workspace|machine|cloudbox)\.[a-zA-Z0-9_.-]+$/;
const GENERIC_CAPABILITY = /^[a-z][a-z0-9]*(\.[a-z0-9_-]+)+$/;
const RECIPE_TAG = /^[a-z][a-z0-9_-]{0,31}\/[a-z0-9][a-z0-9_.-]{0,63}$/;
const MAX_RECIPE_TAGS = 20;

const MAX_CODE_BYTES = 32_000;

function assertObject(value: unknown, field: string): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new RecipeError('InvalidInput', `${field} must be an object`);
  }
  return value as Record<string, unknown>;
}

function cleanName(value: unknown): string {
  const name = typeof value === 'string' ? value.trim() : '';
  if (!/^[a-zA-Z][a-zA-Z0-9_]{0,63}$/.test(name)) {
    throw new RecipeError('InvalidInput', 'name must match /^[a-zA-Z][a-zA-Z0-9_]{0,63}$/');
  }
  return name;
}

function cleanCapabilities(value: unknown): string[] {
  const capabilities = Array.isArray(value) ? value : [];
  if (!capabilities.length) {
    throw new RecipeError('InvalidInput', 'capabilities must list at least one capability');
  }
  const cleaned = capabilities.map((capability) =>
    typeof capability === 'string' ? capability.trim() : '',
  );
  const invalid = cleaned.filter(
    (capability) => !SCOPED_CAPABILITY.test(capability) && !GENERIC_CAPABILITY.test(capability),
  );
  if (invalid.length) {
    throw new RecipeError('InvalidInput', `invalid capabilities: ${invalid.join(', ')}`);
  }
  return [...new Set(cleaned)].sort();
}

function cleanTags(value: unknown): string[] {
  if (value == null) return [];
  if (!Array.isArray(value) || value.length > MAX_RECIPE_TAGS) {
    throw new RecipeError('InvalidInput', `tags must contain at most ${MAX_RECIPE_TAGS} items`);
  }
  const tags = value.map((tag) => (typeof tag === 'string' ? tag.trim().toLowerCase() : ''));
  const invalid = tags.filter((tag) => !RECIPE_TAG.test(tag));
  if (invalid.length) throw new RecipeError('InvalidInput', `invalid tags: ${invalid.join(', ')}`);
  return [...new Set(tags)].sort();
}

function cleanDescription(value: unknown): string {
  const description = typeof value === 'string' ? value.trim() : '';
  if (description.length < 5 || description.length > 500) {
    throw new RecipeError('InvalidInput', 'description must be 5-500 characters');
  }
  return description;
}

function cleanInputSchema(value: unknown): Record<string, unknown> {
  const inputSchema = assertObject(value ?? { type: 'object', properties: {} }, 'inputSchema');
  if (inputSchema.type !== 'object') {
    throw new RecipeError('InvalidInput', 'inputSchema.type must be object');
  }
  return inputSchema;
}

function cleanCode(value: unknown): string {
  const code = typeof value === 'string' ? value.trim() : '';
  if (!code) throw new RecipeError('InvalidInput', 'code is required');
  if (new TextEncoder().encode(code).byteLength > MAX_CODE_BYTES) {
    throw new RecipeError('InvalidInput', `code must be <= ${MAX_CODE_BYTES} bytes`);
  }
  return code;
}

// Validate a full recipe push. Throws RecipeError('InvalidInput') on any failure.
// Best-effort push-time lint. NOT a proof of determinism or safety: it is a
// coarse token scan (like scanRecipeCode) that a recipe can defeat, and a
// clean lint does not guarantee a recipe is deterministic. It surfaces the
// failure modes the research measured (E5 non-determinism, E3 input-contract),
// as WARNINGS for the owner to weigh — it does not reject.
export function lintRecipeCode(code: string): string[] {
  const warnings: string[] = [];
  const nondet: Array<[RegExp, string]> = [
    [/\bMath\.random\b/, 'Math.random'],
    [/\bDate\.now\b/, 'Date.now'],
    [/\bnew Date\b/, 'new Date'],
    [/\bperformance\.now\b/, 'performance.now'],
    [/\bcrypto\.randomUUID\b/, 'crypto.randomUUID'],
    [/\bfetch\s*\(/, 'fetch'],
  ];
  const hits = nondet.filter(([re]) => re.test(code)).map(([, name]) => name);
  if (hits.length) {
    warnings.push(
      `determinism: code references ${hits.join(', ')} — output may differ across runs/agents, so it is not safe to share as a deterministic recipe. Best-effort scan, not a proof.`,
    );
  }
  // Input-contract check: a bare function body (no export default / module.exports)
  // is run as `(ctx) => body`, so it must read ctx.input. Bare `input` is undefined.
  const isExported = /\bexport\s+default\b/.test(code) || /\bmodule\.exports\b/.test(code);
  if (!isExported && /(^|[^.\w])input\b/.test(code) && !/\bctx\.input\b/.test(code)) {
    warnings.push(
      'contract: a bare function body receives `ctx` and must read ctx.input; this code references bare `input`, which is undefined at run time. Use ctx.input, or export default (input, ctx) => ...',
    );
  }
  return warnings;
}

export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  const object = value as Record<string, unknown>;
  return `{${Object.keys(object)
    .sort()
    .map((key) => `${JSON.stringify(key)}:${canonicalJson(object[key])}`)
    .join(',')}}`;
}

export async function sha256Hex(value: string): Promise<string> {
  const bytes = new Uint8Array(
    await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)),
  );
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

export async function recipeSnapshotDigest(
  owner: string,
  recipe: RecipeInput,
  version: number,
): Promise<string> {
  return sha256Hex(
    canonicalJson({
      schema: 'pantry/recipe-snapshot/v0',
      owner,
      name: recipe.name,
      version,
      description: recipe.description,
      inputSchema: recipe.inputSchema,
      code: recipe.code,
      capabilities: recipe.capabilities,
      status: recipe.status,
      visibility: recipe.visibility ?? 'private',
      tags: recipe.tags ?? [],
      sourceRunId: recipe.sourceRunId,
    }),
  );
}

export function validateRecipeInput(input: unknown): RecipeInput {
  const body = assertObject(input, 'recipe');
  const name = cleanName(body.name);
  const description = cleanDescription(body.description);
  const inputSchema = cleanInputSchema(body.inputSchema);
  const code = cleanCode(body.code);
  const capabilities = cleanCapabilities(body.capabilities);
  const tags = cleanTags(body.tags);
  const status: RecipeStatus =
    body.status === 'enabled'
      ? 'enabled'
      : body.status === 'disabled'
        ? 'disabled'
        : body.status === 'rejected'
          ? 'rejected'
          : body.status === 'superseded'
            ? 'superseded'
            : 'pending';
  const visibility: RecipeVisibility = body.visibility === 'shared' ? 'shared' : 'private';
  const sourceRunId =
    typeof body.sourceRunId === 'string' && body.sourceRunId.trim()
      ? body.sourceRunId.trim()
      : null;
  return {
    name,
    description,
    inputSchema,
    code,
    capabilities,
    status,
    sourceRunId,
    visibility,
    tags,
  };
}

// The cheap discovery shape: everything a caller needs to choose a recipe,
// WITHOUT the code. Listing never ships the script.
export function listEntry(row: RecipeRow) {
  return {
    name: row.name,
    description: row.description,
    inputSchema: JSON.parse(row.input_schema_json) as Record<string, unknown>,
    capabilities: JSON.parse(row.capabilities_json) as string[],
    status: row.status,
    version: row.version,
    sourceRunId: row.source_run_id,
    visibility: row.visibility ?? 'private',
    author: row.owner,
    tags: JSON.parse(row.tags_json || '[]') as string[],
    runCount: row.run_count ?? 0,
    lastRunAt: row.last_run_at ?? null,
    retrievalCount: row.run_count ?? 0,
    lastRetrievedAt: row.last_run_at ?? null,
    shareCandidate: (row.visibility ?? 'private') === 'private' && (row.run_count ?? 0) >= 5,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    recipeDigest: row.recipe_digest ?? null,
    ...(row.approved_version !== undefined
      ? {
          approvedVersion: row.approved_version ?? null,
          approvedDigest: row.approved_digest ?? null,
        }
      : {}),
  };
}

// The full shape: includes `code` and `capabilities`. This is what a caller
// fetches and then runs in its OWN sandbox.
export function fullRecipe(row: RecipeRow) {
  return {
    ...listEntry(row),
    code: row.code,
    createdAt: row.created_at,
  };
}

type RecipeMetadata = ReturnType<typeof listEntry>;
export type RecipeListEntry = Omit<
  RecipeMetadata,
  | 'visibility'
  | 'author'
  | 'tags'
  | 'runCount'
  | 'lastRunAt'
  | 'shareCandidate'
  | 'recipeDigest'
  | 'approvedVersion'
  | 'approvedDigest'
  | 'createdAt'
  | 'retrievalCount'
  | 'lastRetrievedAt'
> &
  Partial<
    Pick<
      RecipeMetadata,
      | 'visibility'
      | 'author'
      | 'tags'
      | 'runCount'
      | 'lastRunAt'
      | 'shareCandidate'
      | 'recipeDigest'
      | 'approvedVersion'
      | 'approvedDigest'
      | 'createdAt'
      | 'retrievalCount'
      | 'lastRetrievedAt'
    >
  >;
export type FullRecipe = Omit<
  ReturnType<typeof fullRecipe>,
  | 'visibility'
  | 'author'
  | 'tags'
  | 'runCount'
  | 'lastRunAt'
  | 'shareCandidate'
  | 'recipeDigest'
  | 'approvedVersion'
  | 'approvedDigest'
  | 'retrievalCount'
  | 'lastRetrievedAt'
> &
  Partial<
    Pick<
      ReturnType<typeof fullRecipe>,
      | 'visibility'
      | 'author'
      | 'tags'
      | 'runCount'
      | 'lastRunAt'
      | 'shareCandidate'
      | 'recipeDigest'
      | 'approvedVersion'
      | 'approvedDigest'
      | 'retrievalCount'
      | 'lastRetrievedAt'
    >
  >;
