/**
 * TunnelRuntime abstraction.
 *
 * The manager talks to a backend through this interface only, so the v0.4.0
 * default (ProcessTunnelRuntime, a plugin-owned child process) can later be
 * swapped for a NativeManagedTunnelRuntime (official `runtimes connect`)
 * without touching the manager, routes or UI. Contract: start returns an
 * owned handle; stop only ever terminates the process that handle owns.
 */
import type {
  TunnelDetectionResult,
  TunnelDoctorResult,
  TunnelLaunchConfig,
  TunnelRuntimeHandle,
  TunnelRuntimeStatus,
} from './types.js';

export interface TunnelRuntime {
  /** Detect/version the tunnel-client executable. */
  detect(): Promise<TunnelDetectionResult>;

  /** Optional: update runtime-wide settings (e.g. configured executable) before detect/start. */
  configure?(options: { executable?: string }): void;

  /** Launch a runtime from a validated, fully-expanded config. */
  start(config: TunnelLaunchConfig): Promise<TunnelRuntimeHandle>;

  /**
   * Currently owned handle, if any. Used when start() throws after spawn so
   * the manager can retain ownership instead of orphaning the process.
   */
  ownedHandle(): TunnelRuntimeHandle | undefined;

  /** Stop exactly the runtime owned by `handle` (verified identity). */
  stop(handle: TunnelRuntimeHandle): Promise<void>;

  /** Read the live status of a runtime (or of the currently owned one). */
  status(handle?: TunnelRuntimeHandle): Promise<TunnelRuntimeStatus>;

  /** Structured layered diagnostics for a launch config. */
  doctor(config: TunnelLaunchConfig): Promise<TunnelDoctorResult>;

  /** Release backend resources (stop children, clear state). */
  dispose(): Promise<void>;
}

/** Error carrying a stable code for the manager/routes to surface. */
export class RuntimeError extends Error {
  readonly code: string;
  readonly component: 'bridge' | 'tunnel' | 'openai' | 'runtime';
  constructor(code: string, message: string, component: 'bridge' | 'tunnel' | 'openai' | 'runtime' = 'tunnel') {
    super(message);
    this.name = 'RuntimeError';
    this.code = code;
    this.component = component;
  }
}
