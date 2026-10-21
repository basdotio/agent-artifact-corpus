import { z } from 'zod';

export const idSchema = z.string().min(1).max(200);
export const counterSchema = z.string().regex(/^(0|[1-9][0-9]{0,19})$/);
export const nameSchema = z
  .string()
  .regex(/^[A-Za-z][A-Za-z0-9_-]{0,63}$/)
  .refine(
    value => value.toLowerCase() !== 'here',
    'The name "here" is reserved for group mentions.',
  );
export const titleSchema = z.string().trim().min(1).max(200);
export const threadDescriptionSchema = z.string().max(2000);
export const threadStateSchema = z.enum(['active', 'archived', 'deleted']);
export const ticketStateSchema = z.enum(['todo', 'in_progress', 'blocked', 'done']);
export const pageLimitSchema = z.number().int().min(1).max(50).default(20);
export const fileTargetsSchema = z
  .array(
    z
      .object({
        path: z
          .string()
          .min(1)
          .max(4096)
          .refine(value => !value.includes('\0'), 'Paths cannot contain NUL.'),
        kind: z.enum(['file', 'directory']),
      })
      .strict(),
  )
  .min(1)
  .max(256);
