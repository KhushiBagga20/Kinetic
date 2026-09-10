#!/usr/bin/env bash
#
# kinetic — start (or stop) the whole app with one command.
#
# Runs the two processes Kinetic needs: the Python backend (FastAPI on
# :8000) and the web frontend (Vite on :5173). Both run in the background,
# so the command returns your terminal to you; logs live in .kinetic/ next
# to this script. Liveness is checked by port, not by a saved PID, so it
# stays correct even if a process died since the last run.
#
# Usage:
#   kinetic            start both servers (does nothing if already running)
#   kinetic stop       stop both servers
#   kinetic restart    stop, then start
#   kinetic status     show whether each server is up
#   kinetic logs       follow both logs
#
set -euo pipefail

# Resolve the real directory of this script, even when reached through the
# ~/.local/bin symlink the installer sets up.
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
ROOT="$(cd -P "$(dirname "$SOURCE")" && pwd)"

RUN_DIR="$ROOT/.kinetic"
mkdir -p "$RUN_DIR"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"
BACKEND_PORT=8000
FRONTEND_PORT=5173
BACKEND_URL="http://127.0.0.1:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"

lime() { printf '\033[38;5;149m%s\033[0m\n' "$1"; }
dim()  { printf '\033[2m%s\033[0m\n' "$1"; }
err()  { printf '\033[38;5;203m%s\033[0m\n' "$1" >&2; }

# PIDs of whatever is listening on a TCP port, one per line (empty if none).
pids_on_port() { lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true; }
listening()    { [ -n "$(pids_on_port "$1")" ]; }

wait_for() {
  local url="$1" tries="${2:-60}"
  for _ in $(seq 1 "$tries"); do
    curl -fsS -o /dev/null "$url" 2>/dev/null && return 0
    sleep 0.5
  done
  return 1
}

start() {
  if listening "$BACKEND_PORT" && listening "$FRONTEND_PORT"; then
    lime "Kinetic is already running."
    printf '  %s\n' "$FRONTEND_URL"
    return 0
  fi

  if ! listening "$BACKEND_PORT"; then
    dim "Starting backend…"
    (cd "$ROOT/backend" && exec python3 -m uvicorn main:app --host 127.0.0.1 --port "$BACKEND_PORT") \
      >"$BACKEND_LOG" 2>&1 &
    disown
  fi

  if ! listening "$FRONTEND_PORT"; then
    if [ ! -d "$ROOT/frontend/node_modules" ]; then
      dim "Installing frontend dependencies (first run only)…"
      (cd "$ROOT/frontend" && npm install --no-audit --no-fund) >>"$FRONTEND_LOG" 2>&1
    fi
    dim "Starting frontend…"
    (cd "$ROOT/frontend" && exec npm run dev -- --port "$FRONTEND_PORT") >"$FRONTEND_LOG" 2>&1 &
    disown
  fi

  dim "Waiting for both servers to come up…"
  if wait_for "$BACKEND_URL/api/health" && wait_for "$FRONTEND_URL"; then
    lime "Kinetic is up."
    printf '  backend   %s\n' "$BACKEND_URL"
    printf '  frontend  %s\n' "$FRONTEND_URL"
    dim "Logs: $BACKEND_LOG · $FRONTEND_LOG"
    dim "Stop with: kinetic stop"
    if [[ "${1:-}" != "--no-open" ]] && command -v open >/dev/null 2>&1; then
      open "$FRONTEND_URL"
    fi
  else
    err "One of the servers did not come up in time — check the logs:"
    err "  $BACKEND_LOG"
    err "  $FRONTEND_LOG"
    return 1
  fi
}

stop_port() {
  local port="$1" label="$2" pids
  pids="$(pids_on_port "$port")"
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
    sleep 0.3
    pids="$(pids_on_port "$port")"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
    dim "Stopped $label."
  fi
}

stop() {
  stop_port "$BACKEND_PORT" "backend"
  stop_port "$FRONTEND_PORT" "frontend"
  lime "Kinetic is stopped."
}

status() {
  if listening "$BACKEND_PORT"; then lime "backend   running  $BACKEND_URL"; else err "backend   stopped"; fi
  if listening "$FRONTEND_PORT"; then lime "frontend  running  $FRONTEND_URL"; else err "frontend  stopped"; fi
}

logs() {
  tail -f "$BACKEND_LOG" "$FRONTEND_LOG"
}

# Anything that isn't one of these exact words is treated as an option to
# `start` (e.g. `kinetic --no-open`), so `kinetic` alone just starts it.
case "${1:-}" in
  stop)    stop ;;
  restart) shift; stop; start "${1:-}" ;;
  status)  status ;;
  logs)    logs ;;
  start)   shift; start "${1:-}" ;;
  ""|--*)  start "${1:-}" ;;
  *)
    err "Usage: kinetic [start|stop|restart|status|logs]"
    exit 1
    ;;
esac
