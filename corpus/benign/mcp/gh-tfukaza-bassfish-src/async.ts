export async function mapAsync<T, R>(
  values: readonly T[],
  fn: (value: T, index: number, values: readonly T[]) => R | Promise<R>,
): Promise<R[]> {
  const result: R[] = [];
  for (let index = 0; index < values.length; index++)
    result.push(await fn(values[index]!, index, values));
  return result;
}
export async function filterAsync<T>(
  values: readonly T[],
  fn: (value: T, index: number) => unknown | Promise<unknown>,
): Promise<T[]> {
  const result: T[] = [];
  for (let index = 0; index < values.length; index++)
    if (await fn(values[index]!, index)) result.push(values[index]!);
  return result;
}
