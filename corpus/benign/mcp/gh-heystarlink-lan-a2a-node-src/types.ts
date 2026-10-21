import type { ThreadEvent } from "@openai/codex-sdk";

export type Permission = "read-only" | "workspace-write";
export type WebSearchMode = "disabled" | "cached" | "live";
export type TaskStatus =
  | "pending_acceptance"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "rejected";

export interface WorkspaceConfig {
  path: string;
  maxPermission: Permission;
  skipGitRepoCheck: boolean;
  networkAccessEnabled: boolean;
  webSearchMode: WebSearchMode;
}

export interface RuntimeConfig {
  configPath: string;
  nodeName: string;
  host: string;
  port: number;
  dataDir: string;
  logFile: string;
  maxConcurrentTasks: number;
  discoveryEnabled: boolean;
  workspaces: Record<string, WorkspaceConfig>;
}

export interface PeerPolicy {
  autoAccept: boolean;
  workspace: string | null;
  permission: Permission;
}

export interface PeerRecord {
  nodeId: string;
  name: string;
  url: string;
  fingerprint: string;
  publicKey: string;
  pairedAt: string;
  updatedAt: string;
  policy: PeerPolicy;
}

export interface NodeAttestation {
  protocolVersion: 1;
  nodeId: string;
  nodeName: string;
  fingerprint: string;
  publicKey: string;
  issuedAt: string;
  nonce: string;
  signature: string;
}

export interface NearbyAgent {
  nodeId: string;
  name: string;
  url: string;
  fingerprint: string;
  lastSeenAt: string;
}

export interface TaskRecord {
  id: string;
  requesterNodeId: string;
  requesterName: string;
  objective: string;
  summary: string | null;
  expectedOutput: string | null;
  status: TaskStatus;
  workspace: string | null;
  permission: Permission | null;
  threadId: string | null;
  result: string | null;
  error: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ExecuteInput {
  taskId: string;
  prompt: string;
  threadId: string | null;
  workspace: WorkspaceConfig;
  permission: Permission;
  signal: AbortSignal;
  onEvent: (event: ThreadEvent) => void;
}

export interface ExecuteResult {
  threadId: string;
  finalResponse: string;
}

export interface AgentExecutor {
  execute(input: ExecuteInput): Promise<ExecuteResult>;
}
