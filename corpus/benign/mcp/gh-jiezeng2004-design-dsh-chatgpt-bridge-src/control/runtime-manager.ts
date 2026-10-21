/**
 * RuntimeManager: the single status authority and serialized mutation owner
 * for the tunnel runtime.
 *
 * The UI and management API only ever read the RuntimeSnapshot this class
 * produces; start/stop/restart run through a promise-chain mutex so they can
 * never interleave. The manager is also the only component that spawns or
 * stops tunnel processes, and it stops exactly the runtime it owns (verified
 * ProcessIdentity). It never holds or logs the runtime API key.
 */
import { rmSync } from 'node:fs';
import { join } from 'node:path';

import { ConfigStore, mergeRuntimeConfig } from './config-store.js';
import { SecretStore } from './secret-store.js';
import { ProfileGenerator } from './profile-generator.js';
import { probeBridge, probeControlPlane, probeTunnelHealth, buildDiagnosticSteps, type ControlPlaneProbeResult } from './diagnostics.js';
import { RuntimeError, type TunnelRuntime } from './tunnel-runtime.js';
import { ProcessTunnelRuntime, type ControlLogger } from './process-tunnel-runtime.js';
import { discoverExistingRuntime, type ExistingRuntimeDiscovery } from './discover.js';
import { redactText } from '../redact.js';
import type { DoctorStep, RuntimeConfig, RuntimeSnapshot, TunnelLaunchConfig, TunnelRuntimeHandle, TunnelRuntimeStatus } from './types.js';

export interface RuntimeManagerOptions {
  dshHome: string;
  bridge: {
    url: string;
    token: string;
    authMode: 'token' | 'none';
  };
  logger?: ControlLogger;
  /** Injectable runtime backend (tests inject FakeTunnelRuntime). */
  createRuntime?: () => TunnelRuntime;
  pollIntervalMs?: number;
  /** How long start() waits for tunnel ready before failing. */
  readyTimeoutMs?: number;
  now?: () => number;
  /** Injectable existing-install discovery (tests isolate APPDATA / PATH). */
  discover?: () => ExistingRuntimeDiscovery;
}

const DEFAULT_CONTROL_PLANE = 'https://api.openai.com';
const DETECTION_TTL_MS = 30_000;
const CONTROL_PLANE_PROBE_TTL_MS = 30_000;

/**
 * Probe the same authenticated tunnel resource that tunnel-client uses for
 * metadata, rather than the control-plane origin root. The origin root is not
 * an API-key validation endpoint and may return 401 even when the Runtime API
 * key is accepted by `/v1/tunnel/<id>`.
 */
function controlPlaneProbeUrl(baseUrl: string, tunnelId?: string): string {
  if (tunnelId === undefined || tunnelId === '') return baseUrl;
  try {
    const url = new URL(baseUrl);
    const prefix = url.pathname.replace(/\/+$/, '');
    url.pathname = `${prefix}/v1/tunnel/${encodeURIComponent(tunnelId)}`;
    url.search = '';
    url.hash = '';
    return url.toString();
  } catch {
    // Preserve the existing malformed-URL classification in probeControlPlane.
    return baseUrl;
  }
}

function silentLogger(): ControlLogger {
  return { info: () => {}, warn: () => {}, error: () => {} };
}

export interface OverallDerivationInput {
  bridge: RuntimeSnapshot['bridge'];
  tunnel: RuntimeSnapshot['tunnel'];
  openai: RuntimeSnapshot['openai']['status'];
}

/**
 * Composite overall state machine. Rules (documented + matrix-tested):
 *  - tunnel error             -> overall error
 *  - tunnel not installed     -> overall degraded
 *  - tunnel starting/stoping  -> overall degraded
 *  - tunnel ready + bridge running:
 *      openai connected     -> overall ready   (the ONLY ready path)
 *      openai unauthorized  -> overall degraded
 *      openai unreachable   -> overall degraded
 *      openai unknown       -> overall degraded
 *      openai error         -> overall error
 *  - tunnel process running  -> overall degraded
 *  - otherwise               -> overall stopped
 */
export function deriveOverallStatus(input: OverallDerivationInput): {
  status: RuntimeSnapshot['overall']['status'];
  lastError?: RuntimeSnapshot['lastError'];
} {
  const { bridge, tunnel, openai } = input;
  if (tunnel.status === 'error') {
    return { status: 'error', lastError: { component: 'tunnel', code: 'tunnel-error', message: 'tunnel runtime error' } };
  }
  if (tunnel.status === 'not-installed') {
    return { status: 'degraded', lastError: { component: 'tunnel', code: 'tunnel-client-not-installed', message: 'tunnel-client is not installed' } };
  }
  if (tunnel.status === 'starting' || tunnel.status === 'stopping') {
    return { status: 'degraded' };
  }
  // Only a live, healthy, connected runtime may ever report overall=ready.
  // OpenAI state decides overall even when the tunnel itself is up: any
  // non-connected OpenAI state must NOT default-fallthrough to ready.
  if (tunnel.ready && bridge.status === 'running') {
    switch (openai) {
      case 'connected':
        return { status: 'ready' };
      case 'unauthorized':
        return { status: 'degraded', lastError: { component: 'openai', code: 'runtime-api-unauthorized', message: 'OpenAI control plane rejected the runtime API key' } };
      case 'unreachable':
        return { status: 'degraded', lastError: { component: 'openai', code: 'control-plane-unreachable', message: 'OpenAI control plane is unreachable' } };
      case 'error':
        return { status: 'error', lastError: { component: 'openai', code: 'runtime-api-key-missing', message: 'OpenAI runtime status is error: the Runtime API key is not configured' } };
      default:
        // unknown: key configured but connectivity not yet verified.
        return { status: 'degraded' };
    }
  }
  if (tunnel.processRunning) {
    return { status: 'degraded' };
  }
  return { status: 'stopped' };
}

/**
 * Lifecycle/ownership error codes that must stay latched. While such an
 * error is pending AND the manager still holds an owned runtime handle it
 * could not safely converge, ordinary refresh()/polling — which only proves
 * the runtime is alive/ready — must never restore overall to ready. Only an
 * explicit resolution (confirmed stop, confirmed cleanup, successful fresh
 * start) clears the latch. These are the real RuntimeError codes emitted by
 * ProcessTunnelRuntime / ProcessIdentity; no synthetic codes are introduced.
 */
export const LATCHED_LIFECYCLE_ERROR_CODES = [
  'stale-process-identity',
  'start-time-mismatch',
  'unknown-start-time',
  'tunnel-stop-timeout',
] as const;

/** True when the given error is one of the latched lifecycle/ownership codes. */
export function isLatchedLifecycleError(error: { code: string } | undefined): boolean {
  return error !== undefined && (LATCHED_LIFECYCLE_ERROR_CODES as readonly string[]).includes(error.code);
}

/**
 * Trustworthy "the owned runtime is confirmed gone" evidence, from a status
 * probe that SUCCEEDED. A thrown probe is NOT evidence — callers must never
 * pass a synthetic/unknown status here. `processRunning=true` always means
 * the runtime is (or may be) alive, so confirmed-gone requires
 * `processRunning=false` PLUS an explicit stopped/exited marker from the
 * backend: `status=stopped` or `lastError.code=unexpected-exit` (the real
 * codes emitted by ProcessTunnelRuntime.status()). Anything else — including
 * a bare `status=error` without exit evidence — is "unknown", not "gone".
 */
export function confirmsRuntimeGone(status: TunnelRuntimeStatus): boolean {
  if (status.processRunning) {
    return false;
  }
  return status.status === 'stopped' || status.lastError?.code === 'unexpected-exit';
}

export class RuntimeManager {
  readonly configStore: ConfigStore;
  readonly secretStore: SecretStore;
  readonly profileGenerator: ProfileGenerator;

  private readonly dshHome: string;
  private readonly bridgeUrl: string;
  private readonly bridgeToken: string;
  private readonly logger: ControlLogger;
  private readonly runtime: TunnelRuntime;
  private readonly pollIntervalMs: number;
  private readonly readyTimeoutMs: number;
  private readonly now: () => number;

  private snapshot: RuntimeSnapshot;
  private handle: TunnelRuntimeHandle | undefined;
  private pendingError: RuntimeSnapshot['lastError'] | undefined;
  private tail: Promise<unknown> = Promise.resolve();
  private pollTimer: NodeJS.Timeout | undefined;
  private autoStartTimer: NodeJS.Timeout | undefined;
  private started = false;

  private cachedDetection: { at: number; value: Awaited<ReturnType<TunnelRuntime['detect']>> } | undefined;
  private cachedControlPlane: { at: number; value: ControlPlaneProbeResult } | undefined;
  private cachedDiscovery: { at: number; value: ExistingRuntimeDiscovery } | undefined;
  private readonly discoverFn?: () => ExistingRuntimeDiscovery;

  constructor(options: RuntimeManagerOptions) {
    this.dshHome = options.dshHome;
    this.bridgeUrl = options.bridge.url;
    this.bridgeToken = options.bridge.token;
    this.logger = options.logger ?? silentLogger();
    this.pollIntervalMs = options.pollIntervalMs ?? 2000;
    this.readyTimeoutMs = options.readyTimeoutMs ?? 30_000;
    this.now = options.now ?? (() => Date.now());
    this.runtime = options.createRuntime !== undefined ? options.createRuntime() : new ProcessTunnelRuntime({ logger: this.logger });
    this.configStore = new ConfigStore(this.dshHome);
    this.secretStore = new SecretStore(this.dshHome);
    this.profileGenerator = new ProfileGenerator(join(this.dshHome, 'chatgpt-bridge', 'tunnel-profiles'));
    this.snapshot = this.initialSnapshot();
    this.discoverFn = options.discover;
  }

  /** Begin the poller and (when configured) schedule auto-start. */
  activate(): void {
    if (this.started) return;
    this.started = true;
    this.autoStartTimer = undefined;
    this.pollTimer = setInterval(() => void this.refresh(), this.pollIntervalMs);
    void this.refresh();
    const cfg = this.configStore.load();
    if (cfg.tunnel.autoStart) {
      const delay = 1500;
      this.autoStartTimer = setTimeout(() => {
        this.autoStartTimer = undefined;
        void this.start().catch(() => {});
      }, delay);
    }
  }

  /** The current composite snapshot (the single status authority's view). */
  getSnapshot(): RuntimeSnapshot {
    return this.snapshot;
  }

  getConfig(): RuntimeConfig {
    return this.configStore.load();
  }

  /**
   * Non-secret hints from an already-installed tunnel-client / official
   * profile / env proxy. Never reads secret values onto the result.
   */
  getDiscovery(): ExistingRuntimeDiscovery {
    try {
      if (this.cachedDiscovery !== undefined && this.now() - this.cachedDiscovery.at < DETECTION_TTL_MS) {
        return this.cachedDiscovery.value;
      }
      const value =
        this.discoverFn !== undefined
          ? this.discoverFn()
          : discoverExistingRuntime({ configuredExecutable: this.configStore.load().tunnel.executable });
      this.cachedDiscovery = { at: this.now(), value };
      return value;
    } catch {
      return {};
    }
  }

  /** Cached tunnel-client detection (for the config/status surfaces). */
  async getDetection(): Promise<Awaited<ReturnType<TunnelRuntime['detect']>>> {
    const cfg = this.configStore.load();
    this.runtime.configure?.({ executable: cfg.tunnel.executable });
    return this.detectWithCache(false);
  }

  /** Persist non-secret config; serialized with mutations. */
  saveConfig(patch: Partial<RuntimeConfig>): Promise<RuntimeConfig> {
    return this.enqueue(() => {
      const next = this.configStore.update((current) => mergeConfig(current, patch));
      this.cachedDetection = undefined;
      this.cachedDiscovery = undefined;
      // Any config change may alter the control-plane network/auth path
      // (proxy.enabled/host/port, controlPlaneBaseUrl, Runtime API Key).
      // Invalidate so the next status refresh re-probes immediately instead
      // of serving a result up to CONTROL_PLANE_PROBE_TTL_MS stale.
      this.cachedControlPlane = undefined;
      this.logger.info('runtime config saved');
      return next;
    });
  }

  start(): Promise<RuntimeSnapshot> {
    return this.enqueue(() => this.startInternal());
  }

  stop(): Promise<RuntimeSnapshot> {
    return this.enqueue(() => this.stopInternal());
  }

  restart(): Promise<RuntimeSnapshot> {
    return this.enqueue(async () => {
      this.setTunnel('stopping');
      if (this.handle !== undefined) {
        try {
          await this.runtime.stop(this.handle);
        } catch (error) {
          // Fail closed: we could not confirm the old runtime has exited, so a
          // new one MUST NOT be started. Keep the handle (we still own the old
          // process identity) and surface an error snapshot.
          this.recordError(error);
          return this.snapshot;
        }
        this.handle = undefined;
      }
      return this.startInternal();
    });
  }

  /** Run layered diagnostics against current state. */
  async diagnostics(): Promise<{ ok: boolean; steps: DoctorStep[] }> {
    const cfg = this.configStore.load();
    const detection = await this.detectWithCache(true);
    const endpoint = this.effectiveEndpoint(cfg);
    const bridgeProbe = await probeBridge({ url: endpoint, token: this.bridgeToken });
    let tunnelRunning = false;
    let tunnelHealthy = false;
    let tunnelReady = false;
    let statusProbeFailed = false;
    if (this.handle !== undefined) {
      try {
        const status = await this.runtime.status(this.handle);
        tunnelRunning = status.processRunning;
        tunnelHealthy = status.healthy;
        tunnelReady = status.ready;
      } catch (error) {
        // Same provenance as refresh(): a thrown status probe is unknown, never
        // "stopped". Ownership is retained; diagnostics reports status-failed.
        statusProbeFailed = true;
        this.logger.warn(`diagnostics status probe failed: ${redactText(error instanceof Error ? error.message : String(error))}`);
      }
    } else {
      const observed = await this.observeExternalTunnel();
      tunnelRunning = observed.processRunning;
      tunnelHealthy = observed.healthy;
      tunnelReady = observed.ready;
    }
    const externalReady = this.handle === undefined && tunnelReady;
    const keyConfigured = externalReady || this.secretStore.runtimeApiKeyConfigured() || this.getDiscovery().runtimeApiKeyAvailable === true;
    const controlPlaneBaseUrl = cfg.openai.controlPlaneBaseUrl ?? DEFAULT_CONTROL_PLANE;
    // A ready external runtime is authoritative for its own control-plane
    // connection and may use a different official profile/env key. Owned or
    // stopped paths keep using the plugin key probe, so status and diagnostics
    // remain strict and consistent for plugin-managed startup.
    const cpProbe: ControlPlaneProbeResult = externalReady
      ? { status: 'connected' }
      : await this.controlPlaneStatus(cfg);
    const controlPlaneStatus = cpProbe.status;
    const proxyConfigured = cfg.tunnel.proxy?.enabled === true || this.getDiscovery().proxyInUse === true;
    const proxyValid = !proxyConfigured || (cfg.tunnel.proxy?.host !== undefined && cfg.tunnel.proxy.host !== '' && (cfg.tunnel.proxy.port ?? 0) > 0);
    const steps = buildDiagnosticSteps({
      detection,
      bridgeProbe,
      tunnelRunning,
      tunnelHealthy,
      tunnelReady,
      ...(statusProbeFailed ? { statusProbeFailed: true } : {}),
      runtimeApiKeyConfigured: keyConfigured,
      controlPlaneBaseUrl,
      controlPlaneStatus,
      ...(cpProbe.error !== undefined || cpProbe.stage !== undefined || cpProbe.proxy !== undefined
        ? { controlPlaneError: { code: cpProbe.error, stage: cpProbe.stage, proxy: cpProbe.proxy } }
        : {}),
      proxyConfigured,
      proxyValid,
    });
    // Tunnel-client doctor: real `tunnel-client doctor --profile-file ... --json`
    // normalized into the same structured step shape. Never falls over the API:
    // a doctor failure becomes a structured failed step, and every detail string
    // is redacted before it leaves this method.
    let doctorSteps: DoctorStep[] = [];
    // The generated plugin profile and doctor describe a future/owned launch,
    // not an already-running external process. Do not report that unrelated
    // plugin key/profile as a failure of a ready external tunnel.
    if (!externalReady && detection.installed && detection.executablePath !== undefined) {
      try {
        const launch = await this.buildLaunchConfig(cfg, detection);
        const doctor = await this.runtime.doctor(launch);
        doctorSteps = doctor.steps.map((step) => ({
          ...step,
          ...(step.detail === undefined ? {} : { detail: redactText(step.detail) }),
        }));
      } catch (error) {
        const runtimeError = error instanceof RuntimeError ? error : undefined;
        doctorSteps = [
          {
            id: 'doctor',
            ok: false,
            code: runtimeError?.code ?? 'doctor-failed',
            detail: redactText(error instanceof Error ? error.message : String(error)),
          },
        ];
      }
    }
    steps.push(...doctorSteps);
    return { ok: steps.every((step) => step.ok), steps };
  }

  /** Stop the owned runtime and release the poller. Called on DSH unload. */
  async dispose(): Promise<void> {
    // A pending auto-start must never fire after the plugin has been disposed.
    if (this.autoStartTimer !== undefined) {
      clearTimeout(this.autoStartTimer);
      this.autoStartTimer = undefined;
    }
    if (this.pollTimer !== undefined) {
      clearInterval(this.pollTimer);
      this.pollTimer = undefined;
    }
    await this.enqueue(async () => {
      if (this.handle !== undefined) {
        const handle = this.handle;
        try {
          await this.runtime.stop(handle);
          if (this.handle === handle) {
            this.handle = undefined;
          }
        } catch (error) {
          // Unload-time ownership failure: the process may still be alive.
          // Keep the handle (no further spawn can happen once the manager is
          // disposed, but we must not report a clean stop), and log a
          // redacted warning for diagnosis.
          this.logger.warn(`unload: could not confirm runtime shutdown: ${redactText(error instanceof Error ? error.message : String(error))}`);
        }
      }
      try {
        await this.runtime.dispose();
      } catch {
        // best-effort
      }
    });
  }

  // ---------------------------------------------------------------- internal

  private async startInternal(): Promise<RuntimeSnapshot> {
    if (this.handle === undefined && this.getDiscovery().runningProcess !== undefined) {
      // An already-running tunnel-client is observed, never adopted. Spawning
      // a second one would duplicate the channel the user already has working.
      this.logger.info('start skipped: an external tunnel-client is already running');
      await this.refresh();
      return this.snapshot;
    }
    this.setTunnel('starting');
    try {
      const cfg = this.configStore.load();
      const endpoint = this.effectiveEndpoint(cfg);
      if (this.handle !== undefined) {
        let status: TunnelRuntimeStatus;
        try {
          status = await this.runtime.status(this.handle);
        } catch {
          // Status unknown: never treat as confirmed gone and never spawn a
          // second runtime. Refresh (fail-closed snapshot) and refuse.
          this.logger.warn('refusing start: runtime status probe failed');
          await this.refresh();
          return this.snapshot;
        }
        if (status.processRunning && status.ready) {
          await this.refresh();
          return this.snapshot;
        }
        // An owned handle whose shutdown was never confirmed (e.g. a failed
        // start whose cleanup stop failed) MUST NOT be replaced by a fresh
        // spawn: that could leave two runtimes. Fail closed in the manager —
        // never trust the backend to refuse a double start.
        const unresolved =
          status.processRunning ||
          status.status === 'starting' ||
          status.status === 'running' ||
          status.status === 'stopping';
        if (unresolved) {
          this.logger.warn('refusing start: previous runtime still active with unconfirmed shutdown');
          await this.refresh();
          return this.snapshot;
        }
        // A successful probe whose state is not trusted confirmed-gone
        // evidence (stopped / unexpected-exit) is "unknown", never "released":
        // starting a new runtime on uncertainty could orphan a still-running
        // one.
        if (!confirmsRuntimeGone(status)) {
          this.logger.warn('refusing start: previous runtime state unknown (no confirmed exit evidence)');
          await this.refresh();
          return this.snapshot;
        }
        // Backend confirms the process is no longer running (stopped or
        // exited): the stale handle is safe to release and a fresh start is
        // allowed.
        this.handle = undefined;
      }
      const probe = await probeBridge({ url: endpoint, token: this.bridgeToken });
      if (!probe.listening) {
        throw new RuntimeError('bridge-unavailable', `Bridge is not listening at ${endpoint}`, 'bridge');
      }
      if (!probe.authenticated) {
        throw new RuntimeError('bridge-auth-failed', 'Bridge rejected the authorization token', 'bridge');
      }
      this.runtime.configure?.({ executable: cfg.tunnel.executable });
      const detection = await this.detectWithCache(true);
      if (!detection.installed || detection.executablePath === undefined) {
        throw new RuntimeError('tunnel-client-not-installed', detection.error ?? 'tunnel-client not installed', 'tunnel');
      }
      const launch = await this.buildLaunchConfig(cfg, detection);
      try {
        this.handle = await this.runtime.start(launch);
      } catch (error) {
        // start() may throw after spawn (health-url timeout, identity-failed
        // cleanup). Adopt the leftover owned handle so we never orphan a live
        // process or allow a second spawn.
        if (this.handle === undefined) {
          this.handle = this.runtime.ownedHandle();
        }
        throw error;
      }
      const ready = await this.waitForReady(this.readyTimeoutMs);
      if (!ready) {
        let code = 'tunnel-not-ready';
        try {
          const status = await this.runtime.status(this.handle);
          code = status.lastError?.code ?? 'tunnel-not-ready';
        } catch {
          // Status unknown: still attempt ownership-safe cleanup below.
        }
        await this.safeStopHandle();
        throw new RuntimeError(code, 'tunnel did not become ready', 'tunnel');
      }
      this.logger.info('tunnel started and ready');
      this.clearError();
      await this.refresh();
      return this.snapshot;
    } catch (error) {
      this.recordError(error);
      await this.refresh();
      return this.snapshot;
    }
  }

  private async stopInternal(): Promise<RuntimeSnapshot> {
    this.setTunnel('stopping');
    try {
      if (this.handle === undefined) {
        await this.refresh();
        return this.snapshot;
      }
      await this.runtime.stop(this.handle);
      this.handle = undefined;
      this.logger.info('tunnel stopped');
      this.clearError();
      await this.refresh();
      return this.snapshot;
    } catch (error) {
      this.recordError(error);
      await this.refresh();
      return this.snapshot;
    }
  }

  /**
   * Stop the owned runtime and release ownership ONLY after shutdown is
   * confirmed. This is the single ownership gate for failed-start cleanup.
   * If stop() throws, the process may still be alive: the handle is retained
   * and the error propagates (fail closed) so callers surface it and never
   * pretend the runtime is gone.
   */
  private async safeStopHandle(): Promise<void> {
    if (this.handle === undefined) return;
    const handle = this.handle;
    await this.runtime.stop(handle);
    if (this.handle === handle) {
      this.handle = undefined;
    }
  }

  private async waitForReady(timeoutMs: number): Promise<boolean> {
    if (this.handle === undefined) return false;
    const deadline = this.now() + timeoutMs;
    while (this.now() < deadline) {
      let status: TunnelRuntimeStatus;
      try {
        status = await this.runtime.status(this.handle);
      } catch {
        return false;
      }
      if (status.processRunning && status.healthy && status.ready) return true;
      if (status.status === 'error') return false;
      await sleep(500);
    }
    return false;
  }

  private async detectWithCache(force: boolean): Promise<Awaited<ReturnType<TunnelRuntime['detect']>>> {
    if (!force && this.cachedDetection !== undefined && this.now() - this.cachedDetection.at < DETECTION_TTL_MS) {
      return this.cachedDetection.value;
    }
    const value = await this.runtime.detect();
    this.cachedDetection = { at: this.now(), value };
    return value;
  }

  /**
   * True while an unresolved lifecycle/ownership error is latched: the
   * manager still holds a handle whose shutdown/identity was never confirmed.
   * Health/readiness probing can never resolve this — see refresh().
   */
  private hasUnresolvedLifecycleError(): boolean {
    return this.handle !== undefined && isLatchedLifecycleError(this.pendingError);
  }

  /** Refresh the composite snapshot from real probes. */
  async refresh(): Promise<void> {
    const cfg = this.configStore.load();
    const endpoint = this.effectiveEndpoint(cfg);
    const bridgeProbe = await probeBridge({ url: endpoint, token: this.bridgeToken });

    let statusProbeFailed = false;
    let tunnel: RuntimeSnapshot['tunnel'];
    if (this.handle !== undefined) {
      let status: TunnelRuntimeStatus;
      try {
        status = await this.runtime.status(this.handle);
      } catch (error) {
        // A thrown status probe is "unknown", never "confirmed exited". The
        // synthetic status below is only a UI representation ("currently
        // cannot confirm it is running"); it must NEVER be treated as
        // ownership-release evidence.
        statusProbeFailed = true;
        this.logger.warn(`runtime status probe failed: ${redactText(error instanceof Error ? error.message : String(error))}`);
        status = { status: 'error', processRunning: false, healthy: false, ready: false, lastError: { code: 'status-failed', message: 'runtime status unavailable' } };
      }
      // Ownership release requires trusted confirmed-gone evidence from a
      // SUCCESSFUL probe. Releasing the handle on a failed probe could
      // orphan a still-running runtime and permit a duplicate backend start.
      if (!statusProbeFailed && confirmsRuntimeGone(status)) {
        this.logger.warn('tunnel runtime confirmed exited; ownership released');
        this.handle = undefined;
        const observed = await this.observeExternalTunnel();
        if (observed.processRunning) {
          tunnel = observed;
        } else if (status.status === 'error' || status.lastError?.code === 'unexpected-exit') {
          tunnel = {
            status: 'error',
            processRunning: false,
            healthy: false,
            ready: false,
            ...(status.pid === undefined ? {} : { pid: status.pid }),
          };
        } else {
          tunnel = observed;
        }
      } else {
        tunnel = {
          status: status.status,
          processRunning: status.processRunning,
          healthy: status.healthy,
          ready: status.ready,
          owned: true,
          ...(status.pid === undefined ? {} : { pid: status.pid }),
        };
      }
    } else {
      tunnel = await this.observeExternalTunnel();
    }

    const pluginKey = this.secretStore.runtimeApiKeyConfigured();
    const externalReady = tunnel.owned === false && tunnel.ready;
    // A ready external tunnel is authoritative evidence about its own
    // control-plane connection. It may use a different official profile/env
    // key, so an optional stale plugin key must not override that live state.
    // Owned runtimes stay strict: they are launched from the plugin's secret
    // store and must have that key present and accepted by the control plane.
    let openaiStatus: RuntimeSnapshot['openai']['status'] = 'unknown';
    if (externalReady) {
      openaiStatus = 'connected';
    } else if (tunnel.ready) {
      openaiStatus = pluginKey ? (await this.controlPlaneStatus(cfg)).status : 'error';
    }

    const bridgeStatus: RuntimeSnapshot['bridge'] = {
      status: bridgeProbe.status,
      url: endpoint,
      reachable: bridgeProbe.reachable,
    };
    // A latched lifecycle/ownership error overrides whatever the live probes
    // would derive: the runtime being alive/ready proves it can serve, NOT
    // that the previously failed shutdown/identity problem has been resolved.
    // overall cannot return to ready until an explicit resolution (confirmed
    // stop, confirmed cleanup, successful fresh start) clears the latch.
    const latchedError = this.hasUnresolvedLifecycleError() ? this.pendingError : undefined;
    // A failed status probe is fail-closed "unknown": surface status-failed
    // (rather than a generic tunnel-error that could read as "the runtime is
    // gone") and keep overall away from ready. It recovers automatically once
    // a probe on the same retained handle succeeds again.
    const probeError: RuntimeSnapshot['lastError'] | undefined = statusProbeFailed
      ? { component: 'tunnel', code: 'status-failed', message: 'runtime status unavailable' }
      : undefined;
    const overallResult =
      latchedError !== undefined
        ? { status: 'error' as const, lastError: latchedError }
        : probeError !== undefined
          ? { status: 'error' as const, lastError: probeError }
          : deriveOverallStatus({ bridge: bridgeStatus, tunnel, openai: openaiStatus });
    const lastError = overallResult.lastError ?? this.pendingError;
    this.snapshot = {
      bridge: bridgeStatus,
      tunnel,
      openai: { status: openaiStatus },
      overall: { status: overallResult.status },
      ...(lastError === undefined ? {} : { lastError }),
      updatedAt: new Date(this.now()).toISOString(),
    };
  }

  /**
   * The single Control Plane probe shared by the status refresh and
   * diagnostics (force=true bypasses the TTL cache). Proxy settings come ONLY
   * from user config (cfg.tunnel.proxy): an enabled proxy is authoritative
   * (fail closed — never a silent fallback to direct). The result carries only
   * redacted host:port provenance; secrets never enter it or the logs.
   */
  private async controlPlaneStatus(cfg: RuntimeConfig, force = false): Promise<ControlPlaneProbeResult> {
    const cached = this.cachedControlPlane;
    if (!force && cached !== undefined && this.now() - cached.at < CONTROL_PLANE_PROBE_TTL_MS) {
      return cached.value;
    }
    const baseUrl = controlPlaneProbeUrl(cfg.openai.controlPlaneBaseUrl ?? DEFAULT_CONTROL_PLANE, cfg.tunnel.tunnelId);
    const key = this.secretStore.runtimeApiKeyConfigured() ? this.secretStore.readRuntimeApiKey() : undefined;
    const proxy = this.resolveProxy(cfg);
    const value = await probeControlPlane({
      baseUrl,
      apiKey: key,
      ...(proxy?.enabled === true ? { proxy: { host: proxy.host, port: proxy.port } } : {}),
    });
    this.cachedControlPlane = { at: this.now(), value };
    if (value.status !== 'connected') {
      const parts: string[] = [];
      if (value.error !== undefined) parts.push(value.error);
      if (value.stage !== undefined) parts.push('stage=' + value.stage);
      if (value.proxy !== undefined) parts.push('proxy=' + value.proxy);
      if (parts.length > 0) this.logger.warn('control plane probe failed: ' + parts.join(' '));
    }
    return value;
  }

  private setTunnel(status: RuntimeSnapshot['tunnel']['status']): void {
    this.snapshot = {
      ...this.snapshot,
      tunnel: { ...this.snapshot.tunnel, status },
      updatedAt: new Date(this.now()).toISOString(),
    };
  }

  private recordError(error: unknown): void {
    const message = redactText(error instanceof Error ? error.message : String(error));
    const code = error instanceof RuntimeError ? error.code : 'runtime-error';
    const component = error instanceof RuntimeError ? error.component : 'runtime';
    this.logger.warn(`runtime mutation failed: ${message}`);
    this.pendingError = { component, code, message };
    this.snapshot = {
      ...this.snapshot,
      tunnel: { ...this.snapshot.tunnel, status: this.snapshot.tunnel.status === 'starting' || this.snapshot.tunnel.status === 'stopping' ? 'error' : this.snapshot.tunnel.status },
      // A failed mutation must never leave overall stale at `ready`.
      overall: { status: 'error' },
      lastError: { component, code, message },
      updatedAt: new Date(this.now()).toISOString(),
    };
  }

  /**
   * Drop the last error once a mutation explicitly resolves the previous
   * failure: confirmed stop, confirmed cleanup, or a successful fresh start.
   * Never invoked from refresh()/polling — health/readiness cannot clear a
   * latched lifecycle/ownership error.
   */
  private clearError(): void {
    this.pendingError = undefined;
    const { lastError: _drop, ...rest } = this.snapshot;
    void _drop;
    this.snapshot = { ...rest, updatedAt: new Date(this.now()).toISOString() };
  }

  private effectiveEndpoint(cfg: RuntimeConfig): string {
    return cfg.bridge.endpoint ?? this.bridgeUrl;
  }

  /**
   * Read-only observation of a tunnel-client this plugin did not start.
   * Never takes ownership: Stop will not kill the process.
   */
  private async observeExternalTunnel(): Promise<RuntimeSnapshot['tunnel']> {
    const detection = await this.detectWithCache(false);
    const discovered = this.getDiscovery();
    const running = discovered.runningProcess;
    if (running === undefined || !Number.isInteger(running.pid) || running.pid <= 0) {
      return {
        status: detection.installed ? 'stopped' : 'not-installed',
        processRunning: false,
        healthy: false,
        ready: false,
      };
    }
    let healthy = false;
    let ready = false;
    if (discovered.healthBaseUrl !== undefined && discovered.healthBaseUrl !== '') {
      const probe = await probeTunnelHealth(discovered.healthBaseUrl);
      healthy = probe.healthy;
      ready = probe.ready;
    }
    return {
      status: 'running',
      processRunning: true,
      healthy,
      ready,
      pid: running.pid,
      owned: false,
    };
  }

  private resolveProxy(cfg: RuntimeConfig): { enabled: true; scheme: 'http' | 'socks5'; host: string; port: number } | undefined {
    const proxy = cfg.tunnel.proxy;
    if (proxy?.enabled !== true) return undefined;
    return {
      enabled: true,
      scheme: 'http',
      host: proxy.host ?? '127.0.0.1',
      port: proxy.port ?? 0,
    };
  }

  /**
   * Build the fully-expanded launch config shared by start and doctor. Throws
   * a RuntimeError when required runtime prerequisites are missing (key,
   * tunnel id, proxy validity), so callers can map the failure instead of
   * passing a half-built config to the backend.
   */
  private async buildLaunchConfig(cfg: RuntimeConfig, detection: { installed: boolean; executablePath?: string; error?: string }): Promise<TunnelLaunchConfig> {
    if (!this.secretStore.runtimeApiKeyConfigured()) {
      throw new RuntimeError('runtime-api-key-missing', 'Runtime API key is not configured', 'openai');
    }
    const tunnelId = cfg.tunnel.tunnelId;
    if (tunnelId === undefined || tunnelId === '') {
      throw new RuntimeError('tunnel-id-missing', 'Tunnel ID is not configured', 'runtime');
    }
    const proxy = this.resolveProxy(cfg);
    if (proxy?.enabled === true && (proxy.host === '' || proxy.port <= 0)) {
      throw new RuntimeError('proxy-invalid', 'Proxy host or port is invalid', 'runtime');
    }
    const authRef = this.secretStore.ensureMcpAuthorization(this.bridgeToken);
    const keyRef = this.secretStore.runtimeApiKeyRef;
    const profileName = cfg.tunnel.profileName ?? 'chatgpt-bridge';
    const healthUrlFile = join(this.dshHome, 'chatgpt-bridge', 'tunnel-health.url');
    const pidFile = join(this.dshHome, 'chatgpt-bridge', 'tunnel.pid');
    try {
      rmSync(healthUrlFile, { force: true });
      rmSync(pidFile, { force: true });
    } catch {
      // best-effort
    }
    const logFile = join(this.dshHome, 'chatgpt-bridge', 'logs', 'tunnel-client.ndjson');
    const endpoint = this.effectiveEndpoint(cfg);
    const profilePath = this.profileGenerator.write(profileName, {
      controlPlaneBaseUrl: cfg.openai.controlPlaneBaseUrl ?? DEFAULT_CONTROL_PLANE,
      tunnelId,
      runtimeApiKeyRef: keyRef,
      mcpAuthorizationRef: authRef,
      bridgeUrl: endpoint,
      healthListenAddr: '127.0.0.1:0',
      healthUrlFile,
      logFile,
      logLevel: 'info',
    });
    return {
      executablePath: detection.executablePath as string,
      profilePath,
      profileDir: this.profileGenerator.directory,
      profileName,
      tunnelId,
      runtimeApiKeyRef: keyRef,
      mcpAuthorizationRef: authRef,
      bridgeUrl: endpoint,
      healthUrlFile,
      pidFile,
      logFile,
      ...(proxy === undefined ? {} : { proxy }),
    };
  }

  private initialSnapshot(): RuntimeSnapshot {
    const endpoint = this.bridgeUrl;
    return {
      bridge: { status: 'offline', url: endpoint, reachable: false },
      tunnel: { status: 'stopped', processRunning: false, healthy: false, ready: false },
      openai: { status: 'unknown' },
      overall: { status: 'stopped' },
      updatedAt: new Date(this.now()).toISOString(),
    };
  }

  private enqueue<T>(op: () => Promise<T> | T): Promise<T> {
    const run = this.tail.then(op, op);
    this.tail = run.then(
      () => undefined,
      () => undefined,
    );
    return run;
  }
}

function mergeConfig(current: RuntimeConfig, patch: Partial<RuntimeConfig>): RuntimeConfig {
  return mergeRuntimeConfig(current, patch);
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
