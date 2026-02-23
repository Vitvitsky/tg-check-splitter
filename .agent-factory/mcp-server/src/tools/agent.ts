import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { readdir, readFile, copyFile } from "node:fs/promises";
import { join } from "node:path";

const PHASE_DIRS = [
  "0-discovery",
  "1-design",
  "2-planning",
  "3-build",
  "4-validate",
  "5-retrospective",
];

const AGENT_PHASE_MAP: Record<string, number> = {
  "business-analyst": 0,
  "product-manager": 0,
  architect: 1,
  "primary-planner": 2,
  "sub-planner": 2,
  worker: 3,
  judge: 3,
  "qa-engineer": 4,
  "retrospective-analyst": 5,
};

export function registerAgentTools(
  server: McpServer,
  projectDir: string
): void {
  const phasesDir = join(projectDir, ".agent-factory", "phases");

  server.registerTool(
    "agent_list",
    {
      description:
        "List agents across all phases or for a specific phase, showing each agent's title.",
      inputSchema: {
        phase: z.number().int().min(0).max(5).optional(),
      },
    },
    async ({ phase }) => {
      const indices =
        phase !== undefined ? [phase] : [0, 1, 2, 3, 4, 5];
      const lines: string[] = ["# Agents", ""];

      for (const idx of indices) {
        const agentsDir = join(phasesDir, PHASE_DIRS[idx], "agents");
        let files: string[];
        try {
          files = await readdir(agentsDir);
        } catch {
          continue;
        }
        const mdFiles = files.filter((f) => f.endsWith(".md"));
        if (mdFiles.length === 0) continue;

        lines.push(`## Phase ${idx}: ${PHASE_DIRS[idx]}`);
        for (const f of mdFiles) {
          const content = await readFile(join(agentsDir, f), "utf-8");
          const titleMatch = content.match(/^# (.+)/m);
          const title = titleMatch ? titleMatch[1] : "Untitled";
          lines.push(`- ${f.replace(".md", "")}: ${title}`);
        }
        lines.push("");
      }

      return {
        content: [{ type: "text" as const, text: lines.join("\n") }],
      };
    }
  );

  server.registerTool(
    "agent_get_prompt",
    {
      description:
        "Get the full prompt file for a given agent type (e.g. 'worker', 'architect').",
      inputSchema: { agent_type: z.string() },
    },
    async ({ agent_type }) => {
      const phaseIdx = AGENT_PHASE_MAP[agent_type];
      if (phaseIdx === undefined) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Unknown agent type: ${agent_type}. Known types: ${Object.keys(AGENT_PHASE_MAP).join(", ")}`,
            },
          ],
        };
      }

      const filePath = join(
        phasesDir,
        PHASE_DIRS[phaseIdx],
        "agents",
        `${agent_type}.md`
      );

      try {
        const content = await readFile(filePath, "utf-8");
        return {
          content: [{ type: "text" as const, text: content }],
        };
      } catch {
        return {
          content: [
            {
              type: "text" as const,
              text: `Agent prompt file not found: ${filePath}`,
            },
          ],
        };
      }
    }
  );

  server.registerTool(
    "get_goal",
    {
      description: "Read and return the project GOAL.md file.",
      inputSchema: {},
    },
    async () => {
      const goalPath = join(projectDir, ".agent-factory", "GOAL.md");
      try {
        const content = await readFile(goalPath, "utf-8");
        return {
          content: [{ type: "text" as const, text: content }],
        };
      } catch {
        return {
          content: [
            {
              type: "text" as const,
              text: "GOAL.md not found.",
            },
          ],
        };
      }
    }
  );

  server.registerTool(
    "create_artifact",
    {
      description:
        "Copy a template from a phase's templates/ directory to its artifacts/ directory with a new name.",
      inputSchema: {
        phase: z.number().int().min(0).max(5),
        template: z.string(),
        name: z.string(),
      },
    },
    async ({ phase, template, name }) => {
      const phaseDir = join(phasesDir, PHASE_DIRS[phase]);
      const src = join(phaseDir, "templates", template);
      const dst = join(phaseDir, "artifacts", name);

      try {
        await copyFile(src, dst);
        return {
          content: [
            {
              type: "text" as const,
              text: `Artifact created: ${PHASE_DIRS[phase]}/artifacts/${name} (from template ${template})`,
            },
          ],
        };
      } catch (err) {
        return {
          content: [
            {
              type: "text" as const,
              text: `Failed to create artifact: ${err instanceof Error ? err.message : String(err)}`,
            },
          ],
        };
      }
    }
  );
}
