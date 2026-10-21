#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
  ToolSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { realpathSync } from "node:fs";
import * as fs from "node:fs/promises";
import * as path from "node:path";
import * as os from "node:os";
import { fileURLToPath } from "node:url";
import { z } from "zod";

const DEFAULT_PATH = path.join(os.homedir(), "Documents", "tasks.json");
const TASK_FILE_PATH = process.env.TASK_MANAGER_FILE_PATH || DEFAULT_PATH;

interface Task {
  id: string;
  title: string;
  description: string;
  done: boolean;
  approved: boolean;
  completedDetails: string;
}

interface RequestEntry {
  requestId: string;
  originalRequest: string;
  splitDetails: string;
  tasks: Task[];
  completed: boolean; // marked true after all tasks done and request completion approved
}

interface TaskManagerFile {
  requests: RequestEntry[];
}

// Zod Schemas
const RequestPlanningSchema = z.object({
  originalRequest: z.string(),
  splitDetails: z.string().optional(),
  tasks: z.array(
    z.object({
      title: z.string(),
      description: z.string(),
    })
  ),
});

const GetNextTaskSchema = z.object({
  requestId: z.string(),
});

const MarkTaskDoneSchema = z.object({
  requestId: z.string(),
  taskId: z.string(),
  completedDetails: z.string().optional(),
});

const ApproveTaskCompletionSchema = z.object({
  requestId: z.string(),
  taskId: z.string(),
});

const ApproveRequestCompletionSchema = z.object({
  requestId: z.string(),
});

const OpenTaskDetailsSchema = z.object({
  taskId: z.string(),
});

const ListRequestsSchema = z.object({});

const AddTasksToRequestSchema = z.object({
  requestId: z.string(),
  tasks: z.array(
    z.object({
      title: z.string(),
      description: z.string(),
    })
  ),
});

const UpdateTaskSchema = z.object({
  requestId: z.string(),
  taskId: z.string(),
  title: z.string().optional(),
  description: z.string().optional(),
});

const DeleteTaskSchema = z.object({
  requestId: z.string(),
  taskId: z.string(),
});

// Tools with enriched English descriptions

const REQUEST_PLANNING_TOOL: Tool = {
  name: "request_planning",
  description:
    "Register a new user request and plan its associated tasks. You must provide 'originalRequest' and 'tasks', and optionally 'splitDetails'.\n\n" +
    "This tool initiates a new workflow for handling a user's request. The workflow is as follows:\n" +
    "1. Use 'request_planning' to register a request and its tasks.\n" +
    "2. After adding tasks, you MUST use 'get_next_task' to retrieve the first task. A progress table will be displayed.\n" +
    "3. Use 'get_next_task' to retrieve the next uncompleted task.\n" +
    "4. **IMPORTANT:** After marking a task as done, the assistant MUST NOT proceed to another task without the user's approval. The user must explicitly approve the completed task using 'approve_task_completion'. A progress table will be displayed before each approval request.\n" +
    "5. Once a task is approved, you can proceed to 'get_next_task' again to fetch the next pending task.\n" +
    "6. Repeat this cycle until all tasks are done.\n" +
    "7. After all tasks are completed (and approved), 'get_next_task' will indicate that all tasks are done and that the request awaits approval for full completion.\n" +
    "8. The user must then approve the entire request's completion using 'approve_request_completion'. If the user does not approve and wants more tasks, you can again use 'request_planning' to add new tasks and continue the cycle.\n\n" +
    "The critical point is to always wait for user approval after completing each task and after all tasks are done, wait for request completion approval. Do not proceed automatically.",
  inputSchema: {
    type: "object",
    properties: {
      originalRequest: { type: "string" },
      splitDetails: { type: "string" },
      tasks: {
        type: "array",
        items: {
          type: "object",
          properties: {
            title: { type: "string" },
            description: { type: "string" },
          },
          required: ["title", "description"],
        },
      },
    },
    required: ["originalRequest", "tasks"],
  },
};

const GET_NEXT_TASK_TOOL: Tool = {
  name: "get_next_task",
  description:
    "Given a 'requestId', return the next pending task (not done yet). If all tasks are completed, it will indicate that no more tasks are left and that you must wait for the request completion approval.\n\n" +
    "A progress table showing the current status of all tasks will be displayed with each response.\n\n" +
    "If the same task is returned again or if no new task is provided after a task was marked as done but not yet approved, you MUST NOT proceed. In such a scenario, you must prompt the user for approval via 'approve_task_completion' before calling 'get_next_task' again. Do not skip the user's approval step.\n" +
    "In other words:\n" +
    "- After calling 'mark_task_done', do not call 'get_next_task' again until 'approve_task_completion' is called by the user.\n" +
    "- If 'get_next_task' returns 'all_tasks_done', it means all tasks have been completed. At this point, you must not start a new request or do anything else until the user decides to 'approve_request_completion' or possibly add more tasks via 'request_planning'.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
    },
    required: ["requestId"],
  },
};

const MARK_TASK_DONE_TOOL: Tool = {
  name: "mark_task_done",
  description:
    "Mark a given task as done after you've completed it. Provide 'requestId' and 'taskId', and optionally 'completedDetails'.\n\n" +
    "After marking a task as done, a progress table will be displayed showing the updated status of all tasks.\n\n" +
    "After this, DO NOT proceed to 'get_next_task' again until the user has explicitly approved this completed task using 'approve_task_completion'.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
      taskId: { type: "string" },
      completedDetails: { type: "string" },
    },
    required: ["requestId", "taskId"],
  },
};

const APPROVE_TASK_COMPLETION_TOOL: Tool = {
  name: "approve_task_completion",
  description:
    "Once the assistant has marked a task as done using 'mark_task_done', the user must call this tool to approve that the task is genuinely completed. Only after this approval can you proceed to 'get_next_task' to move on.\n\n" +
    "A progress table will be displayed before requesting approval, showing the current status of all tasks.\n\n" +
    "If the user does not approve, do not call 'get_next_task'. Instead, the user may request changes, or even re-plan tasks by using 'request_planning' again.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
      taskId: { type: "string" },
    },
    required: ["requestId", "taskId"],
  },
};

const APPROVE_REQUEST_COMPLETION_TOOL: Tool = {
  name: "approve_request_completion",
  description:
    "After all tasks are done and approved, this tool finalizes the entire request. The user must call this to confirm that the request is fully completed.\n\n" +
    "A progress table showing the final status of all tasks will be displayed before requesting final approval.\n\n" +
    "If not approved, the user can add new tasks using 'request_planning' and continue the process.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
    },
    required: ["requestId"],
  },
};

const OPEN_TASK_DETAILS_TOOL: Tool = {
  name: "open_task_details",
  description:
    "Get details of a specific task by 'taskId'. This is for inspecting task information at any point.",
  inputSchema: {
    type: "object",
    properties: {
      taskId: { type: "string" },
    },
    required: ["taskId"],
  },
};

const LIST_REQUESTS_TOOL: Tool = {
  name: "list_requests",
  description:
    "List all requests with their basic information and summary of tasks. This provides a quick overview of all requests in the system.",
  inputSchema: {
    type: "object",
    properties: {},
  },
};

const ADD_TASKS_TO_REQUEST_TOOL: Tool = {
  name: "add_tasks_to_request",
  description:
    "Add new tasks to an existing request. This allows extending a request with additional tasks.\n\n" +
    "A progress table will be displayed showing all tasks including the newly added ones.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
      tasks: {
        type: "array",
        items: {
          type: "object",
          properties: {
            title: { type: "string" },
            description: { type: "string" },
          },
          required: ["title", "description"],
        },
      },
    },
    required: ["requestId", "tasks"],
  },
};

const UPDATE_TASK_TOOL: Tool = {
  name: "update_task",
  description:
    "Update an existing task's title and/or description. Only uncompleted tasks can be updated.\n\n" +
    "A progress table will be displayed showing the updated task information.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
      taskId: { type: "string" },
      title: { type: "string" },
      description: { type: "string" },
    },
    required: ["requestId", "taskId"],
  },
};

const DELETE_TASK_TOOL: Tool = {
  name: "delete_task",
  description:
    "Delete a specific task from a request. Only uncompleted tasks can be deleted.\n\n" +
    "A progress table will be displayed showing the remaining tasks after deletion.",
  inputSchema: {
    type: "object",
    properties: {
      requestId: { type: "string" },
      taskId: { type: "string" },
    },
    required: ["requestId", "taskId"],
  },
};

export class TaskManagerServer {
  private requestCounter = 0;
  private taskCounter = 0;
  private data: TaskManagerFile = { requests: [] };

  constructor() {
    this.loadTasks();
  }

  private async loadTasks() {
    try {
      const data = await fs.readFile(TASK_FILE_PATH, "utf-8");
      this.data = JSON.parse(data);
      const allTaskIds: number[] = [];
      const allRequestIds: number[] = [];

      for (const req of this.data.requests) {
        const reqNum = Number.parseInt(req.requestId.replace("req-", ""), 10);
        if (!Number.isNaN(reqNum)) {
          allRequestIds.push(reqNum);
        }
        for (const t of req.tasks) {
          const tNum = Number.parseInt(t.id.replace("task-", ""), 10);
          if (!Number.isNaN(tNum)) {
            allTaskIds.push(tNum);
          }
        }
      }

      this.requestCounter =
        allRequestIds.length > 0 ? Math.max(...allRequestIds) : 0;
      this.taskCounter = allTaskIds.length > 0 ? Math.max(...allTaskIds) : 0;
    } catch (error) {
      this.data = { requests: [] };
    }
  }

  private async saveTasks() {
    try {
      // Ensure the parent directory exists before writing. Without this,
      // environments where the default dir is absent (Docker /root/Documents,
      // CI runners, fresh OS profiles) fail with ENOENT. See issue #4.
      await fs.mkdir(path.dirname(TASK_FILE_PATH), { recursive: true });
      await fs.writeFile(
        TASK_FILE_PATH,
        JSON.stringify(this.data, null, 2),
        "utf-8"
      );
    } catch (error) {
      if (error instanceof Error && error.message.includes("EROFS")) {
        console.error("EROFS: read-only file system. Cannot save tasks.");
        throw error;
      }
      throw error;
    }
  }

  private formatTaskProgressTable(requestId: string): string {
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return "Request not found";

    let table = "\nProgress Status:\n";
    table += "| Task ID | Title | Description | Status | Approval |\n";
    table += "|----------|----------|------|------|----------|\n";

    for (const task of req.tasks) {
      const status = task.done ? "✅ Done" : "🔄 In Progress";
      const approved = task.approved ? "✅ Approved" : "⏳ Pending";
      table += `| ${task.id} | ${task.title} | ${task.description} | ${status} | ${approved} |\n`;
    }

    return table;
  }

  private formatRequestsList(): string {
    let output = "\nRequests List:\n";
    output +=
      "| Request ID | Original Request | Total Tasks | Completed | Approved |\n";
    output +=
      "|------------|------------------|-------------|-----------|----------|\n";

    for (const req of this.data.requests) {
      const totalTasks = req.tasks.length;
      const completedTasks = req.tasks.filter((t) => t.done).length;
      const approvedTasks = req.tasks.filter((t) => t.approved).length;
      output += `| ${req.requestId} | ${req.originalRequest.substring(0, 30)}${req.originalRequest.length > 30 ? "..." : ""} | ${totalTasks} | ${completedTasks} | ${approvedTasks} |\n`;
    }

    return output;
  }

  public async requestPlanning(
    originalRequest: string,
    tasks: { title: string; description: string }[],
    splitDetails?: string
  ) {
    await this.loadTasks();
    this.requestCounter += 1;
    const requestId = `req-${this.requestCounter}`;

    const newTasks: Task[] = [];
    for (const taskDef of tasks) {
      this.taskCounter += 1;
      newTasks.push({
        id: `task-${this.taskCounter}`,
        title: taskDef.title,
        description: taskDef.description,
        done: false,
        approved: false,
        completedDetails: "",
      });
    }

    this.data.requests.push({
      requestId,
      originalRequest,
      splitDetails: splitDetails || originalRequest,
      tasks: newTasks,
      completed: false,
    });

    await this.saveTasks();

    const progressTable = this.formatTaskProgressTable(requestId);

    return {
      status: "planned",
      requestId,
      totalTasks: newTasks.length,
      tasks: newTasks.map((t) => ({
        id: t.id,
        title: t.title,
        description: t.description,
      })),
      message: `Tasks have been successfully added. Please use 'get_next_task' to retrieve the first task.\n${progressTable}`,
    };
  }

  public async getNextTask(requestId: string) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) {
      return { status: "error", message: "Request not found" };
    }
    if (req.completed) {
      return {
        status: "already_completed",
        message: "Request already completed.",
      };
    }
    const nextTask = req.tasks.find((t) => !t.done);
    if (!nextTask) {
      // all tasks done?
      const allDone = req.tasks.every((t) => t.done);
      if (allDone && !req.completed) {
        const progressTable = this.formatTaskProgressTable(requestId);
        return {
          status: "all_tasks_done",
          message: `All tasks have been completed. Awaiting request completion approval.\n${progressTable}`,
        };
      }
      return { status: "no_next_task", message: "No undone tasks found." };
    }

    const progressTable = this.formatTaskProgressTable(requestId);
    return {
      status: "next_task",
      task: {
        id: nextTask.id,
        title: nextTask.title,
        description: nextTask.description,
      },
      message: `Next task is ready. Task approval will be required after completion.\n${progressTable}`,
    };
  }

  public async markTaskDone(
    requestId: string,
    taskId: string,
    completedDetails?: string
  ) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return { status: "error", message: "Request not found" };
    const task = req.tasks.find((t) => t.id === taskId);
    if (!task) return { status: "error", message: "Task not found" };
    if (task.done)
      return {
        status: "already_done",
        message: "Task is already marked done.",
      };

    task.done = true;
    task.completedDetails = completedDetails || "";
    await this.saveTasks();
    return {
      status: "task_marked_done",
      requestId: req.requestId,
      task: {
        id: task.id,
        title: task.title,
        description: task.description,
        completedDetails: task.completedDetails,
        approved: task.approved,
      },
    };
  }

  public async approveTaskCompletion(requestId: string, taskId: string) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return { status: "error", message: "Request not found" };
    const task = req.tasks.find((t) => t.id === taskId);
    if (!task) return { status: "error", message: "Task not found" };
    if (!task.done) return { status: "error", message: "Task not done yet." };
    if (task.approved)
      return { status: "already_approved", message: "Task already approved." };

    task.approved = true;
    await this.saveTasks();
    return {
      status: "task_approved",
      requestId: req.requestId,
      task: {
        id: task.id,
        title: task.title,
        description: task.description,
        completedDetails: task.completedDetails,
        approved: task.approved,
      },
    };
  }

  public async approveRequestCompletion(requestId: string) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return { status: "error", message: "Request not found" };

    // Check if all tasks are done and approved
    const allDone = req.tasks.every((t) => t.done);
    if (!allDone) {
      return { status: "error", message: "Not all tasks are done." };
    }
    const allApproved = req.tasks.every((t) => t.done && t.approved);
    if (!allApproved) {
      return { status: "error", message: "Not all done tasks are approved." };
    }

    req.completed = true;
    await this.saveTasks();
    return {
      status: "request_approved_complete",
      requestId: req.requestId,
      message: "Request is fully completed and approved.",
    };
  }

  public async openTaskDetails(taskId: string) {
    await this.loadTasks();
    for (const req of this.data.requests) {
      const target = req.tasks.find((t) => t.id === taskId);
      if (target) {
        return {
          status: "task_details",
          requestId: req.requestId,
          originalRequest: req.originalRequest,
          splitDetails: req.splitDetails,
          completed: req.completed,
          task: {
            id: target.id,
            title: target.title,
            description: target.description,
            done: target.done,
            approved: target.approved,
            completedDetails: target.completedDetails,
          },
        };
      }
    }
    return { status: "task_not_found", message: "No such task found" };
  }

  public async listRequests() {
    await this.loadTasks();
    const requestsList = this.formatRequestsList();
    return {
      status: "requests_listed",
      message: `Current requests in the system:\n${requestsList}`,
      requests: this.data.requests.map((req) => ({
        requestId: req.requestId,
        originalRequest: req.originalRequest,
        totalTasks: req.tasks.length,
        completedTasks: req.tasks.filter((t) => t.done).length,
        approvedTasks: req.tasks.filter((t) => t.approved).length,
      })),
    };
  }

  public async addTasksToRequest(
    requestId: string,
    tasks: { title: string; description: string }[]
  ) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return { status: "error", message: "Request not found" };
    if (req.completed)
      return {
        status: "error",
        message: "Cannot add tasks to completed request",
      };

    const newTasks: Task[] = [];
    for (const taskDef of tasks) {
      this.taskCounter += 1;
      newTasks.push({
        id: `task-${this.taskCounter}`,
        title: taskDef.title,
        description: taskDef.description,
        done: false,
        approved: false,
        completedDetails: "",
      });
    }

    req.tasks.push(...newTasks);
    await this.saveTasks();

    const progressTable = this.formatTaskProgressTable(requestId);
    return {
      status: "tasks_added",
      message: `Added ${newTasks.length} new tasks to request.\n${progressTable}`,
      newTasks: newTasks.map((t) => ({
        id: t.id,
        title: t.title,
        description: t.description,
      })),
    };
  }

  public async updateTask(
    requestId: string,
    taskId: string,
    updates: { title?: string; description?: string }
  ) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return { status: "error", message: "Request not found" };

    const task = req.tasks.find((t) => t.id === taskId);
    if (!task) return { status: "error", message: "Task not found" };
    if (task.done)
      return { status: "error", message: "Cannot update completed task" };

    if (updates.title) task.title = updates.title;
    if (updates.description) task.description = updates.description;

    await this.saveTasks();

    const progressTable = this.formatTaskProgressTable(requestId);
    return {
      status: "task_updated",
      message: `Task ${taskId} has been updated.\n${progressTable}`,
      task: {
        id: task.id,
        title: task.title,
        description: task.description,
      },
    };
  }

  public async deleteTask(requestId: string, taskId: string) {
    await this.loadTasks();
    const req = this.data.requests.find((r) => r.requestId === requestId);
    if (!req) return { status: "error", message: "Request not found" };

    const taskIndex = req.tasks.findIndex((t) => t.id === taskId);
    if (taskIndex === -1) return { status: "error", message: "Task not found" };
    if (req.tasks[taskIndex].done)
      return { status: "error", message: "Cannot delete completed task" };

    req.tasks.splice(taskIndex, 1);
    await this.saveTasks();

    const progressTable = this.formatTaskProgressTable(requestId);
    return {
      status: "task_deleted",
      message: `Task ${taskId} has been deleted.\n${progressTable}`,
    };
  }
}

const server = new Server(
  {
    name: "task-manager-server",
    version: "2.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

const taskManagerServer = new TaskManagerServer();

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    REQUEST_PLANNING_TOOL,
    GET_NEXT_TASK_TOOL,
    MARK_TASK_DONE_TOOL,
    APPROVE_TASK_COMPLETION_TOOL,
    APPROVE_REQUEST_COMPLETION_TOOL,
    OPEN_TASK_DETAILS_TOOL,
    LIST_REQUESTS_TOOL,
    ADD_TASKS_TO_REQUEST_TOOL,
    UPDATE_TASK_TOOL,
    DELETE_TASK_TOOL,
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  try {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "request_planning": {
        const parsed = RequestPlanningSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { originalRequest, tasks, splitDetails } = parsed.data;
        const result = await taskManagerServer.requestPlanning(
          originalRequest,
          tasks,
          splitDetails
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "get_next_task": {
        const parsed = GetNextTaskSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const result = await taskManagerServer.getNextTask(
          parsed.data.requestId
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "mark_task_done": {
        const parsed = MarkTaskDoneSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { requestId, taskId, completedDetails } = parsed.data;
        const result = await taskManagerServer.markTaskDone(
          requestId,
          taskId,
          completedDetails
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "approve_task_completion": {
        const parsed = ApproveTaskCompletionSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { requestId, taskId } = parsed.data;
        const result = await taskManagerServer.approveTaskCompletion(
          requestId,
          taskId
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "approve_request_completion": {
        const parsed = ApproveRequestCompletionSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { requestId } = parsed.data;
        const result =
          await taskManagerServer.approveRequestCompletion(requestId);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "open_task_details": {
        const parsed = OpenTaskDetailsSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { taskId } = parsed.data;
        const result = await taskManagerServer.openTaskDetails(taskId);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "list_requests": {
        const parsed = ListRequestsSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const result = await taskManagerServer.listRequests();
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "add_tasks_to_request": {
        const parsed = AddTasksToRequestSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { requestId, tasks } = parsed.data;
        const result = await taskManagerServer.addTasksToRequest(
          requestId,
          tasks
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "update_task": {
        const parsed = UpdateTaskSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { requestId, taskId, title, description } = parsed.data;
        const result = await taskManagerServer.updateTask(requestId, taskId, {
          title,
          description,
        });
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      case "delete_task": {
        const parsed = DeleteTaskSchema.safeParse(args);
        if (!parsed.success) {
          throw new Error(`Invalid arguments: ${parsed.error}`);
        }
        const { requestId, taskId } = parsed.data;
        const result = await taskManagerServer.deleteTask(requestId, taskId);
        return {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${errorMessage}` }],
      isError: true,
    };
  }
});

async function runServer() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `Task Manager MCP Server running. Saving tasks at: ${TASK_FILE_PATH}`
  );
}

// Only start the stdio server when executed directly as a binary, not when
// imported by tests. npm installs bin entries as SYMLINKS (node_modules/.bin,
// npx cache), so argv[1] must be realpath'd before comparing — path.resolve
// alone breaks `npx @kazuph/mcp-taskmanager`.
const isMain = (() => {
  if (!process.argv[1]) return false;
  try {
    return fileURLToPath(import.meta.url) === realpathSync(process.argv[1]);
  } catch {
    return false;
  }
})();

if (isMain) {
  runServer().catch((error) => {
    console.error("Fatal error running server:", error);
    process.exit(1);
  });
}
