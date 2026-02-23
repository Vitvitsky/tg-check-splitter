import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  readPhaseConfig,
  writePhaseConfig,
  findNextActive,
} from "../state/phase-config.js";
import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const PHASE_DIRS = [
  "0-discovery",
  "1-design",
  "2-planning",
  "3-build",
  "4-validate",
  "5-retrospective",
];

export function registerPhaseTools(
  server: McpServer,
  projectDir: string
): void {
  const phasesDir = join(projectDir, ".agent-factory", "phases");

  server.registerTool(
    "phase_status",
    {
      description:
        "Show current phase configuration: which phases are active, artifact counts, and the current phase.",
      inputSchema: {},
    },
    async () => {
      const config = await readPhaseConfig(projectDir);
      const lines: string[] = ["# Phase Status", ""];

      for (const phase of config.phases) {
        const dir = join(phasesDir, PHASE_DIRS[phase.index], "artifacts");
        let artifactCount = 0;
        try {
          const files = await readdir(dir);
          artifactCount = files.filter(
            (f) => f.endsWith(".md") && f !== ".gitkeep"
          ).length;
        } catch {
          // directory may not exist
        }
        const marker = phase.index === config.currentPhase ? ">" : " ";
        const check = phase.active ? "x" : " ";
        lines.push(
          `${marker} [${check}] Phase ${phase.index}: ${phase.name} (${artifactCount} artifacts)`
        );
      }

      lines.push("");
      lines.push(`Current Phase: ${config.currentPhase}`);
      lines.push(`Started: ${config.started}`);

      return {
        content: [{ type: "text" as const, text: lines.join("\n") }],
      };
    }
  );

  server.registerTool(
    "phase_start",
    {
      description: "Activate a phase, set it as current, and record the started date.",
      inputSchema: { phase: z.number().int().min(0).max(5) },
    },
    async ({ phase }) => {
      const config = await readPhaseConfig(projectDir);
      config.phases[phase].active = true;
      config.currentPhase = phase;
      config.started = new Date().toISOString().split("T")[0];
      await writePhaseConfig(projectDir, config);
      return {
        content: [
          {
            type: "text" as const,
            text: `Phase ${phase} (${config.phases[phase].name}) started and set as current.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "phase_complete",
    {
      description:
        "Mark a phase as complete (deactivate it) and auto-advance to the next active phase.",
      inputSchema: { phase: z.number().int().min(0).max(5) },
    },
    async ({ phase }) => {
      const config = await readPhaseConfig(projectDir);
      config.phases[phase].active = false;

      if (config.currentPhase === phase) {
        const next = findNextActive(config, phase);
        if (next !== null) {
          config.currentPhase = next;
        }
      }

      await writePhaseConfig(projectDir, config);
      return {
        content: [
          {
            type: "text" as const,
            text: `Phase ${phase} (${config.phases[phase].name}) completed. Current phase: ${config.currentPhase}.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "phase_skip",
    {
      description:
        "Skip a phase (deactivate it) and advance to next active phase if it was current.",
      inputSchema: { phase: z.number().int().min(0).max(5) },
    },
    async ({ phase }) => {
      const config = await readPhaseConfig(projectDir);
      config.phases[phase].active = false;

      if (config.currentPhase === phase) {
        const next = findNextActive(config, phase);
        if (next !== null) {
          config.currentPhase = next;
        }
      }

      await writePhaseConfig(projectDir, config);
      return {
        content: [
          {
            type: "text" as const,
            text: `Phase ${phase} (${config.phases[phase].name}) skipped. Current phase: ${config.currentPhase}.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "phase_reset",
    {
      description: "Re-activate a phase that was previously completed or skipped.",
      inputSchema: { phase: z.number().int().min(0).max(5) },
    },
    async ({ phase }) => {
      const config = await readPhaseConfig(projectDir);
      config.phases[phase].active = true;
      await writePhaseConfig(projectDir, config);
      return {
        content: [
          {
            type: "text" as const,
            text: `Phase ${phase} (${config.phases[phase].name}) re-activated.`,
          },
        ],
      };
    }
  );

  server.registerTool(
    "phase_agents",
    {
      description:
        "List agent prompt files in a phase's agents/ directory with their titles.",
      inputSchema: { phase: z.number().int().min(0).max(5) },
    },
    async ({ phase }) => {
      const agentsDir = join(phasesDir, PHASE_DIRS[phase], "agents");
      let files: string[];
      try {
        files = await readdir(agentsDir);
      } catch {
        return {
          content: [
            {
              type: "text" as const,
              text: `No agents directory found for phase ${phase}.`,
            },
          ],
        };
      }

      const mdFiles = files.filter((f) => f.endsWith(".md"));
      const lines: string[] = [
        `# Phase ${phase} Agents (${PHASE_DIRS[phase]})`,
        "",
      ];

      for (const f of mdFiles) {
        const content = await readFile(join(agentsDir, f), "utf-8");
        const titleMatch = content.match(/^# (.+)/m);
        const title = titleMatch ? titleMatch[1] : "Untitled";
        lines.push(`- ${f}: ${title}`);
      }

      if (mdFiles.length === 0) {
        lines.push("No agent files found.");
      }

      return {
        content: [{ type: "text" as const, text: lines.join("\n") }],
      };
    }
  );
}
