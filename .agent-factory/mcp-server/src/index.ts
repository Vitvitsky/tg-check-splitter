#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { resolveProjectDir } from "./resolve-project.js";
import { registerPhaseTools } from "./tools/phase.js";
import { registerQueueTools } from "./tools/queue.js";
import { registerAgentTools } from "./tools/agent.js";

async function main() {
  const projectDir = await resolveProjectDir();
  console.error(`Agent Factory MCP Server — project: ${projectDir}`);

  const server = new McpServer({
    name: "agent-factory",
    version: "1.0.0",
  });

  registerPhaseTools(server, projectDir);
  registerQueueTools(server, projectDir);
  registerAgentTools(server, projectDir);

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Agent Factory MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
