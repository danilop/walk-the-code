#!/usr/bin/env bash
# Start the walk-the-code example project
# Usage: ./start.sh [port]  (default: 8000)
set -e

PORT="${1:-8000}"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
WTC_DIR="$(cd "$ROOT_DIR/.." && pwd)"

echo "Starting Monte Carlo Pi example at http://localhost:$PORT"

# Open browser after a short delay (background)
(sleep 1 && python3 -m webbrowser "http://localhost:$PORT") &

# Start server (foreground — Ctrl+C to stop)
exec python3 "$WTC_DIR/server.py" --config "$ROOT_DIR/config.json" "$PORT"
