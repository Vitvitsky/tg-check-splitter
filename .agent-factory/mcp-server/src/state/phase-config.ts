import { readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

export interface PhaseState {
  index: number;
  name: string;
  active: boolean;
}

export interface PhaseConfig {
  phases: PhaseState[];
  currentPhase: number;
  started: string;
}

const PHASE_NAMES = [
  "Discovery",
  "Design",
  "Planning",
  "Build",
  "Validate",
  "Retrospective",
];

export function configPath(projectDir: string): string {
  return join(projectDir, ".agent-factory", "phases", "phase.config.md");
}

export async function readPhaseConfig(
  projectDir: string
): Promise<PhaseConfig> {
  const content = await readFile(configPath(projectDir), "utf-8");
  const phases: PhaseState[] = [];

  for (let i = 0; i < 6; i++) {
    const re = new RegExp(`- \\[([ x])\\] Phase ${i}: (\\w+)`);
    const match = content.match(re);
    phases.push({
      index: i,
      name: match ? match[2] : PHASE_NAMES[i],
      active: match ? match[1] === "x" : false,
    });
  }

  const currentMatch = content.match(/## Current Phase: (\d+)/);
  const startedMatch = content.match(/## Started: (.+)/);

  return {
    phases,
    currentPhase: currentMatch ? parseInt(currentMatch[1], 10) : 0,
    started: startedMatch ? startedMatch[1].trim() : "",
  };
}

export async function writePhaseConfig(
  projectDir: string,
  config: PhaseConfig
): Promise<void> {
  const lines = ["# Phase Configuration", "", "## Active Phases"];

  for (const phase of config.phases) {
    const check = phase.active ? "x" : " ";
    lines.push(`- [${check}] Phase ${phase.index}: ${phase.name}`);
  }

  lines.push("");
  lines.push(`## Current Phase: ${config.currentPhase}`);
  lines.push(`## Started: ${config.started}`);
  lines.push("");

  await writeFile(configPath(projectDir), lines.join("\n"));
}

export function findNextActive(
  config: PhaseConfig,
  afterPhase: number
): number | null {
  for (let i = afterPhase + 1; i < 6; i++) {
    if (config.phases[i].active) return i;
  }
  return null;
}
