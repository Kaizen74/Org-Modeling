#!/bin/bash
# run_checks.sh — run everything; exit non-zero on any failure.
# Owner usage: type ./run_checks.sh and press Enter — you want to see "ALL CHECKS PASSED".
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
MOCK_DIR="$ROOT/scripts/mock_journey"

# Servers and scratch folders started below; all stopped/removed on exit, pass or fail
PIDS=""; TMPS=""
cleanup() { for p in $PIDS; do kill "$p" 2>/dev/null || true; done; for d in $TMPS; do rm -rf "$d"; done; }
trap cleanup EXIT
wait_for() { for i in $(seq 1 60); do curl -sf "$1" >/dev/null && return 0; sleep 0.5; done; echo "FAIL  $1 did not start"; return 1; }
# exec so the recorded PID is the server itself and cleanup really stops it
start_web() { # <port> <api port> <log>
  (cd "$ROOT/frontend" && API_PROXY_TARGET="http://localhost:$2" exec node node_modules/vite/bin/vite.js preview --port "$1" --strictPort > "$3" 2>&1) & PIDS="$PIDS $!"
}
start_fake_api() { # <port> <folder>: backend with a fake Claude, fresh database, own folder for its .env
  mkdir -p "$2"
  (cd "$2" && exec python "$MOCK_DIR/fake_claude_server.py" "$1" "$2/mock.db" "$2/prompts.jsonl" "$ROOT/backend" > "$2/api.log" 2>&1) & PIDS="$PIDS $!"
}

PW="$(readlink -f /opt/node22/lib/node_modules/playwright 2>/dev/null || true)"
[ -n "$PW" ] && [ -f "$PW/index.js" ] || PW=""

echo "1/5 Backend tests..."
cd "$ROOT/backend"
python -m pytest tests/ -q

echo "2/5 Frontend type check..."
cd "$ROOT/frontend"
npx tsc --noEmit

echo "3/5 Frontend production build..."
npm run build

echo "4/5 End-to-end smoke test (browser → frontend → backend)..."
if [ -z "$PW" ]; then
  echo "SKIPPED: Playwright not installed on this machine"
else
  TMP="$(mktemp -d)"; TMPS="$TMPS $TMP"
  API_PORT=8765; WEB_PORT=4765
  (cd "$ROOT/backend" && DATABASE_URL="sqlite+aiosqlite:///$TMP/smoke.db" exec python -m uvicorn app.main:app --port $API_PORT > "$TMP/api.log" 2>&1) & PIDS="$PIDS $!"
  start_web $WEB_PORT $API_PORT "$TMP/web.log"
  wait_for "http://localhost:$API_PORT/health"; wait_for "http://localhost:$WEB_PORT/"
  curl -sf -F "file=@$ROOT/backend/tests/fixtures/org_structure_PAX.csv;type=text/csv" "http://localhost:$API_PORT/api/v1/org-data/upload-csv" > /dev/null \
    || { echo "FAIL  could not upload the test CSV"; tail -5 "$TMP/api.log"; exit 1; }
  node "$ROOT/scripts/smoke_e2e.mjs" "http://localhost:$WEB_PORT" "$PW/index.js"
fi

echo "5/5 Mock journey (whole workflow, fake Claude, sample org with messy data)..."
MOCK="$(mktemp -d)"; TMPS="$TMPS $MOCK"
python "$MOCK_DIR/make_org.py" "$MOCK/org.csv" > /dev/null
start_fake_api 8766 "$MOCK/api"
wait_for "http://localhost:8766/health"
python "$MOCK_DIR/journey_api.py" "http://localhost:8766" "$MOCK/org.csv" "$MOCK/api/prompts.jsonl" \
  || { echo "Backend log (last lines):"; tail -20 "$MOCK/api/api.log"; exit 1; }
if [ -z "$PW" ]; then
  echo "SKIPPED browser half: Playwright not installed on this machine"
else
  # Separate backend and database, so the browser journey also starts from nothing
  start_fake_api 8767 "$MOCK/ui"
  start_web 4766 8767 "$MOCK/web.log"
  wait_for "http://localhost:8767/health"; wait_for "http://localhost:4766/"
  node "$MOCK_DIR/journey_ui.mjs" "http://localhost:4766" "$PW/index.js" "$MOCK/org.csv" \
    || { echo "Backend log (last lines):"; tail -20 "$MOCK/ui/api.log"; exit 1; }
fi

echo "ALL CHECKS PASSED ✅"
