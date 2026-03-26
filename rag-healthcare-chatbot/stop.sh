#!/usr/bin/env bash
# =============================================================================
# stop.sh — Stops all services started by start.sh
# =============================================================================

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info() { echo -e "${GREEN}[stop.sh]${NC} $*"; }
warn() { echo -e "${YELLOW}[stop.sh]${NC} $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

stop_pid_file() {
  local label="$1" pidfile="$2"
  if [ -f "$pidfile" ]; then
    local pid; pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && info "Stopped $label (PID $pid)"
    else
      warn "$label (PID $pid) was not running"
    fi
    rm -f "$pidfile"
  else
    warn "No PID file for $label — may not have been started by start.sh"
  fi
}

stop_pid_file "React frontend" "$LOG_DIR/frontend.pid"
stop_pid_file "FastAPI backend" "$LOG_DIR/backend.pid"
stop_pid_file "ChromaDB"        "$LOG_DIR/chroma.pid"
stop_pid_file "Ollama"          "$LOG_DIR/ollama.pid"

echo ""
info "All managed services stopped."
echo "Note: if Ollama is a brew service, stop it with: brew services stop ollama"
