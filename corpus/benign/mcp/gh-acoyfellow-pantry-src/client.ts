import type { FullRecipe, RecipeInput, RecipeListEntry } from './recipe.ts';

export type PantryAuthentication =
  | { kind: 'automation-token'; token: string }
  | { kind: 'session'; headers: () => Record<string, string> };

export type PantryAuthenticationKind = PantryAuthentication['kind'];

export function automationTokenAuthentication(token: string): PantryAuthentication {
  return { kind: 'automation-token', token };
}

export type PantryConfig = {
  url?: string;
  token?: string;
  authentication?: PantryAuthentication;
  fetch?: typeof fetch;
};

export type PushRecipeResult = {
  name: string;
  version: number;
  recipeDigest: string;
};

export type ApprovalAction = 'approve' | 'reject' | 'request-revision';

export type ApprovalResult = {
  recipe: RecipeListEntry;
  receipt: { id: string; digest: string; action: ApprovalAction; version: number };
};

export class PantryClient {
  private url: string | undefined;
  private authentication: PantryAuthentication | undefined;
  private fetchImpl: typeof fetch;

  constructor(config: PantryConfig = {}) {
    const env = (globalThis as { process?: { env?: Record<string, string | undefined> } }).process
      ?.env;
    const token = config.token ?? env?.PANTRY_TOKEN;
    this.url = (config.url ?? env?.PANTRY_URL)?.replace(/\/$/, '');
    this.authentication =
      config.authentication ?? (token ? automationTokenAuthentication(token) : undefined);
    this.fetchImpl = config.fetch ?? fetch;
  }

  get configured(): boolean {
    return Boolean(this.url && this.authentication);
  }

  get authenticationKind(): PantryAuthenticationKind | undefined {
    return this.authentication?.kind;
  }

  private headers(): Record<string, string> {
    if (!this.authentication) throw new Error('pantry client: authentication is not configured');
    const authenticationHeaders =
      this.authentication.kind === 'automation-token'
        ? { authorization: `Bearer ${this.authentication.token}` }
        : this.authentication.headers();
    return { ...authenticationHeaders, 'content-type': 'application/json' };
  }

  private require(): void {
    if (!this.url) throw new Error('pantry client: PANTRY_URL is not set');
    if (!this.authentication) throw new Error('pantry client: authentication is not configured');
  }

  // Fail-soft: an unconfigured client lists nothing rather than erroring, so a
  // recipe lookup degrades to "re-reason it" instead of crashing the caller.
  async list(
    options: { scope?: 'owner' | 'shared'; q?: string; capability?: string; tag?: string } = {},
  ): Promise<RecipeListEntry[]> {
    if (!this.configured) return [];
    const params = new URLSearchParams();
    if (options.scope === 'shared') params.set('scope', 'shared');
    if (options.q) params.set('q', options.q);
    if (options.capability) params.set('capability', options.capability);
    if (options.tag) params.set('tag', options.tag);
    const suffix = params.toString() ? `?${params}` : '';
    const res = await this.fetchImpl(`${this.url}/recipes${suffix}`, { headers: this.headers() });
    if (!res.ok) throw new Error(`pantry list failed: ${res.status}`);
    const body = (await res.json()) as { recipes: RecipeListEntry[] };
    return body.recipes ?? [];
  }

  async listShared(
    options: { q?: string; capability?: string; tag?: string } = {},
  ): Promise<RecipeListEntry[]> {
    return this.list({ ...options, scope: 'shared' });
  }

  // Report a successful caller-side use. Pantry never executes the recipe.
  async reportUsage(
    name: string,
    version: number,
    eventId: string,
  ): Promise<{
    recorded: boolean;
    runCount: number;
    lastRunAt: string | null;
  }> {
    this.require();
    const res = await this.fetchImpl(`${this.url}/recipe/${encodeURIComponent(name)}/usage`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({ eventId, version, outcome: 'success' }),
    });
    if (!res.ok) throw new Error(`pantry usage report failed: ${res.status}`);
    return (await res.json()) as { recorded: boolean; runCount: number; lastRunAt: string | null };
  }

  async approve(name: string, action: ApprovalAction, reason?: string): Promise<ApprovalResult> {
    this.require();
    const res = await this.fetchImpl(`${this.url}/recipe/${encodeURIComponent(name)}/approval`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify({ action, ...(reason ? { reason } : {}) }),
    });
    if (!res.ok) throw new Error(`pantry approval failed: ${res.status}`);
    return (await res.json()) as ApprovalResult;
  }

  // Returns the full approved recipe including code + capabilities + inputSchema.
  // The caller decides whether to run `code`.
  async get(name: string, version?: number): Promise<FullRecipe | null> {
    this.require();
    const suffix = version === undefined ? '' : `?version=${encodeURIComponent(version)}`;
    const res = await this.fetchImpl(`${this.url}/recipe/${encodeURIComponent(name)}${suffix}`, {
      headers: this.headers(),
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`pantry get failed: ${res.status}`);
    return (await res.json()) as FullRecipe;
  }

  async push(recipe: RecipeInput): Promise<PushRecipeResult> {
    this.require();
    const res = await this.fetchImpl(`${this.url}/recipes`, {
      method: 'POST',
      headers: this.headers(),
      body: JSON.stringify(recipe),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      throw new Error(`pantry push failed: ${res.status} ${detail}`);
    }
    return (await res.json()) as PushRecipeResult;
  }

  async delete(name: string): Promise<boolean> {
    this.require();
    const res = await this.fetchImpl(`${this.url}/recipe/${encodeURIComponent(name)}`, {
      method: 'DELETE',
      headers: this.headers(),
    });
    if (res.status === 404) return false;
    if (!res.ok) throw new Error(`pantry delete failed: ${res.status}`);
    return true;
  }
}

// Convenience: a default client wired to the ambient environment.
export const pantry = new PantryClient();
