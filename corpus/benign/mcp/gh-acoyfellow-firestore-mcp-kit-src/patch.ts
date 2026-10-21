import { z } from 'zod'

export function createPatchSchema<
  const Keys extends readonly [string, ...string[]],
>(allowedKeys: Keys) {
  const shape = Object.fromEntries(
    allowedKeys.map((key) => [key, z.unknown().optional()])
  )

  return z.object(shape).strict()
}

export function pickPatchedFields<const Shape extends z.ZodRawShape>(
  patch: z.infer<z.ZodObject<Shape>>,
  allowedKeys: readonly (keyof z.infer<z.ZodObject<Shape>>)[]
) {
  return allowedKeys.reduce<Partial<z.infer<z.ZodObject<Shape>>>>(
    (result, key) => {
      if (key in patch) {
        result[key] = patch[key]
      }

      return result
    },
    {}
  )
}
