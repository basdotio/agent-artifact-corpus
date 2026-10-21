/**
 * Control-plane types for the ChatGPT Bridge runtime manager.
 */
export interface TunnelDetectionResult {
  installed: boolean;
  executablePath?: string;
  version?: string;
  error?: string;
  /** How the binary was found. Absent when not installed. */
  source?: 'configured' | 'path' | 'well-known' | 'running-process';
}
export interface ProxyConfig {
  enabled: boolean;
  scheme: 'http' | 'socks5';
  host: string;
  port: number;
}
export interface TunnelLaunchConfig {
  executablePath: string;
  profilePath: string;
  profileDir: string;
  profileName: string;
  tunnelId: string;
  runtimeApiKeyRef: string;
  mcpAuthorizationRef: string;
  bridgeUrl: string;
  /** File where tunnel-client writes its health base URL. */
  healthUrlFile?: string;
  /** File where tunnel-client writes its process id. */
  pidFile?: string;
  /** Log file for the tunnel-client daemon (redacted on read). */
  logFile?: string;
  proxy?: ProxyConfig;
  env?: Record<string, string>;
}
export interface ProcessIdentity {
  pid: number;
  startedAt: string;
  executablePath: string;
  runtimeInstanceId: string;
  profileName?: string;
  tunnelId?: string;
}
export type TunnelRuntimeKind = 'fake' | 'process' | 'native';
export interface TunnelRuntimeHandle {
  readonly kind: TunnelRuntimeKind;
  readonly identity: ProcessIdentity;
}
export interface TunnelRuntimeStatus {
  status: 'not-installed' | 'stopped' | 'starting' | 'running' | 'stopping' | 'error';
  processRunning: boolean;
  healthy: boolean;
  ready: boolean;
  pid?: number;
  healthUrl?: string;
  uiUrl?: string;
  lastError?: { code: string; message: string };
}
export interface DoctorStep {
  id: string;
  ok: boolean;
  detail?: string;
  code?: string;
}
export interface TunnelDoctorResult {
  ok: boolean;
  steps: DoctorStep[];
}
export interface RuntimeConfig {
  schemaVersion: 1;
  tunnel: {
    executable?: string;
    tunnelId?: string;
    profileName?: string;
    proxy?: { enabled: boolean; host?: string; port?: number };
    autoStart: boolean;
  };
  openai: {
    controlPlaneBaseUrl?: string;
    runtimeApiKeyRef?: string;
  };
  bridge: {
    endpoint?: string;
  };
}
export type ErrorComponent = 'bridge' | 'tunnel' | 'openai' | 'runtime';
export interface RuntimeSnapshot {
  bridge: { status: 'running' | 'offline' | 'error'; url: string; reachable: boolean };
  tunnel: {
    status: 'not-installed' | 'stopped' | 'starting' | 'running' | 'stopping' | 'error';
    processRunning: boolean;
    healthy: boolean;
    ready: boolean;
    pid?: number;
    /** False when the process was observed, not started by this plugin. Stop must not kill it. */
    owned?: boolean;
  };
  openai: { status: 'unknown' | 'connected' | 'unreachable' | 'unauthorized' | 'error' };
  overall: { status: 'ready' | 'degraded' | 'stopped' | 'error' };
  lastError?: { component: ErrorComponent; code: string; message: string };
  updatedAt: string;
}
export type RuntimeMode = 'process' | 'native';
