import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  queueCounts,
  listTasks,
  taskClaim,
  taskSubmit,
  taskReject,
  taskDone,
  taskReturn,
  QueueName,
} from "../state/queue.js";

export function registerQueueTools(
  server: McpServer,
  projectDir: string
): void {
  server.registerTool(
    "queue_status",
    {
      description:
        "Show task counts per queue, in-progress tasks with assignments, and tasks in review.",
      inputSchema: {},
    },
    async () => {
      const counts = await queueCounts(projectDir);
      const lines: string[] = ["# Queue Status", ""];

      for (const [queue, count] of Object.entries(counts)) {
        lines.push(`- ${queue}: ${count}`);
      }

      const inProgress = await listTasks(projectDir, "in-progress");
      if (inProgress.length > 0) {
        lines.push("");
        lines.push("## In Progress");
        for (const task of inProgress) {
          lines.push(`- ${task.filename}: ${task.title} [${task.assigned}]`);
        }
      }

      const review = await listTasks(projectDir, "review");
      if (review.length > 0) {
        lines.push("");
        lines.push("## In Review");
        for (const task of review) {
          lines.push(`- ${task.filename}: ${task.title}`);
        }
      }

      return {
        content: [{ type: "text" as const, text: lines.join("\n") }],
      };
    }
  );

  server.registerTool(
    "queue_list",
    {
      description: "List all tasks in a specific queue.",
      inputSchema: {
        queue: z.enum(["backlog", "todo", "in-progress", "review", "done"]),
      },
    },
    async ({ queue }) => {
      const tasks = await listTasks(projectDir, queue as QueueName);
      const lines: string[] = [`# ${queue} (${tasks.length} tasks)`, ""];

      for (const task of tasks) {
        const parts = [`- ${task.filename}: ${task.title}`];
        if (task.assigned && task.assigned !== "none") {
          parts.push(`[${task.assigned}]`);
        }
        if (task.domain) {
          parts.push(`(${task.domain})`);
        }
        lines.push(parts.join(" "));
      }

      if (tasks.length === 0) {
        lines.push("No tasks in this queue.");
      }

      return {
        content: [{ type: "text" as const, text: lines.join("\n") }],
      };
    }
  );

  server.registerTool(
    "task_claim",
    {
      description:
        "Claim a task from the todo queue and move it to in-progress.",
      inputSchema: {
        filename: z.string(),
        worker_id: z.string().optional(),
      },
    },
    async ({ filename, worker_id }) => {
      await taskClaim(projectDir, filename, worker_id);
      return {
        content: [
          {
            type: "text" as const,
            text: `Task ${filename} claimed and moved to in-progress.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "task_submit",
    {
      description:
        "Submit a task for review by moving it from in-progress to review.",
      inputSchema: { filename: z.string() },
    },
    async ({ filename }) => {
      await taskSubmit(projectDir, filename);
      return {
        content: [
          {
            type: "text" as const,
            text: `Task ${filename} submitted for review.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "task_reject",
    {
      description:
        "Reject a task in review and send it back to todo.",
      inputSchema: {
        filename: z.string(),
        reason: z.string().optional(),
      },
    },
    async ({ filename, reason }) => {
      await taskReject(projectDir, filename);
      const msg = reason
        ? `Task ${filename} rejected: ${reason}`
        : `Task ${filename} rejected and returned to todo.`;
      return {
        content: [{ type: "text" as const, text: msg }],
      };
    }
  );

  server.registerTool(
    "task_done",
    {
      description: "Approve a task in review and mark it as done.",
      inputSchema: { filename: z.string() },
    },
    async ({ filename }) => {
      await taskDone(projectDir, filename);
      return {
        content: [
          {
            type: "text" as const,
            text: `Task ${filename} approved and moved to done.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "task_return",
    {
      description:
        "Return a task from in-progress back to todo (worker gives up).",
      inputSchema: { filename: z.string() },
    },
    async ({ filename }) => {
      await taskReturn(projectDir, filename);
      return {
        content: [
          {
            type: "text" as const,
            text: `Task ${filename} returned to todo.`,
          },
        ],
      };
    }
  );
}
