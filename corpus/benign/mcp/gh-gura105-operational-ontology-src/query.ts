/**
 * Evaluated sets and aggregations. These operations never read or write a store.
 * The functions below validate collection shapes and evaluate callbacks.
 * Runtime reads supply actor-visible snapshots; these helpers also accept
 * caller-constructed values.
 * Filtering an existing snapshot does not refresh it or recheck visibility.
 */
import { z } from 'zod'
import type { ObjectInstance, Properties } from './core.js'

/** A tagged collection of snapshots. objectSet checks tags and deduplicates IDs. */
export interface ObjectSet<O extends ObjectInstance = ObjectInstance> {
  readonly type: string
  readonly objects: readonly O[]
}
type Scalar = string | number | boolean
/** Local predicates are ordinary synchronous TypeScript; they are never sent to MCP. */
export type ObjectFilter<O extends ObjectInstance = ObjectInstance> = (object: O) => boolean

/**
 * `set` holds the target objects; each row's `pks` associates metrics with members
 * of that set. `key` labels the group and need not be an object's primary key.
 * For metrics derived from other objects (e.g. transfers for an account), a
 * Function returns that evidence separately; pks here still identify set members.
 */
export interface AggregationResult<O extends ObjectInstance = ObjectInstance> {
  readonly set: ObjectSet<O>
  readonly values: readonly AggregationRow[]
}
/** Keep numeric metrics separate from identity. A null key denotes an ungrouped total. */
export interface AggregationRow {
  readonly key: Scalar | null
  readonly pks: readonly string[]
  readonly metrics: Readonly<Record<string, number>>
}

const own = (value: object, key: string) => Object.hasOwn(value, key)
const scalar = (v: unknown): v is Scalar => typeof v === 'string' || typeof v === 'boolean' || (typeof v === 'number' && Number.isFinite(v))

/**
 * Build a fresh collection, preserving the first snapshot for each ID.
 * Tag/element agreement is a runtime check, including caller-constructed sets.
 */
export function objectSet<O extends ObjectInstance>(type: string, objects: readonly O[]): ObjectSet<O> {
  if (typeof type !== 'string' || !Array.isArray(objects)) throw new Error('invalid object set')
  const unique = new Map<string, O>()
  for (const object of objects) {
    if (!object || object.type !== type || typeof object.pk !== 'string' ||
        !object.properties || typeof object.properties !== 'object' || Array.isArray(object.properties)) {
      throw new Error(`object set ${type} contains an invalid or differently tagged object`)
    }
    // After checking the common tag, pk alone is enough to deduplicate identity.
    if (!unique.has(object.pk)) unique.set(object.pk, object)
  }
  return { type, objects: [...unique.values()] }
}

/** Same-type identity operations; preserve left-hand order and snapshots when IDs overlap. */
export function combine(op: 'union' | 'intersect' | 'subtract', a: ObjectSet, b: ObjectSet): ObjectSet {
  if (a.type !== b.type) throw new Error('set operations require the same object type')
  const left = objectSet(a.type, a.objects)
  const right = objectSet(b.type, b.objects)
  const ids = new Set(right.objects.map((o) => o.pk))
  return objectSet(a.type, op === 'union' ? [...left.objects, ...right.objects]
    : left.objects.filter((o) => op === 'intersect' ? ids.has(o.pk) : !ids.has(o.pk)))
}

/** Supported aggregation fields; MCP uses the same classification for its input schema. */
export function fieldKind(schema: z.core.$ZodType): 'string' | 'number' | 'boolean' | undefined {
  let inner = schema as z.ZodType
  while (inner instanceof z.ZodOptional || inner instanceof z.ZodNullable || inner instanceof z.ZodDefault) inner = inner.unwrap() as z.ZodType
  if (inner instanceof z.ZodString || inner instanceof z.ZodISODateTime || inner instanceof z.ZodISODate) return 'string'
  if (inner instanceof z.ZodNumber) return 'number'
  if (inner instanceof z.ZodBoolean) return 'boolean'
  const values = inner instanceof z.ZodEnum ? inner.options : inner instanceof z.ZodLiteral ? [...inner.values] : []
  if (!values.length) return undefined
  if (values.every((value) => typeof value === 'string')) return 'string'
  if (values.every((value) => typeof value === 'number')) return 'number'
  if (values.every((value) => typeof value === 'boolean')) return 'boolean'
  return undefined
}

/** Preserve the tag and snapshots; comparison semantics belong to the caller's code. */
export function filterObjects<O extends ObjectInstance>(set: ObjectSet<O>, predicate: ObjectFilter<O>): ObjectSet<O> {
  if (typeof predicate !== 'function') throw new Error('filter requires a synchronous predicate function')
  const input = objectSet(set.type, set.objects)
  return objectSet(set.type, input.objects.filter(predicate))
}

/**
 * Attach metrics to a set without putting derived values in business properties.
 * Validate finite metrics and group membership, then retain only referenced
 * objects. Groups may overlap; their combined target set still has unique IDs.
 * No column schema is needed. Producers keep their metric names consistent;
 * callers may construct results too, so membership is checked here.
 */
export function aggregationResult<O extends ObjectInstance>(
  set: ObjectSet<O>, values: readonly AggregationRow[],
): AggregationResult<O> {
  const input = objectSet(set.type, set.objects)
  const known = new Set(input.objects.map((o) => o.pk))
  const included = new Set<string>()
  const keys = new Set<Scalar | null>()
  const rows = values.map((row) => {
    // Only an ungrouped total can describe an empty selection (count/sum = 0).
    if ((row.key !== null && !scalar(row.key)) || keys.has(row.key) || !Array.isArray(row.pks) ||
        (row.pks.length === 0 && row.key !== null)) {
      throw new Error('invalid or duplicate aggregation group')
    }
    keys.add(row.key)
    const pks = [...new Set(row.pks)]
    for (const pk of pks) {
      if (!known.has(pk)) throw new Error(`aggregation refers to unknown object ${pk}`)
      included.add(pk)
    }
    if (!row.metrics || typeof row.metrics !== 'object' || Array.isArray(row.metrics)) throw new Error('invalid metrics')
    for (const [name, value] of Object.entries(row.metrics)) {
      if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`invalid metric ${name}`)
    }
    return { key: row.key, pks, metrics: { ...row.metrics } }
  })
  return { set: objectSet(set.type, input.objects.filter((o) => included.has(o.pk))), values: rows }
}

/**
 * Select metric rows and their associated objects together. Retained metrics
 * are unchanged; filtering .set by object properties and aggregating again is
 * a separate operation when a newly calculated total is wanted.
 */
export function filterAggregation<O extends ObjectInstance>(
  input: AggregationResult<O>, predicate: (row: AggregationRow) => boolean,
): AggregationResult<O> {
  if (typeof predicate !== 'function') throw new Error('filter requires a synchronous predicate function')
  const result = aggregationResult(input.set, input.values)
  return aggregationResult(result.set, result.values.filter(predicate))
}

/** Omit groupBy to total the whole set; otherwise group by a property. Both retain member IDs. */
export function aggregate<O extends ObjectInstance>(
  set: ObjectSet<O>, options: { groupBy?: string; sum?: string }, properties: Properties,
): AggregationResult<O> {
  if (options.groupBy !== undefined && (!own(properties, options.groupBy) || !fieldKind(properties[options.groupBy]))) throw new Error('invalid groupBy property')
  if (options.sum !== undefined && (!own(properties, options.sum) || fieldKind(properties[options.sum]) !== 'number')) {
    throw new Error('sum requires a numeric property')
  }
  const input = objectSet(set.type, set.objects)
  // Count unique objects, not paths that reached them. Sum also uses this object
  // grain: aggregate transfers before pivoting to deduplicated recipient accounts.
  const groups = new Map<Scalar | null, { key: Scalar | null; pks: string[]; metrics: Record<string, number> }>()
  // Seed the total so even an empty input returns one row with zero metrics.
  if (options.groupBy === undefined) groups.set(null, { key: null, pks: [], metrics: options.sum === undefined ? { count: 0 } : { count: 0, sum: 0 } })
  for (const object of input.objects) {
    let key: Scalar | null = null
    if (options.groupBy !== undefined) {
      const value = object.properties[options.groupBy]
      if (!scalar(value)) throw new Error('groupBy requires a non-null scalar value')
      key = value
    }
    const row = groups.get(key) ?? { key, pks: [], metrics: options.sum === undefined ? { count: 0 } : { count: 0, sum: 0 } }
    row.pks.push(object.pk)
    row.metrics.count++
    if (options.sum !== undefined) {
      const amount = object.properties[options.sum]
      if (typeof amount !== 'number' || !Number.isFinite(amount)) throw new Error('sum requires a non-null finite number')
      row.metrics.sum += amount
    }
    groups.set(key, row)
  }
  return aggregationResult(input, [...groups.values()])
}
