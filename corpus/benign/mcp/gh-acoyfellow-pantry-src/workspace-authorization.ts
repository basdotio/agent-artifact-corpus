export type WorkspaceRole = 'reader' | 'contributor' | 'reviewer' | 'admin';
export type FolderPermission = 'read' | 'write' | 'review' | 'admin';

export type VerifiedAccessIdentity = {
  subject: string;
  displayEmail: string | null;
};

export type HumanAuthorization = {
  actor: { id: string; kind: 'human'; displayEmail: string | null };
  workspace: { id: string; slug: string; displayName: string };
  role: WorkspaceRole;
  accessSubject: string;
};

type WorkspaceRow = {
  id: string;
  slug: string;
  display_name: string;
  status: 'active' | 'disabled';
};

type ActorRow = {
  id: string;
  display_email_normalized: string | null;
  status: 'active' | 'revoked' | 'disabled';
};

type MembershipRow = {
  role: WorkspaceRole;
};

type FolderRow = {
  id: string;
  workspace_id: string;
  parent_id: string | null;
  archived_at: string | null;
};

type PermissionRow = {
  subject_actor_id: string;
  permission: FolderPermission;
};

export type WorkspaceAuthEnv = {
  PANTRY_EMPLOYEE_WORKSPACE_ENABLED?: string;
  PANTRY_EMPLOYEE_WORKSPACE_SLUG?: string;
  PANTRY_DEV_ACCESS_IDENTITY?: string;
  PANTRY_LOCAL_DEVELOPMENT?: string;
  PANTRY_ACCESS_SHARE_ALL?: string;
};

export function employeeWorkspaceEnabled(env: WorkspaceAuthEnv): boolean {
  return env.PANTRY_EMPLOYEE_WORKSPACE_ENABLED === 'true';
}

export function verifiedAccessIdentity(env: WorkspaceAuthEnv): VerifiedAccessIdentity | null {
  if (env.PANTRY_LOCAL_DEVELOPMENT !== 'true') return null;
  const configured = env.PANTRY_DEV_ACCESS_IDENTITY?.trim();
  if (!configured) return null;
  const [subject, rawEmail] = configured.split('|', 2);
  if (!subject || subject.length > 256) return null;
  const displayEmail = rawEmail?.trim().toLowerCase() || null;
  return { subject, displayEmail };
}

export function employeeConfigurationError(env: WorkspaceAuthEnv): string | null {
  if (!employeeWorkspaceEnabled(env)) return null;
  if (env.PANTRY_ACCESS_SHARE_ALL === 'true')
    return 'employee workspace mode cannot share all Access users';
  if (!env.PANTRY_EMPLOYEE_WORKSPACE_SLUG?.trim()) return 'employee workspace slug is required';
  if (env.PANTRY_DEV_ACCESS_IDENTITY && env.PANTRY_LOCAL_DEVELOPMENT !== 'true') {
    return 'development Access identity is not permitted outside local development';
  }
  return null;
}

export async function resolveHumanAuthorization(
  db: D1Database,
  env: WorkspaceAuthEnv,
): Promise<{ authorization: HumanAuthorization } | { error: string; status: number }> {
  const configurationError = employeeConfigurationError(env);
  if (configurationError) return { error: configurationError, status: 503 };
  const identity = verifiedAccessIdentity(env);
  if (!identity) return { error: 'verified Cloudflare Access session required', status: 401 };
  const workspaceSlug = env.PANTRY_EMPLOYEE_WORKSPACE_SLUG?.trim();
  if (!workspaceSlug) return { error: 'employee workspace slug is required', status: 503 };
  const workspace = await db
    .prepare('SELECT id, slug, display_name, status FROM workspaces WHERE slug = ?')
    .bind(workspaceSlug)
    .first<WorkspaceRow>();
  if (!workspace || workspace.status !== 'active')
    return { error: 'employee workspace is unavailable', status: 403 };
  let actor = await db
    .prepare(
      "SELECT id, display_email_normalized, status FROM actors WHERE kind = 'human' AND access_subject = ?",
    )
    .bind(identity.subject)
    .first<ActorRow>();
  const now = new Date().toISOString();
  if (!actor) {
    const id = crypto.randomUUID();
    const inserted = await db
      .prepare(
        "INSERT INTO actors (id, kind, access_subject, display_email_normalized, status, created_at, updated_at) VALUES (?, 'human', ?, ?, 'active', ?, ?)",
      )
      .bind(id, identity.subject, identity.displayEmail, now, now)
      .run();
    if ((inserted.meta?.changes ?? 0) !== 1) {
      actor = await db
        .prepare(
          "SELECT id, display_email_normalized, status FROM actors WHERE kind = 'human' AND access_subject = ?",
        )
        .bind(identity.subject)
        .first<ActorRow>();
    } else {
      actor = { id, display_email_normalized: identity.displayEmail, status: 'active' };
    }
  }
  if (!actor || actor.status !== 'active') return { error: 'actor is not active', status: 403 };
  const membership = await db
    .prepare(
      'SELECT role FROM workspace_memberships WHERE workspace_id = ? AND actor_id = ? AND revoked_at IS NULL AND valid_from <= ? AND (valid_until IS NULL OR valid_until > ?) ORDER BY valid_from DESC LIMIT 1',
    )
    .bind(workspace.id, actor.id, now, now)
    .first<MembershipRow>();
  return {
    authorization: {
      actor: { id: actor.id, kind: 'human', displayEmail: actor.display_email_normalized },
      workspace: { id: workspace.id, slug: workspace.slug, displayName: workspace.display_name },
      role: membership?.role ?? 'reader',
      accessSubject: identity.subject,
    },
  };
}

const roleRank: Record<WorkspaceRole, number> = {
  reader: 0,
  contributor: 1,
  reviewer: 2,
  admin: 3,
};

const permissionRank: Record<FolderPermission, number> = {
  read: 0,
  write: 1,
  review: 2,
  admin: 3,
};

export function hasWorkspaceRole(role: WorkspaceRole, required: WorkspaceRole): boolean {
  return roleRank[role] >= roleRank[required];
}

export async function hasFolderPermission(
  db: D1Database,
  authorization: HumanAuthorization,
  folderId: string,
  required: FolderPermission,
): Promise<boolean> {
  const lineage: FolderRow[] = [];
  let currentId: string | null = folderId;
  while (currentId) {
    const folder: FolderRow | null = await db
      .prepare('SELECT id, workspace_id, parent_id, archived_at FROM folders WHERE id = ?')
      .bind(currentId)
      .first<FolderRow>();
    if (!folder || folder.workspace_id !== authorization.workspace.id || folder.archived_at)
      return false;
    lineage.push(folder);
    currentId = folder.parent_id;
    if (lineage.length > 100) return false;
  }
  for (const folder of lineage) {
    const { results = [] } = await db
      .prepare(
        'SELECT subject_actor_id, permission FROM folder_permissions WHERE folder_id = ? AND revoked_at IS NULL',
      )
      .bind(folder.id)
      .all<PermissionRow>();
    if (
      results.length > 0 &&
      !results.some(
        (grant) =>
          grant.subject_actor_id === authorization.actor.id &&
          permissionRank[grant.permission] >= permissionRank[required],
      )
    ) {
      return false;
    }
  }
  return hasWorkspaceRole(
    authorization.role,
    required === 'read'
      ? 'reader'
      : required === 'write'
        ? 'contributor'
        : required === 'review'
          ? 'reviewer'
          : 'admin',
  );
}
