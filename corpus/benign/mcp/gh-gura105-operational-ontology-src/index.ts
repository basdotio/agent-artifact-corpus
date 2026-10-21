/**
 * Public entry point: define a model, create a Runtime, then expose it through
 * MCP if needed. Persistence and query evaluators remain implementation details;
 * callers work with instances, sets and operation results.
 */
export {
  defineObject,
  defineLink,
  defineAction,
  defineFunction,
  defineOntology,
  createRuntime,
  Runtime,
  declarations,
  reject,
  modify,
  create,
  link,
  unlink,
  // Model Functions can construct result sets and attach domain-specific metrics.
  objectSet,
  aggregationResult,
} from './core.js'
// Compile-time contracts only: these exports emit no JavaScript. Runtime
// validation comes from model schemas and the checks behind the public API.
export type {
  ObjectTypeDef,
  LinkTypeDef,
  ActionDef,
  ActionCtx,
  FunctionDef,
  FunctionResultOf,
  OntologyDef,
  Direction,
  ObjectOf,
  ObjectInstance,
  ObjectFilter,
  ObjectSet,
  AggregationResult,
  AggregationRow,
  TraverseOptions,
  Violation,
  Edit,
  ActionResult,
  AuditEntry,
  WritebackAdapter,
} from './core.js'
// Transport adapter: tool names and input schemas come from the same model.
export { buildMcpServer } from './mcp.js'
