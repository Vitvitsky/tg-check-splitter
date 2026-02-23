#!/bin/bash
# Queue management script for Agent Factory
# Provides atomic file operations to prevent race conditions

set -euo pipefail

QUEUE_DIR="$(cd "$(dirname "$0")/.." && pwd)/queue"
LOCK_DIR="/tmp/agent-factory-locks"
mkdir -p "$LOCK_DIR"

usage() {
    cat <<EOF
Usage: $0 <command> <task-file>

Commands:
  claim   <file>  — Move task from todo/ to in-progress/ (worker claims task)
  submit  <file>  — Move task from in-progress/ to review/ (worker submits for review)
  reject  <file>  — Move task from review/ to todo/ (judge rejects)
  done    <file>  — Move task from review/ to done/ (judge approves)
  return  <file>  — Move task from in-progress/ back to todo/ (worker returns)
  status          — Show queue status overview
  list    <queue> — List tasks in a specific queue (backlog|todo|in-progress|review|done)
EOF
    exit 1
}

# Atomic move with lock file to prevent race conditions
atomic_move() {
    local src="$1"
    local dst="$2"
    local filename
    filename="$(basename "$src")"
    local lockfile="$LOCK_DIR/$filename.lock"

    # Use mkdir as atomic lock (fails if already exists)
    if ! mkdir "$lockfile" 2>/dev/null; then
        echo "ERROR: Task '$filename' is locked by another agent. Try a different task."
        exit 1
    fi

    # Cleanup lock on exit
    trap "rmdir '$lockfile' 2>/dev/null || true" EXIT

    if [ ! -f "$src" ]; then
        echo "ERROR: Source file not found: $src"
        echo "Task may have been claimed by another agent."
        rmdir "$lockfile" 2>/dev/null || true
        exit 1
    fi

    mv "$src" "$dst"
    echo "OK: Moved $(basename "$src") -> $(basename "$(dirname "$dst")")/"

    rmdir "$lockfile" 2>/dev/null || true
    trap - EXIT
}

# Update the Assigned field in a task file
update_assigned() {
    local file="$1"
    local value="$2"
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^## Assigned:.*/## Assigned: $value/" "$file"
    else
        sed -i "s/^## Assigned:.*/## Assigned: $value/" "$file"
    fi
}

# Update the Status field in a task file
update_status() {
    local file="$1"
    local value="$2"
    if [ "$(uname)" = "Darwin" ]; then
        sed -i '' "s/^## Status:.*/## Status: $value/" "$file"
    else
        sed -i "s/^## Status:.*/## Status: $value/" "$file"
    fi
}

cmd_claim() {
    local filename="$1"
    local src="$QUEUE_DIR/todo/$filename"
    local dst="$QUEUE_DIR/in-progress/$filename"
    local worker_id="${WORKER_ID:-worker-$$}"

    atomic_move "$src" "$dst"
    update_assigned "$dst" "$worker_id"
    update_status "$dst" "in-progress"
    echo "Claimed by: $worker_id"
}

cmd_submit() {
    local filename="$1"
    local src="$QUEUE_DIR/in-progress/$filename"
    local dst="$QUEUE_DIR/review/$filename"

    atomic_move "$src" "$dst"
    update_status "$dst" "review"
}

cmd_reject() {
    local filename="$1"
    local src="$QUEUE_DIR/review/$filename"
    local dst="$QUEUE_DIR/todo/$filename"

    atomic_move "$src" "$dst"
    update_assigned "$dst" "none"
    update_status "$dst" "todo (rejected)"
}

cmd_done() {
    local filename="$1"
    local src="$QUEUE_DIR/review/$filename"
    local dst="$QUEUE_DIR/done/$filename"

    atomic_move "$src" "$dst"
    update_status "$dst" "done"
}

cmd_return() {
    local filename="$1"
    local src="$QUEUE_DIR/in-progress/$filename"
    local dst="$QUEUE_DIR/todo/$filename"

    atomic_move "$src" "$dst"
    update_assigned "$dst" "none"
    update_status "$dst" "todo (returned)"
}

cmd_status() {
    echo "=== Agent Factory Queue Status ==="
    echo ""
    for dir in backlog todo in-progress review done; do
        count=$(find "$QUEUE_DIR/$dir" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
        echo "  $dir: $count tasks"
    done
    echo ""
    echo "--- In Progress ---"
    for f in "$QUEUE_DIR/in-progress"/*.md; do
        [ -f "$f" ] || continue
        task_name=$(head -1 "$f" | sed 's/^# //')
        assigned=$(grep "^## Assigned:" "$f" | sed 's/^## Assigned: //')
        echo "  $(basename "$f"): $task_name [${assigned}]"
    done
    echo ""
    echo "--- Ready for Review ---"
    for f in "$QUEUE_DIR/review"/*.md; do
        [ -f "$f" ] || continue
        task_name=$(head -1 "$f" | sed 's/^# //')
        echo "  $(basename "$f"): $task_name"
    done
}

cmd_list() {
    local queue="$1"
    if [ ! -d "$QUEUE_DIR/$queue" ]; then
        echo "ERROR: Unknown queue '$queue'. Use: backlog|todo|in-progress|review|done"
        exit 1
    fi
    echo "=== $queue ==="
    for f in "$QUEUE_DIR/$queue"/*.md; do
        [ -f "$f" ] || { echo "  (empty)"; continue; }
        task_name=$(head -1 "$f" | sed 's/^# //')
        echo "  $(basename "$f"): $task_name"
    done
}

# Main
[ $# -lt 1 ] && usage

case "$1" in
    claim)   [ $# -lt 2 ] && usage; cmd_claim "$2" ;;
    submit)  [ $# -lt 2 ] && usage; cmd_submit "$2" ;;
    reject)  [ $# -lt 2 ] && usage; cmd_reject "$2" ;;
    done)    [ $# -lt 2 ] && usage; cmd_done "$2" ;;
    return)  [ $# -lt 2 ] && usage; cmd_return "$2" ;;
    status)  cmd_status ;;
    list)    [ $# -lt 2 ] && usage; cmd_list "$2" ;;
    *)       usage ;;
esac
