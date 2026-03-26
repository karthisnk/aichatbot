#!/usr/bin/env bash
# =============================================================================
# start.sh — Starts the full RAG Healthcare Chatbot stack
#
# Services started:
#   1. ChromaDB       — http://localhost:8001
#   2. Ollama         — http://localhost:11434  (via brew service or ollama serve)
#   3. FastAPI        — http://localhost:8000
#   4. React frontend — http://localhost:3000   (skipped with --backend-only)
#
# Usage:
#   bash start.sh                # start everything
#   bash start.sh --backend-only # skip the React dev server
#
# See docs/03-local-dev-setup.md for full setup instructions.
# =============================================================================

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[start.sh]${NC} $*"; }
warn()    { echo -e "${YELLOW}[start.sh]${NC} $*"; }
error()   { echo -e "${RED}[start.sh] ERROR:${NC} $*"; exit 1; }

# ── Argument parsing ──────────────────────────────────────────────────────────
BACKEND_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--backend-only" ]] && BACKEND_ONLY=true
done

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend/chatbot-ui"
LOG_DIR="$SCRIPT_DIR/logs"

# Locate the Python virtualenv (sibling of this repo or inside it)
if   [ -d "$SCRIPT_DIR/../.venv" ]; then
  VENV_DIR="$(cd "$SCRIPT_DIR/../.venv" && pwd)"
elif [ -d "$SCRIPT_DIR/.venv" ];    then
  VENV_DIR="$SCRIPT_DIR/.venv"
else
  error "No .venv found.  Run:
  python3 -m venv \"$SCRIPT_DIR/../.venv\"
  source \"$SCRIPT_DIR/../.venv/bin/activate\"
  pip install -r \"$BACKEND_DIR/requirements.txt\""
fi

PYTHON="$VENV_DIR/bin/python"
CHROMA="$VENV_DIR/bin/chroma"
PIP="$VENV_DIR/bin/pip"

# ChromaDB persistent storage — change to ~/chroma-data to survive reboots
CHROMA_DATA_DIR="${CHROMA_DATA_DIR:-/tmp/chroma-data}"
CHROMA_PORT=8001
BACKEND_PORT=8000
OLLAMA_PORT=11434
FRONTEND_PORT=3000

mkdir -p "$LOG_DIR" "$CHROMA_DATA_DIR"

# ── Helper: is a port already listening? ─────────────────────────────────────
port_in_use() { lsof -ti :"$1" >/dev/null 2>&1; }

# ── Helper: wait for an HTTP endpoint to respond ─────────────────────────────
wait_for() {
  local url="$1" label="$2" timeout="${3:-30}" elapsed=0
  until "$PYTHON" -c "import urllib.request; urllib.request.urlopen('$url')" >/dev/null 2>&1; do
    sleep 1; elapsed=$((elapsed + 1))
    [[ $elapsed -ge $timeout ]] && error "$label did not start within ${timeout}s. Check $LOG_DIR/"
  done
  info "$label is up → $url"
}

# =============================================================================
# 1. CHROMA DB
# =============================================================================
if port_in_use $CHROMA_PORT; then
  warn "ChromaDB already running on port $CHROMA_PORT — skipping."
else
  info "Starting ChromaDB on port $CHROMA_PORT (data: $CHROMA_DATA_DIR) …"
  "$CHROMA" run \
    --path "$CHROMA_DATA_DIR" \
    --port "$CHROMA_PORT" \
    > "$LOG_DIR/chroma.log" 2>&1 &
  CHROMA_PID=$!
  echo "$CHROMA_PID" > "$LOG_DIR/chroma.pid"
  wait_for "http://localhost:$CHROMA_PORT/api/v2/heartbeat" "ChromaDB"
fi

# ── Check / ingest collections ───────────────────────────────────────────────
COLLECTIONS=$("$PYTHON" -c "
import sys
try:
    import chromadb
    c = chromadb.HttpClient(host='localhost', port=$CHROMA_PORT)
    names = [col.name for col in c.list_collections()]
    print(','.join(names))
except Exception as e:
    print('ERROR:' + str(e), file=sys.stderr)
    sys.exit(1)
")
if [[ "$COLLECTIONS" != *"kinexushhd"* ]] || [[ "$COLLECTIONS" != *"nx2meapp"* ]]; then
  warn "ChromaDB collections not found (found: '$COLLECTIONS'). Running ingestion …"
  cd "$BACKEND_DIR"
  "$PYTHON" scripts/build_index.py
  info "Ingestion complete."
  cd "$SCRIPT_DIR"
else
  info "ChromaDB collections present: $COLLECTIONS"
fi

# =============================================================================
# 2. OLLAMA
# =============================================================================
if port_in_use $OLLAMA_PORT; then
  info "Ollama already serving on port $OLLAMA_PORT — skipping."
else
  if command -v brew >/dev/null 2>&1 && brew services list | grep -q "ollama.*started"; then
    info "Ollama is registered as a brew service but not yet up — waiting …"
    brew services start ollama >/dev/null 2>&1 || true
    wait_for "http://localhost:$OLLAMA_PORT/api/tags" "Ollama"
  elif command -v ollama >/dev/null 2>&1; then
    info "Starting Ollama server …"
    ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
    echo "$!" > "$LOG_DIR/ollama.pid"
    wait_for "http://localhost:$OLLAMA_PORT/api/tags" "Ollama"
  else
    error "ollama not found. Install with: brew install ollama && ollama pull qwen2.5"
  fi
fi

# Verify the required model is available
MODEL_PRESENT=$("$PYTHON" -c "
import urllib.request, json
data = json.load(urllib.request.urlopen('http://localhost:$OLLAMA_PORT/api/tags'))
names = [m['name'] for m in data.get('models', [])]
found = any('qwen2.5' in n for n in names)
print('yes' if found else 'no')
" 2>/dev/null || echo "no")

if [[ "$MODEL_PRESENT" != "yes" ]]; then
  warn "Model 'qwen2.5' not found locally. Pulling (~4.7 GB) …"
  ollama pull qwen2.5
fi

# =============================================================================
# 3. FASTAPI BACKEND
# =============================================================================
if port_in_use $BACKEND_PORT; then
  warn "FastAPI already running on port $BACKEND_PORT — skipping."
else
  info "Starting FastAPI backend on port $BACKEND_PORT …"
  cd "$BACKEND_DIR"
  "$VENV_DIR/bin/uvicorn" app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    > "$LOG_DIR/backend.log" 2>&1 &
  BACKEND_PID=$!
  echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
  cd "$SCRIPT_DIR"
  wait_for "http://localhost:$BACKEND_PORT/docs" "FastAPI backend"
fi

# =============================================================================
# 4. REACT FRONTEND (optional)
# =============================================================================
if [[ "$BACKEND_ONLY" == "true" ]]; then
  warn "Skipping frontend (--backend-only flag set)."
else
  if port_in_use $FRONTEND_PORT; then
    warn "React dev server already running on port $FRONTEND_PORT — skipping."
  else
    if ! command -v npm >/dev/null 2>&1; then
      error "npm not found. Install Node.js 18+: brew install node"
    fi

    # Install node_modules if missing
    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
      info "Installing frontend npm dependencies …"
      cd "$FRONTEND_DIR"
      npm install --silent
      cd "$SCRIPT_DIR"
    fi

    info "Starting React dev server on port $FRONTEND_PORT …"
    cd "$FRONTEND_DIR"
    BROWSER=none npm start > "$LOG_DIR/frontend.log" 2>&1 &
    echo "$!" > "$LOG_DIR/frontend.pid"
    cd "$SCRIPT_DIR"
    wait_for "http://localhost:$FRONTEND_PORT" "React frontend" 60
  fi
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All services are running                          ${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "  ChromaDB   → http://localhost:$CHROMA_PORT"
echo -e "  Ollama     → http://localhost:$OLLAMA_PORT"
echo -e "  FastAPI    → http://localhost:$BACKEND_PORT"
echo -e "  Swagger UI → http://localhost:$BACKEND_PORT/docs"
if [[ "$BACKEND_ONLY" != "true" ]]; then
  echo -e "  Frontend   → http://localhost:$FRONTEND_PORT"
fi
echo -e ""
echo -e "  Logs       → $LOG_DIR/"
echo -e "${GREEN}════════════════════════════════════════════════════${NC}"
echo ""
echo "To stop all services: bash $SCRIPT_DIR/stop.sh"
