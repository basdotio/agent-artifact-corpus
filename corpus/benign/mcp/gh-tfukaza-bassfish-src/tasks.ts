import { z } from 'zod';

/** Immutable Bassfish runtime subset of io.modelcontextprotocol/tasks@2026-07-28. */
export const tasksExtensionId = 'io.modelcontextprotocol/tasks' as const;
const taskId = z.string().min(1).max(200);
const baseTask = z
  .object({
    taskId,
    status: z.enum(['working', 'input_required', 'completed', 'failed', 'cancelled']),
    statusMessage: z.string().optional(),
    createdAt: z.string().datetime(),
    lastUpdatedAt: z.string().datetime(),
    ttlMs: z.number().int().nonnegative().nullable(),
    pollIntervalMs: z.number().int().nonnegative().optional(),
  })
  .passthrough();
export const getTaskParams = z.object({ taskId }).strict();
export const cancelTaskParams = z.object({ taskId }).strict();
export const updateTaskParams = z
  .object({ taskId, inputResponses: z.record(z.string(), z.unknown()) })
  .strict();
export const taskResult = baseTask.extend({ resultType: z.literal('complete') }).passthrough();
export const createTaskResult = baseTask.extend({ resultType: z.literal('task') }).passthrough();
export const taskAck = z.object({ resultType: z.literal('complete') }).passthrough();

export function hasTasksCapability(
  envelope: unknown,
  era: 'legacy' | 'modern' = 'modern',
): boolean {
  if (era !== 'modern') return false;
  const value = envelope as Record<string, unknown> | undefined;
  const capabilities = (value?.clientCapabilities ??
    value?.['io.modelcontextprotocol/clientCapabilities']) as
    { extensions?: Record<string, unknown> } | undefined;
  return Boolean(
    capabilities?.extensions && Object.hasOwn(capabilities.extensions, tasksExtensionId),
  );
}

/**
 * MCP: "a tool that returns structured content SHOULD also return the serialized JSON in a
 * TextContent block". Clients that render only `content` showed every Bassfish result as an
 * empty body without it, so the payload is mirrored rather than left structured-only.
 */
export function toolResult(value: unknown): Record<string, unknown> {
  return {
    content: [{ type: 'text' as const, text: JSON.stringify(value) }],
    structuredContent: value as Record<string, unknown>,
  };
}

export function wireTask(
  value: Record<string, unknown>,
  resultType: 'task' | 'complete',
): Record<string, unknown> {
  const output: Record<string, unknown> = { ...value, resultType };
  if (value.status === 'completed' && value.result) output.result = toolResult(value.result);
  return output;
}

export function wireTaskNotification(value: Record<string, unknown>): Record<string, unknown> {
  const output: Record<string, unknown> = { ...value };
  if (value.status === 'completed' && value.result) output.result = toolResult(value.result);
  return output;
}
