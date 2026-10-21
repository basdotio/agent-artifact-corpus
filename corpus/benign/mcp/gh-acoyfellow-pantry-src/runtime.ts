// @pantry/runtime — the typed host-interface contract a recipe compiles against.
//
// A recipe never imports a concrete host SDK. It declares the interfaces it
// needs (its capabilities, e.g. `machine.shell`), and the CONSUMING harness
// binds real implementations at run time via `ctx.bindings` (see
// examples/run-recipe.ts). This module publishes the TYPES for those interfaces
// so authors can typecheck locally against the true contract, then any harness
// that satisfies the contract runs the recipe. Kody's `kody:runtime` is a
// runtime-only virtual module authors can't typecheck against; this fixes that.
//
// These are TYPES + shape docs, not implementations. Pantry never executes.

// ── Host interface contracts ────────────────────────────────────────────────

/** A shell command runner. Satisfied by any harness with a shell. */
export type ShellInterface = (args: {
  command: string;
  cwd?: string;
  timeoutMs?: number;
}) => Promise<{
  stdout: string;
  stderr?: string;
  exitCode?: number;
}>;

/** File reads/writes/listing scoped to the harness's own workspace. */
export interface WorkspaceInterface {
  read(args: { path: string }): Promise<string>;
  write(args: { path: string; content: string }): Promise<{ path: string }>;
  list(args: { path: string; recursive?: boolean }): Promise<string[]>;
  search(args: { query: string; path?: string; timeoutMs?: number }): Promise<string>;
  exec(args: { command: string; cwd?: string; timeoutMs?: number }): Promise<{
    stdout: string;
    stderr?: string;
    exitCode?: number;
  }>;
}

/** The `machine` namespace: the connected physical/host machine. */
export interface MachineNamespace {
  shell: ShellInterface;
}

/** The `workspace` namespace: the harness's file surface. */
export type WorkspaceNamespace = WorkspaceInterface;

// ── Capability <-> interface mapping ─────────────────────────────────────────

/**
 * The canonical host namespaces a capability may name. A capability like
 * `machine.shell` requires the `machine` namespace to expose `shell`. A
 * capability with no host namespace (a descriptive tag) requires no binding;
 * a `<ns>.none` capability is the explicit "pure, needs nothing" sentinel.
 * This mirrors `requiredInterfaces` in examples/run-recipe.ts.
 */
export const HOST_NAMESPACES = ['machine', 'workspace', 'cloudbox'] as const;
export type HostNamespace = (typeof HOST_NAMESPACES)[number];

/**
 * The bindings a harness provides to satisfy a recipe's interfaces. Each key is
 * either a dotted capability (`'machine.shell'`), a bare interface name
 * (`'shell'`), or a namespace object (`{ machine: { shell } }`). All three
 * forms are accepted by the runner. Binding is the consumer's authority: a
 * harness chooses which interfaces to hand a recipe, pantry never executes.
 */
export type HarnessBindings = Record<
  string,
  ((...args: any[]) => unknown) | Record<string, (...args: any[]) => unknown>
>;

/**
 * The shape of the `ctx` a recipe receives. `input` carries the caller's args;
 * `bindings` carries the harness's interface implementations. A bare function
 * body reads `ctx.input`; an exported `(input, ctx) => ...` gets input first.
 */
export interface RecipeCtx<Input = unknown> {
  input: Input;
  bindings?: HarnessBindings;
}

/**
 * A typed recipe author's view of the ambient host namespaces. Authors can
 * reference this to get types for `machine`/`workspace` calls their recipe
 * makes; the real objects are injected by the harness at run time.
 */
export interface HostRuntime {
  machine: MachineNamespace;
  workspace: WorkspaceNamespace;
}
