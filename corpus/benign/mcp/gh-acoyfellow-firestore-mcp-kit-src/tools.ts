import type { input, output, ZodType } from 'zod'

import { AuthorizationError, ValidationError } from './errors.js'

export type MaybePromise<T> = T | Promise<T>

export interface ToolDefinition<
  TContext,
  TInputSchema extends ZodType,
  TOutputSchema extends ZodType,
> {
  readonly name: string
  readonly description?: string
  readonly inputSchema: TInputSchema
  readonly outputSchema: TOutputSchema
  readonly authorize?: (args: {
    context: TContext
    input: output<TInputSchema>
  }) => MaybePromise<boolean>
  readonly execute: (args: {
    context: TContext
    input: output<TInputSchema>
  }) => MaybePromise<input<TOutputSchema>>
}

export function defineTool<
  TContext,
  TInputSchema extends ZodType,
  TOutputSchema extends ZodType,
>(definition: ToolDefinition<TContext, TInputSchema, TOutputSchema>) {
  return definition
}

export async function executeTool<
  TContext,
  TInputSchema extends ZodType,
  TOutputSchema extends ZodType,
>(
  tool: ToolDefinition<TContext, TInputSchema, TOutputSchema>,
  args: {
    context: TContext
    input: unknown
  }
) {
  const parsedInput = tool.inputSchema.safeParse(args.input)

  if (!parsedInput.success) {
    throw new ValidationError('Invalid tool input', parsedInput.error.flatten())
  }

  if (tool.authorize) {
    const allowed = await tool.authorize({
      context: args.context,
      input: parsedInput.data,
    })

    if (!allowed) {
      throw new AuthorizationError(`Not allowed to execute tool ${tool.name}`)
    }
  }

  const rawOutput = await tool.execute({
    context: args.context,
    input: parsedInput.data,
  })

  const parsedOutput = tool.outputSchema.safeParse(rawOutput)

  if (!parsedOutput.success) {
    throw new ValidationError(
      'Invalid tool output',
      parsedOutput.error.flatten()
    )
  }

  return parsedOutput.data
}
