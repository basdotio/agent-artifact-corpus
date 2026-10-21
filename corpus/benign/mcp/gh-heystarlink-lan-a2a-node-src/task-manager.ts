import { randomUUID } from "node:crypto";
import type { AuditLog } from "./audit-log.js";
import { permissionAllowed } from "./config.js";
import type {
  AgentExecutor,
  PeerRecord,
  Permission,
  RuntimeConfig,
  TaskRecord,
} from "./types.js";

interface IncomingTask {
  taskId?: string;
  objective: string;
  summary?: string | null;
  expectedOutput?: string | null;
}

export class TaskManager {
  private readonly tasks = new Map<string, TaskRecord>();
  private readonly queue: Array<{ taskId: string; prompt: string }> = [];
  private readonly controllers = new Map<string, AbortController>();
  private running = 0;

  constructor(
    private readonly config: RuntimeConfig,
    private readonly executor: AgentExecutor,
    private readonly audit: AuditLog,
  ) {}

  list(): TaskRecord[] {
    return [...this.tasks.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }

  stop(): void {
    for (const { taskId } of this.queue) {
      const task = this.tasks.get(taskId);
      if (task?.status === "queued") {
        task.status = "cancelled";
        task.error = "节点停止，内存任务已取消";
        task.updatedAt = new Date().toISOString();
        this.log("task.cancelled", task);
      }
    }
    this.queue.length = 0;
    for (const [taskId, controller] of this.controllers) {
      controller.abort();
      const task = this.tasks.get(taskId);
      if (task && ["queued", "running"].includes(task.status)) {
        task.status = "cancelled";
        task.error = "节点停止，内存任务已取消";
        task.updatedAt = new Date().toISOString();
        this.log("task.cancelled", task);
      }
    }
    this.controllers.clear();
  }

  require(taskId: string): TaskRecord {
    const task = this.tasks.get(taskId);
    if (!task) throw new Error(`内存中不存在任务：${taskId}，服务重启后任务状态不会恢复`);
    return task;
  }

  receive(peer: PeerRecord, input: IncomingTask): TaskRecord {
    const taskId = input.taskId ?? randomUUID();
    const existing = this.tasks.get(taskId);
    if (existing) {
      if (existing.requesterNodeId === peer.nodeId && existing.objective === input.objective) return existing;
      throw new Error("任务 ID 已被其他请求占用");
    }
    const now = new Date().toISOString();
    const task: TaskRecord = {
      id: taskId,
      requesterNodeId: peer.nodeId,
      requesterName: peer.name,
      objective: input.objective,
      summary: input.summary?.trim() || null,
      expectedOutput: input.expectedOutput?.trim() || null,
      status: "pending_acceptance",
      workspace: null,
      permission: null,
      threadId: null,
      result: null,
      error: null,
      createdAt: now,
      updatedAt: now,
    };
    this.tasks.set(task.id, task);
    this.log("task.received", task);
    if (peer.policy.autoAccept && peer.policy.workspace) {
      this.accept(task.id, peer.policy.workspace, peer.policy.permission);
    }
    return task;
  }

  accept(taskId: string, workspaceName: string, permission: Permission): TaskRecord {
    const task = this.require(taskId);
    if (task.status !== "pending_acceptance") throw new Error("任务当前不等待接收");
    const workspace = this.config.workspaces[workspaceName];
    if (!workspace) throw new Error(`工作区不在允许列表：${workspaceName}`);
    if (!permissionAllowed(permission, workspace.maxPermission)) throw new Error("请求权限超过工作区上限");
    task.workspace = workspaceName;
    task.permission = permission;
    task.status = "queued";
    task.updatedAt = new Date().toISOString();
    this.log("task.accepted", task);
    this.enqueue(task.id, taskPrompt(task));
    return task;
  }

  reject(taskId: string, reason = "接收节点拒绝任务"): TaskRecord {
    const task = this.require(taskId);
    if (task.status !== "pending_acceptance") throw new Error("任务当前不能拒绝");
    task.status = "rejected";
    task.error = reason;
    task.updatedAt = new Date().toISOString();
    this.log("task.rejected", task);
    return task;
  }

  followUp(taskId: string, requesterNodeId: string, prompt: string): TaskRecord {
    const task = this.requireOwned(taskId, requesterNodeId);
    if (!task.workspace || !task.permission || !task.threadId) throw new Error("任务尚未完成首次执行，不能追问");
    if (["queued", "running"].includes(task.status)) throw new Error("任务已有正在执行的消息");
    task.status = "queued";
    task.result = null;
    task.error = null;
    task.updatedAt = new Date().toISOString();
    this.log("task.follow_up", task);
    this.enqueue(task.id, prompt);
    return task;
  }

  cancel(taskId: string, requesterNodeId: string): TaskRecord {
    const task = this.requireOwned(taskId, requesterNodeId);
    if (!["pending_acceptance", "queued", "running"].includes(task.status)) return task;
    const index = this.queue.findIndex((item) => item.taskId === task.id);
    if (index >= 0) this.queue.splice(index, 1);
    this.controllers.get(task.id)?.abort();
    task.status = "cancelled";
    task.error = "请求节点取消任务";
    task.updatedAt = new Date().toISOString();
    this.log("task.cancelled", task);
    return task;
  }

  requireOwned(taskId: string, requesterNodeId: string): TaskRecord {
    const task = this.require(taskId);
    if (task.requesterNodeId !== requesterNodeId) throw new Error("任务不属于当前请求节点");
    return task;
  }

  private enqueue(taskId: string, prompt: string): void {
    this.queue.push({ taskId, prompt });
    this.drain();
  }

  private drain(): void {
    while (this.running < this.config.maxConcurrentTasks && this.queue.length > 0) {
      const next = this.queue.shift()!;
      this.running += 1;
      void this.execute(next.taskId, next.prompt).finally(() => {
        this.running -= 1;
        this.drain();
      });
    }
  }

  private async execute(taskId: string, prompt: string): Promise<void> {
    const task = this.require(taskId);
    if (task.status === "cancelled") return;
    const workspace = this.config.workspaces[task.workspace!];
    const controller = new AbortController();
    this.controllers.set(task.id, controller);
    task.status = "running";
    task.updatedAt = new Date().toISOString();
    this.log("task.started", task);
    try {
      const result = await this.executor.execute({
        taskId: task.id,
        prompt,
        threadId: task.threadId,
        workspace,
        permission: task.permission!,
        signal: controller.signal,
        onEvent: (event) => {
          void this.audit.record("agent.event", { taskId: task.id, type: event.type }).catch(() => undefined);
        },
      });
      if (controller.signal.aborted) return;
      task.threadId = result.threadId;
      task.result = result.finalResponse;
      task.status = "completed";
      task.updatedAt = new Date().toISOString();
      this.log("task.completed", task, { resultCharacters: result.finalResponse.length });
    } catch (error) {
      if (controller.signal.aborted) return;
      task.status = "failed";
      task.error = error instanceof Error ? error.message : String(error);
      task.updatedAt = new Date().toISOString();
      this.log("task.failed", task);
    } finally {
      this.controllers.delete(task.id);
    }
  }

  private log(event: string, task: TaskRecord, extra: Record<string, unknown> = {}): void {
    void this.audit.record(event, {
      taskId: task.id,
      requesterNodeId: task.requesterNodeId,
      status: task.status,
      workspace: task.workspace,
      permission: task.permission,
      ...extra,
    }).catch(() => undefined);
  }
}

function taskPrompt(task: TaskRecord): string {
  const sections = [task.objective];
  if (task.summary) sections.push(`背景：${task.summary}`);
  if (task.expectedOutput) sections.push(`期望结果：${task.expectedOutput}`);
  return sections.join("\n\n");
}
