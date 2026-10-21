import { randomUUID } from "node:crypto";
import { chmodSync, mkdirSync, readFileSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

export const STATE_VERSION = 1;

export type PersistedJob = {
  job_id: string;
  thread_id: string | null;
  workspace: string;
  turn_id: string | null;
  status: string;
  final_message: string | null;
  latest_diff: string | null;
  files_changed: string[];
  commands_executed: string[];
  error: string | null;
  updated_at: string;
  /** Added in v0.2. Older state files omit this and migrate to revision 0. */
  revision?: number;
  validation?: PersistedValidation[];
  warnings?: string[];
  activity?: string | null;
  completion_report_injected?: boolean;
};

export type PersistedValidation = {
  kind: string;
  command: string;
  status: string;
  exit_code?: number;
  output_tail?: string;
};

type PersistedState = {
  version: number;
  jobs: PersistedJob[];
};

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nullableString(value: unknown): string | null {
  return value === null ? null : typeof value === "string" ? value : null;
}

function optionalNullableString(value: unknown): boolean {
  return value === undefined || value === null || typeof value === "string";
}

function validValidation(value: unknown): value is PersistedValidation {
  if (!isObject(value)) return false;
  return (
    typeof value.kind === "string" && value.kind.length > 0 &&
    typeof value.command === "string" && value.command.length > 0 &&
    typeof value.status === "string" && value.status.length > 0 &&
    (value.exit_code === undefined || typeof value.exit_code === "number" && Number.isInteger(value.exit_code)) &&
    (value.output_tail === undefined || typeof value.output_tail === "string")
  );
}

function validJob(value: unknown): value is PersistedJob {
  if (!isObject(value)) return false;
  return (
    typeof value.job_id === "string" && value.job_id.length > 0 &&
    (value.thread_id === null || typeof value.thread_id === "string" && value.thread_id.length > 0) &&
    typeof value.workspace === "string" && value.workspace.length > 0 &&
    (value.turn_id === null || typeof value.turn_id === "string") &&
    typeof value.status === "string" &&
    nullableString(value.final_message) === value.final_message &&
    nullableString(value.latest_diff) === value.latest_diff &&
    Array.isArray(value.files_changed) && value.files_changed.every((item) => typeof item === "string") &&
    Array.isArray(value.commands_executed) && value.commands_executed.every((item) => typeof item === "string") &&
    nullableString(value.error) === value.error &&
    typeof value.updated_at === "string" &&
    (value.revision === undefined || typeof value.revision === "number" && Number.isInteger(value.revision) && value.revision >= 0) &&
    (value.validation === undefined || Array.isArray(value.validation) && value.validation.every(validValidation)) &&
    (value.warnings === undefined || Array.isArray(value.warnings) && value.warnings.every((item) => typeof item === "string")) &&
    optionalNullableString(value.activity) &&
    (value.completion_report_injected === undefined || typeof value.completion_report_injected === "boolean")
  );
}

function defaultState(): PersistedState {
  return { version: STATE_VERSION, jobs: [] };
}

function assertUnambiguousJobs(jobs: PersistedJob[]): void {
  const jobIds = new Set<string>();
  const threadIds = new Set<string>();
  for (const job of jobs) {
    if (jobIds.has(job.job_id)) throw new Error(`state ambiguo: job_id duplicado (${job.job_id})`);
    jobIds.add(job.job_id);
    if (job.thread_id !== null) {
      if (threadIds.has(job.thread_id)) throw new Error(`state ambiguo: thread_id duplicado (${job.thread_id})`);
      threadIds.add(job.thread_id);
    }
  }
}

export function defaultStateFile(): string {
  return path.join(os.homedir(), ".codex-agent-mcp", "state.json");
}

export class StateStore {
  readonly filePath: string;
  private diagnostic: string | null = null;

  constructor(filePath = process.env.CODEX_AGENT_STATE_FILE ?? defaultStateFile()) {
    this.filePath = path.resolve(filePath);
  }

  getDiagnostic(): string | null {
    return this.diagnostic;
  }

  load(): PersistedJob[] {
    this.diagnostic = null;
    let raw: string;
    try {
      raw = readFileSync(this.filePath, "utf8");
    } catch (error) {
      if (isObject(error) && error.code === "ENOENT") return [];
      this.diagnostic = `No se pudo leer el state local ${this.filePath}: ${error instanceof Error ? error.message : String(error)}`;
      return [];
    }

    try {
      const parsed: unknown = JSON.parse(raw);
      if (!isObject(parsed) || parsed.version !== STATE_VERSION || !Array.isArray(parsed.jobs)) {
        throw new Error(`versión o forma no soportada (se esperaba version=${STATE_VERSION})`);
      }
      const jobs = parsed.jobs.filter(validJob);
      if (jobs.length !== parsed.jobs.length) {
        throw new Error("uno o más jobs persistidos no tienen un schema válido");
      }
      assertUnambiguousJobs(jobs);
      return jobs;
    } catch (error) {
      this.diagnostic = `State local corrupto o incompatible en ${this.filePath}: ${error instanceof Error ? error.message : String(error)}`;
      return [];
    }
  }

  save(jobs: PersistedJob[]): void {
    const directory = path.dirname(this.filePath);
    mkdirSync(directory, { recursive: true });
    try {
      if (!statSync(directory).isDirectory()) {
        throw new Error("la ruta de state no es un directorio");
      }
    } catch (error) {
      throw new Error(`No se puede preparar el state local: ${error instanceof Error ? error.message : String(error)}`);
    }

    const payload: PersistedState = { version: STATE_VERSION, jobs };
    assertUnambiguousJobs(jobs);
    const temporary = path.join(directory, `.${path.basename(this.filePath)}.${process.pid}.${randomUUID()}.tmp`);
    try {
      writeFileSync(temporary, `${JSON.stringify(payload, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
      renameSync(temporary, this.filePath);
      // chmod is intentional even after replacement: it also repairs an existing
      // state file that had been created with broader permissions.
      chmodSync(this.filePath, 0o600);
    } catch (error) {
      try {
        // Best effort only; the original state remains untouched if rename failed.
        unlinkSync(temporary);
      } catch {
        // Ignore cleanup failure and preserve the original diagnostic.
      }
      throw new Error(`No se pudo publicar el state local atómicamente: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
}
