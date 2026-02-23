#!/bin/bash
# Launch an Agent Factory agent with the proper system prompt
#
# Usage:
#   ./launch.sh business-analyst         # Phase 0
#   ./launch.sh product-manager          # Phase 0
#   ./launch.sh architect                # Phase 1
#   ./launch.sh primary-planner          # Phase 2
#   ./launch.sh sub-planner              # Phase 2
#   WORKER_ID=worker-1 ./launch.sh worker  # Phase 3
#   ./launch.sh judge                    # Phase 3
#   ./launch.sh qa-engineer              # Phase 4
#   ./launch.sh retrospective-analyst    # Phase 5

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FACTORY_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$FACTORY_DIR")"
PHASES_DIR="$FACTORY_DIR/phases"

AGENT_TYPE="${1:-}"

# Map agent types to phase directories
get_phase_dir() {
    case "$1" in
        business-analyst)      echo "0-discovery" ;;
        product-manager)       echo "0-discovery" ;;
        architect)             echo "1-design" ;;
        primary-planner)       echo "2-planning" ;;
        sub-planner)           echo "2-planning" ;;
        worker)                echo "3-build" ;;
        judge)                 echo "3-build" ;;
        qa-engineer)           echo "4-validate" ;;
        retrospective-analyst) echo "5-retrospective" ;;
        *)                     echo "" ;;
    esac
}

if [ -z "$AGENT_TYPE" ]; then
    cat <<EOF
Usage: $0 <agent-type>

Phase 0 — Discovery:
  business-analyst     — Analyzes idea, creates BRD
  product-manager      — Creates PRD from BRD

Phase 1 — Design:
  architect            — Creates ADRs, system design, GOAL.md

Phase 2 — Planning:
  primary-planner      — Breaks project into domains
  sub-planner          — Breaks domains into tasks

Phase 3 — Build:
  worker               — Writes code and tests
  judge                — Reviews and commits code

Phase 4 — Validate:
  qa-engineer          — Validates against PRD

Phase 5 — Retrospective:
  retrospective-analyst — Analyzes project, extracts lessons

Environment variables:
  WORKER_ID=worker-N   — Set worker identity (for parallel workers)
EOF
    exit 1
fi

# Find prompt file
PHASE_DIR=$(get_phase_dir "$AGENT_TYPE")

if [ -z "$PHASE_DIR" ]; then
    echo "ERROR: Unknown agent type: $AGENT_TYPE"
    exit 1
fi

PROMPT_FILE="$PHASES_DIR/$PHASE_DIR/agents/$AGENT_TYPE.md"

if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: Agent prompt not found: $PROMPT_FILE"
    exit 1
fi

echo "=== Agent Factory ==="
echo "Launching: $AGENT_TYPE (Phase: $PHASE_DIR)"
echo "Project: $PROJECT_DIR"
echo "====================="
echo ""

cd "$PROJECT_DIR"

cat <<EOF

To start this agent, open a NEW terminal and run:

  cd $PROJECT_DIR
  claude

Then paste this as your first message:

---
I am the **${AGENT_TYPE}** agent. Here are my instructions:

$(cat "$PROMPT_FILE")

I will now begin my work. Let me start by reading the phase config and GOAL.md.
---

For parallel workers, set a unique ID:
  export WORKER_ID=worker-1

TIP: Check phase status: bash .agent-factory/scripts/phase.sh status
EOF
