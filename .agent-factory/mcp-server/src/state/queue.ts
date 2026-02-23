import { readdir, readFile, rename, stat } from "node:fs/promises";
import { join } from "node:path";
import { withLock } from "./lock.js";

export interface TaskInfo {
  filename: string;
  title: string;
  status: string;
  assigned: string;
  domain: string;
  complexity: string;
}

export type QueueName =
  | "backlog"
  | "todo"
  | "in-progress"
  | "review"
  | "done";

const QUEUES: QueueName[] = [
  "backlog",
  "todo",
  "in-progress",
  "review",
  "done",
];

function queueDir(projectDir: string): string {
  return join(projectDir, ".agent-factory", "queue");
}

export async function parseTask(filePath: string): Promise<TaskInfo> {
  const content = await readFile(filePath, "utf-8");
  const titleMatch = content.match(/^# (.+)/m);
  const statusMatch = content.match(/^## Status:\s*(.+)/m);
  const assignedMatch = content.match(/^## Assigned:\s*(.+)/m);
  const domainMatch = content.match(/^## Parent Domain\s*\n(.+)/m);
  const complexityMatch = content.match(/^## Estimated Complexity\s*\n(.+)/m);

  return {
    filename: "",
    title: titleMatch ? titleMatch[1].replace(/^Task:\s*/, "") : "Unknown",
    status: statusMatch ? statusMatch[1].trim() : "unknown",
    assigned: assignedMatch ? assignedMatch[1].trim() : "none",
    domain: domainMatch ? domainMatch[1].trim() : "",
    complexity: complexityMatch ? complexityMatch[1].trim() : "",
  };
}

export async function listTasks(
  projectDir: string,
  queue: QueueName
): Promise<TaskInfo[]> {
  const dir = join(queueDir(projectDir), queue);
  let files: string[];
  try {
    files = await readdir(dir);
  } catch {
    return [];
  }
  const mdFiles = files.filter((f) => f.endsWith(".md"));
  const tasks: TaskInfo[] = [];
  for (const f of mdFiles) {
    const task = await parseTask(join(dir, f));
    task.filename = f;
    tasks.push(task);
  }
  return tasks;
}

export async function queueCounts(
  projectDir: string
): Promise<Record<QueueName, number>> {
  const counts = {} as Record<QueueName, number>;
  for (const q of QUEUES) {
    const tasks = await listTasks(projectDir, q);
    counts[q] = tasks.length;
  }
  return counts;
}

function updateField(content: string, field: string, value: string): string {
  const re = new RegExp(`^## ${field}:.*$`, "m");
  if (re.test(content)) {
    return content.replace(re, `## ${field}: ${value}`);
  }
  return content;
}

async function atomicMove(
  projectDir: string,
  filename: string,
  from: QueueName,
  to: QueueName,
  updates?: Record<string, string>
): Promise<void> {
  const src = join(queueDir(projectDir), from, filename);
  const dst = join(queueDir(projectDir), to, filename);

  await withLock(filename, async () => {
    await stat(src);

    if (updates) {
      let content = await readFile(src, "utf-8");
      for (const [field, value] of Object.entries(updates)) {
        content = updateField(content, field, value);
      }
      const { writeFile: wf } = await import("node:fs/promises");
      await wf(src, content);
    }

    await rename(src, dst);
  });
}

export async function taskClaim(
  projectDir: string,
  filename: string,
  workerId?: string
): Promise<void> {
  const wid = workerId || `worker-${process.pid}`;
  await atomicMove(projectDir, filename, "todo", "in-progress", {
    Status: "in-progress",
    Assigned: wid,
  });
}

export async function taskSubmit(
  projectDir: string,
  filename: string
): Promise<void> {
  await atomicMove(projectDir, filename, "in-progress", "review", {
    Status: "review",
  });
}

export async function taskReject(
  projectDir: string,
  filename: string
): Promise<void> {
  await atomicMove(projectDir, filename, "review", "todo", {
    Status: "todo (rejected)",
    Assigned: "none",
  });
}

export async function taskDone(
  projectDir: string,
  filename: string
): Promise<void> {
  await atomicMove(projectDir, filename, "review", "done", {
    Status: "done",
  });
}

export async function taskReturn(
  projectDir: string,
  filename: string
): Promise<void> {
  await atomicMove(projectDir, filename, "in-progress", "todo", {
    Status: "todo (returned)",
    Assigned: "none",
  });
}
