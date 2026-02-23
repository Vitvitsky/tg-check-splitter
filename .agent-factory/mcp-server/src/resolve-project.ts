import { access } from "node:fs/promises";
import { join, dirname, resolve } from "node:path";

export async function resolveProjectDir(): Promise<string> {
  const idx = process.argv.indexOf("--project-dir");
  if (idx !== -1 && process.argv[idx + 1]) {
    return resolve(process.argv[idx + 1]);
  }

  let dir = process.cwd();
  while (true) {
    try {
      await access(join(dir, ".agent-factory"));
      return dir;
    } catch {
      const parent = dirname(dir);
      if (parent === dir) {
        throw new Error(
          "Could not find .agent-factory/ directory. Use --project-dir or run from project root."
        );
      }
      dir = parent;
    }
  }
}
