#!/bin/bash
# Phase management script for Agent Factory
# Manages phase transitions in the modular pipeline

set -euo pipefail

PHASES_DIR="$(cd "$(dirname "$0")/.." && pwd)/phases"
CONFIG="$PHASES_DIR/phase.config.md"

# Phase names indexed by number
PHASE_NAMES=(Discovery Design Planning Build Validate Retrospective)
PHASE_DIRS=(0-discovery 1-design 2-planning 3-build 4-validate 5-retrospective)

usage() {
    cat <<EOF
Usage: $0 <command> [args]

Commands:
  status          — Show current phase, progress, and agents
  start    <N>    — Start phase N (0-5), set as current
  complete <N>    — Complete phase N, auto-advance to next active
  skip     <N>    — Skip (deactivate) phase N
  reset    <N>    — Re-activate phase N
  agents   <N>    — List agents assigned to phase N
EOF
    exit 1
}

# Validate phase number is 0-5
validate_phase() {
    local n="$1"
    if ! [[ "$n" =~ ^[0-5]$ ]]; then
        echo "ERROR: Phase must be 0-5, got '$n'"
        exit 1
    fi
}

# Check if a phase is active (checked) in config
is_phase_active() {
    local n="$1"
    grep -q "^\- \[x\] Phase $n:" "$CONFIG"
}

# Get current phase number from config
get_current_phase() {
    grep "^## Current Phase:" "$CONFIG" | sed 's/^## Current Phase: //'
}

# Set current phase number in config
set_current_phase() {
    local n="$1"
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^## Current Phase:.*/## Current Phase: $n/" "$CONFIG"
    else
        sed -i "s/^## Current Phase:.*/## Current Phase: $n/" "$CONFIG"
    fi
}

# Set the started date in config
set_started_date() {
    local date_str="$1"
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^## Started:.*/## Started: $date_str/" "$CONFIG"
    else
        sed -i "s/^## Started:.*/## Started: $date_str/" "$CONFIG"
    fi
}

# Activate a phase (check it)
activate_phase() {
    local n="$1"
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^\- \[ \] Phase $n:/- [x] Phase $n:/" "$CONFIG"
    else
        sed -i "s/^\- \[ \] Phase $n:/- [x] Phase $n:/" "$CONFIG"
    fi
}

# Deactivate a phase (uncheck it)
deactivate_phase() {
    local n="$1"
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^\- \[x\] Phase $n:/- [ ] Phase $n:/" "$CONFIG"
    else
        sed -i "s/^\- \[x\] Phase $n:/- [ ] Phase $n:/" "$CONFIG"
    fi
}

# Count artifacts in a phase directory
count_artifacts() {
    local n="$1"
    local phase_dir="$PHASES_DIR/${PHASE_DIRS[$n]}"
    local count=0
    if [ -d "$phase_dir/artifacts" ]; then
        count=$(find "$phase_dir/artifacts" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    fi
    echo "$count"
}

# Find next active phase after N
find_next_active() {
    local after="$1"
    local i
    for i in $(seq $((after + 1)) 5); do
        if is_phase_active "$i"; then
            echo "$i"
            return 0
        fi
    done
    return 1
}

# List agents for a phase
list_agents() {
    local n="$1"
    local agents_dir="$PHASES_DIR/${PHASE_DIRS[$n]}/agents"
    if [ ! -d "$agents_dir" ]; then
        echo "  (no agents directory)"
        return
    fi
    local found=0
    for f in "$agents_dir"/*.md; do
        [ -f "$f" ] || continue
        local title
        title=$(head -1 "$f" | sed 's/^# //')
        echo "  $(basename "$f"): $title"
        found=1
    done
    if [ "$found" -eq 0 ]; then
        echo "  (no agents)"
    fi
}

cmd_status() {
    local current
    current=$(get_current_phase)
    echo "=== Agent Factory Phase Status ==="
    echo ""
    local n
    for n in 0 1 2 3 4 5; do
        local marker=" "
        if [ "$n" = "$current" ]; then
            marker=">"
        fi
        local state="active"
        if ! is_phase_active "$n"; then
            state="skipped"
        fi
        local artifacts
        artifacts=$(count_artifacts "$n")
        printf "%s Phase %d: %-15s [%s]  artifacts: %s\n" "$marker" "$n" "${PHASE_NAMES[$n]}" "$state" "$artifacts"
    done
    echo ""
    echo "Current phase: $current (${PHASE_NAMES[$current]})"
    echo ""
    echo "--- Agents in current phase ---"
    list_agents "$current"
}

cmd_start() {
    local n="$1"
    validate_phase "$n"

    activate_phase "$n"
    set_current_phase "$n"
    set_started_date "$(date +%Y-%m-%d)"

    echo "OK: Started Phase $n (${PHASE_NAMES[$n]})"
}

cmd_complete() {
    local n="$1"
    validate_phase "$n"

    local current
    current=$(get_current_phase)

    if [ "$n" != "$current" ]; then
        echo "WARNING: Completing Phase $n but current phase is $current"
    fi

    deactivate_phase "$n"

    local next
    if next=$(find_next_active "$n"); then
        set_current_phase "$next"
        set_started_date "$(date +%Y-%m-%d)"
        echo "OK: Completed Phase $n (${PHASE_NAMES[$n]})"
        echo "Advanced to Phase $next (${PHASE_NAMES[$next]})"
    else
        echo "OK: Completed Phase $n (${PHASE_NAMES[$n]})"
        echo "All phases completed!"
    fi
}

cmd_skip() {
    local n="$1"
    validate_phase "$n"

    deactivate_phase "$n"
    echo "OK: Skipped Phase $n (${PHASE_NAMES[$n]})"

    local current
    current=$(get_current_phase)

    if [ "$n" = "$current" ]; then
        local next
        if next=$(find_next_active "$n"); then
            set_current_phase "$next"
            set_started_date "$(date +%Y-%m-%d)"
            echo "Advanced to Phase $next (${PHASE_NAMES[$next]})"
        else
            echo "WARNING: No more active phases remain"
        fi
    fi
}

cmd_reset() {
    local n="$1"
    validate_phase "$n"

    activate_phase "$n"
    echo "OK: Reset Phase $n (${PHASE_NAMES[$n]}) — now active"
}

cmd_agents() {
    local n="$1"
    validate_phase "$n"

    echo "=== Agents in Phase $n (${PHASE_NAMES[$n]}) ==="
    list_agents "$n"
}

# Main
[ $# -lt 1 ] && usage

case "$1" in
    status)   cmd_status ;;
    start)    [ $# -lt 2 ] && usage; cmd_start "$2" ;;
    complete) [ $# -lt 2 ] && usage; cmd_complete "$2" ;;
    skip)     [ $# -lt 2 ] && usage; cmd_skip "$2" ;;
    reset)    [ $# -lt 2 ] && usage; cmd_reset "$2" ;;
    agents)   [ $# -lt 2 ] && usage; cmd_agents "$2" ;;
    *)        usage ;;
esac
