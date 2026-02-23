import { mkdir, rmdir } from "node:fs/promises";
import { join } from "node:path";

const LOCK_DIR = "/tmp/agent-factory-locks";

// Ensure lock directory exists
await mkdir(LOCK_DIR, { recursive: true });

export class LockError extends Error {
  constructor(resource: string) {
    super(`Resource '${resource}' is locked by another agent`);
    this.name = "LockError";
  }
}

export async function withLock<T>(
  resource: string,
  fn: () => Promise<T>
): Promise<T> {
  const lockPath = join(LOCK_DIR, `${resource}.lock`);

  try {
    await mkdir(lockPath);
  } catch {
    throw new LockError(resource);
  }

  try {
    return await fn();
  } finally {
    await rmdir(lockPath).catch(() => {});
  }
}
