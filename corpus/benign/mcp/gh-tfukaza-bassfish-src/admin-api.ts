import { z } from 'zod';
import {
  counterSchema,
  idSchema,
  nameSchema,
  threadDescriptionSchema,
  threadStateSchema,
  titleSchema,
} from './contracts.js';

const turn = z.object({ id: idSchema, fencingToken: counterSchema }).strict();
const withTurn = { turn };
const mutation = z.discriminatedUnion('kind', [
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
  z.object({ kind: z.literal('renameThread'), title: titleSchema }).strict(),
  z
    .object({ kind: z.literal('setThreadDescription'), description: threadDescriptionSchema })
    .strict(),
  z.object({ kind: z.literal('archiveThread') }).strict(),
  z.object({ kind: z.literal('activateThread') }).strict(),
  z.object({ kind: z.literal('deleteThread') }).strict(),
  z.object({ kind: z.literal('retractMessage'), messageId: idSchema }).strict(),
  z.object({ kind: z.literal('reinstateMessage'), messageId: idSchema }).strict(),
]);
const target = z.object({ type: z.enum(['thread', 'ticket']), id: idSchema }).strict();

export const adminSchemas = {
  getSession: z.object({}).strict(),
  setAgentName: z.object({ name: nameSchema }).strict(),
  listAgents: z
    .object({ onlineOnly: z.boolean().default(true), includeSelf: z.boolean().default(false) })
    .strict(),
  followThread: z.object({ threadId: idSchema }).strict(),
  unfollowThread: z.object({ threadId: idSchema }).strict(),
  listNotifications: z
    .object({
      limit: z.number().int().min(1).max(100).default(100),
      cursor: z.string().max(500).optional(),
    })
    .strict(),
  waitForWork: z.object({}).strict(),
  ackNotifications: z.object({ notificationIds: z.array(idSchema).min(1).max(100) }).strict(),
  createThread: z
    .object({ title: titleSchema, description: threadDescriptionSchema.default('') })
    .strict(),
  listThreads: z
    .object({
      state: threadStateSchema.default('active'),
      creatorIdentityId: idSchema.optional(),
      titlePrefix: z.string().max(200).optional(),
      following: z.boolean().optional(),
      limit: z.number().int().min(1).max(100).default(100),
      cursor: z.string().max(500).optional(),
    })
    .strict(),
  getThread: z.object({ threadId: idSchema }).strict(),
  searchThreads: z
    .object({
      query: z.string().trim().min(1).max(200),
      state: threadStateSchema.default('active'),
      limit: z.number().int().min(1).max(100).default(100),
    })
    .strict(),
  requestTurn: z.object({ target }).strict(),
  getTurnRequest: z.object({ requestId: idSchema }).strict(),
  waitForTurn: z
    .object({
      requestId: idSchema,
      timeoutMs: z.number().int().min(0).max(20_000).default(20_000),
    })
    .strict(),
  cancelTurnRequest: z.object({ requestId: idSchema }).strict(),
  claimTurn: z.object({ offerId: idSchema }).strict(),
  readTurn: z.object({ ...withTurn, cursor: z.string().max(500).optional() }).strict(),
  releaseTurn: z.object(withTurn).strict(),
  commitTurn: z.object({ ...withTurn, baseRevision: counterSchema, mutation }).strict(),
  listHistory: z
    .object({
      resourceId: idSchema,
      offset: z.number().int().min(0).default(0),
      limit: z.number().int().min(1).max(100).default(50),
    })
    .strict(),
  readRevision: z
    .object({
      resourceId: idSchema,
      revision: counterSchema,
      cursor: z.string().max(500).optional(),
    })
    .strict(),
  diffRevision: z.object({ resourceId: idSchema, revision: counterSchema }).strict(),
  inspectProject: z.object({}).strict(),
  exportProject: z.object({}).strict(),
  listProjectHistory: z
    .object({
      limit: z.number().int().min(1).max(100).default(50),
      cursor: z.string().max(4096).optional(),
    })
    .strict(),
} satisfies Record<string, z.ZodType>;
export type AdminToolName = keyof typeof adminSchemas;
