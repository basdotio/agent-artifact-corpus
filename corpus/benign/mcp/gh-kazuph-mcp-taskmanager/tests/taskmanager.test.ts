import { afterEach, beforeEach, describe, expect, it } from "vitest";
import * as fs from "node:fs/promises";
import * as os from "node:os";
import * as path from "node:path";

// Point the task file at a fresh temp directory BEFORE importing the module,
// because TASK_FILE_PATH is resolved at import time from the env var.
const tmpRoot = path.join(
  os.tmpdir(),
  `mcp-taskmanager-test-${process.pid}-${Date.now()}`
);
// Intentionally include a NON-EXISTENT nested dir to reproduce issue #4 (ENOENT).
const taskFile = path.join(tmpRoot, "nested", "deep", "tasks.json");
process.env.TASK_MANAGER_FILE_PATH = taskFile;

const { TaskManagerServer } = await import("../index.js");

async function fileExists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

describe("TaskManagerServer", () => {
  beforeEach(async () => {
    await fs.rm(tmpRoot, { recursive: true, force: true });
  });

  afterEach(async () => {
    await fs.rm(tmpRoot, { recursive: true, force: true });
  });

  it("creates missing parent directories when saving (issue #4 ENOENT)", async () => {
    expect(await fileExists(path.dirname(taskFile))).toBe(false);

    const server = new TaskManagerServer();
    const result = await server.requestPlanning("do something", [
      { title: "Task A", description: "first" },
    ]);

    expect(result.status).toBe("planned");
    // The save must have created the nested directories and the file.
    expect(await fileExists(taskFile)).toBe(true);
  });

  it("runs the full plan -> get -> done -> approve flow", async () => {
    const server = new TaskManagerServer();
    const planned = await server.requestPlanning("build feature", [
      { title: "Task A", description: "first" },
      { title: "Task B", description: "second" },
    ]);
    const requestId = planned.requestId;
    expect(requestId).toMatch(/^req-\d+$/);

    // First task
    const next1 = await server.getNextTask(requestId);
    expect(next1.status).toBe("next_task");
    const taskId1 = (next1 as { task: { id: string } }).task.id;

    await server.markTaskDone(requestId, taskId1, "done details");
    const approve1 = await server.approveTaskCompletion(requestId, taskId1);
    expect(approve1.status).toBe("task_approved");

    // Second task
    const next2 = await server.getNextTask(requestId);
    expect(next2.status).toBe("next_task");
    const taskId2 = (next2 as { task: { id: string } }).task.id;
    expect(taskId2).not.toBe(taskId1);

    await server.markTaskDone(requestId, taskId2, "done details 2");
    await server.approveTaskCompletion(requestId, taskId2);

    // All tasks done -> queue is empty
    const next3 = await server.getNextTask(requestId);
    expect(next3.status).toBe("all_tasks_done");
  });

  it("persists state across instances (reload from disk)", async () => {
    const server1 = new TaskManagerServer();
    const planned = await server1.requestPlanning("persisted", [
      { title: "Persist me", description: "x" },
    ]);
    const requestId = planned.requestId;

    // A brand new instance must load the same data from disk.
    const server2 = new TaskManagerServer();
    const next = await server2.getNextTask(requestId);
    expect(next.status).toBe("next_task");
  });
});
