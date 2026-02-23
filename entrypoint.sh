#!/bin/sh
set -e

# Run Alembic migrations
uv run alembic upgrade head

# Start bot and API server in parallel
uv run python -m bot &
uv run uvicorn api.app:create_app --factory --host 0.0.0.0 --port 8005 &

# Wait for any process to exit — if one crashes, container stops
wait -n
