import { z } from 'zod';
import {
  fileTargetsSchema,
  nameSchema,
  pageLimitSchema,
  threadStateSchema,
  ticketStateSchema,
  titleSchema,
} from './contracts.js';

const token = z.string().min(1).max(200);
const ticketBody = z
  .string()
  .refine(value => Buffer.byteLength(value, 'utf8') <= 256 * 1024, 'Ticket body exceeds 256 KiB.');

const publicMutation = z.discriminatedUnion('kind', [
  z
    .object({
      kind: z.literal('appendMessage'),
      body: z.string().min(1).max(16_000),
      mentions: z
        .object({
          agents: z.array(nameSchema).max(64).default([]),
          here: z.boolean().default(false),
          global: z.boolean().default(false),
        })
        .strict()
        .refine(value => !value.global || (value.agents.length === 0 && !value.here), {
          message: '@global cannot be combined with direct mentions or @here.',
        })
        .default({ agents: [], here: false, global: false }),
    })
    .strict(),
  z
    .object({
      kind: z.literal('updateTicket'),
      title: titleSchema.optional(),
      description: z.string().max(2000).optional(),
      owner: nameSchema.optional(),
      state: ticketStateSchema.optional(),
      dependsOn: z.array(token).max(64).optional(),
    })
    .strict()
    .refine(
      value =>
        value.title !== undefined ||
        value.description !== undefined ||
        value.owner !== undefined ||
        value.state !== undefined ||
        value.dependsOn !== undefined,
      'Provide at least one ticket metadata field.',
    ),
  z.object({ kind: z.literal('replaceTicketBody'), body: ticketBody }).strict(),
  z
    .object({
      kind: z.literal('appendTicketBody'),
      body: z
        .string()
        .min(1)
        .max(256 * 1024),
    })
    .strict(),
  z
    .object({
      kind: z.literal('patchTicketBody'),
      patch: z
        .string()
        .min(1)
        .max(512 * 1024),
    })
    .strict(),
]);

const turnTarget = z.discriminatedUnion('type', [
  z.object({ type: z.literal('thread'), threadId: token }).strict(),
  z.object({ type: z.literal('files'), paths: fileTargetsSchema }).strict(),
  z.object({ type: z.literal('ticket'), ticketId: token }).strict(),
]);

export const mcpSchemas = {
  bindHostSession: z
    .object({ sessionId: token, workspace: z.string().min(1).max(4096).optional() })
    .strict(),
  deliverHostNotifications: z
    .object({
      sessionId: token,
      phase: z.enum(['prompt', 'active', 'idle', 'paused']),
      turnId: token.optional(),
      workspace: z.string().min(1).max(4096).optional(),
    })
    .strict(),
  getUpdates: z.object({ cursor: z.string().max(500).optional() }).strict(),
  setAgentName: z.object({ name: nameSchema }).strict(),
  // Flat objects, not root-level unions: a JSON Schema whose root is `oneOf` has no top-level
  // `properties`, and function-calling layers that require a flat parameter object cannot
  // represent it. Branch rules are enforced by refinements instead. Defaults that belong to one
  // branch stay out of the schema, since a flat schema cannot say "only when resourceType is
  // ticket"; mcp-dispatch applies them where the branch is known.
  notifications: z
    .object({
      action: z.enum(['read', 'acknowledge']),
      batchToken: token.optional(),
      item: z.number().int().min(0).max(19).optional(),
      items: z.array(z.number().int().min(0).max(19)).min(1).max(20).optional(),
      cursor: z.string().regex(/^\d+$/).max(20).optional(),
    })
    .strict()
    .refine(v => v.action === 'acknowledge' || v.items === undefined, 'items needs acknowledge.')
    .refine(
      v => v.action === 'read' || (v.item === undefined && v.cursor === undefined),
      'item and cursor need read.',
    )
    .refine(
      v => v.action !== 'acknowledge' || Boolean(v.batchToken),
      'Acknowledge needs batchToken.',
    )
    .refine(v => v.item === undefined || Boolean(v.batchToken), 'Expansion needs batchToken.'),
  waitForWork: z.object({}).strict(),
  findResources: z
    .object({
      resourceType: z.enum(['thread', 'ticket']),
      threadId: token.optional(),
      ticketId: token.optional(),
      query: z.string().trim().min(1).max(200).optional(),
      state: threadStateSchema.optional(),
      following: z.boolean().optional(),
      owner: nameSchema.optional(),
      states: z.array(ticketStateSchema).min(1).max(4).optional(),
      ready: z.boolean().optional(),
      limit: pageLimitSchema,
      cursor: z.string().max(500).optional(),
    })
    .strict()
    .refine(
      v =>
        v.resourceType === 'ticket' ||
        (v.ticketId === undefined && v.owner === undefined && v.ready === undefined),
      'ticketId, owner and ready need resourceType ticket.',
    )
    .refine(
      v => v.resourceType === 'thread' || (v.threadId === undefined && v.following === undefined),
      'threadId and following need resourceType thread.',
    )
    .refine(
      v => !(v.threadId && (v.query || v.following !== undefined || v.cursor)),
      'Exact thread lookup cannot be combined with search or pagination.',
    )
    .refine(
      v => !(v.ticketId && (v.query || v.owner || v.ready !== undefined || v.cursor)),
      'Exact ticket lookup cannot be combined with search or pagination.',
    ),
  createResource: z
    .object({
      resourceType: z.enum(['thread', 'ticket']),
      title: titleSchema,
      description: z.string().max(2000).default(''),
      owner: nameSchema.optional(),
      state: ticketStateSchema.optional(),
      body: ticketBody.optional(),
      dependsOn: z.array(token).max(64).optional(),
    })
    .strict()
    .refine(v => v.resourceType !== 'ticket' || Boolean(v.owner), 'A ticket needs an owner.')
    .refine(
      v => v.resourceType === 'ticket' || v.owner === undefined,
      'owner needs resourceType ticket.',
    ),
  acquireTurn: z
    .object({
      target: turnTarget.optional(),
      requestToken: token.optional(),
      timeoutMs: z.number().int().min(0).max(20_000).default(20_000),
    })
    .strict()
    .refine(
      v => Boolean(v.target) !== Boolean(v.requestToken),
      'Provide exactly one of target or requestToken.',
    ),
  cancelTurn: z.object({ requestToken: token }).strict(),
  readResource: z
    .object({
      resourceId: token.optional(),
      turnToken: token.optional(),
      view: z.enum(['page', 'delta', 'message', 'outline', 'find']).default('page'),
      revision: z.string().regex(/^\d+$/).optional(),
      fromRevision: z.string().regex(/^\d+$/).optional(),
      cursor: z.string().max(4096).optional(),
      messageId: token.optional(),
      query: z.string().min(1).max(1024).optional(),
      mode: z.enum(['literal', 'regex']).default('literal'),
      limit: pageLimitSchema,
    })
    .strict()
    .refine(
      v => Boolean(v.resourceId || v.turnToken || v.cursor),
      'Provide resourceId, turnToken, or cursor.',
    )
    .refine(v => v.view !== 'find' || Boolean(v.query), 'Find needs query.')
    .refine(v => v.view !== 'message' || Boolean(v.messageId), 'Message needs messageId.')
    .refine(
      v => v.view !== 'delta' || Boolean(v.fromRevision || v.cursor),
      'Delta needs fromRevision.',
    ),
  commitTurn: z.object({ turnToken: token, mutation: publicMutation }).strict(),
  releaseTurn: z.object({ turnToken: token }).strict(),
} satisfies Record<string, z.ZodType>;

export type McpToolName = keyof typeof mcpSchemas;

// MCP output schemas must have an object root. Bassfish responses deliberately
// remain forward-compatible because threads, tickets, and host hooks add fields
// as the compact API evolves; the individual presenters remain the source of
// truth for those fields while this contract rejects non-object results.
const structuredOutput = z.record(z.string(), z.unknown());
export const mcpOutputSchemas = Object.fromEntries(
  (Object.keys(mcpSchemas) as McpToolName[]).map(name => [name, structuredOutput]),
) as Record<McpToolName, typeof structuredOutput>;

export const mcpDescriptions: Record<McpToolName, string> = {
  bindHostSession:
    'Internal host integration: bind this adapter to the current coding-agent session.',
  deliverHostNotifications:
    'Internal host integration: inject unread Bassfish notifications at a safe host boundary.',
  getUpdates:
    'Bootstrap compact project metadata once; pass its cursor for changes at later checkpoints. Finish nextCursor pages before adopting cursor.',
  setAgentName: 'Choose or reclaim an inactive agent name before requesting a turn.',
  notifications:
    'Read the next new content batch, replay/expand a batchToken, or acknowledge processed entry versions with batchToken and optional items.',
  waitForWork:
    'Wait for unread direct mentions, @here, @global, ticket assignments, or newly-ready tickets. Requires MCP Tasks.',
  findResources:
    'Search compact thread or ticket metadata. Reuse getUpdates inventory for routine checkpoints.',
  createResource: 'Create a new chat thread or project ticket.',
  acquireTurn:
    'Acquire FIFO access to a thread, ticket, or an atomic set of files/directories. Resume with requestToken. Content turns have short leases; advisory file locks last until release or session loss. Reread files with native tools after acquiring.',
  cancelTurn: 'Cancel a queued request or unclaimed offer.',
  readResource:
    'Read revision-pinned content without a writer turn: page, delta fromRevision, message, outline, or find. Use turnToken to inspect a claimed revision. Follow nextCursor.',
  commitTurn: 'Commit one supported chat or ticket change and release the turn. Never retries.',
  releaseTurn:
    'Release a content turn or the complete file set. File writes use native filesystem tools.',
};
