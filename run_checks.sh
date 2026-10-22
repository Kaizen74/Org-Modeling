#!/bin/bash
# run_checks.sh — run everything; exit non-zero on any failure.
# Owner usage: type ./run_checks.sh and press Enter — you want to see "ALL CHECKS PASSED".
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "1/4 Backend tests..."
cd "$ROOT/backend"
python -m pytest tests/ -q

echo "2/4 Frontend type check..."
cd "$ROOT/frontend"
npx tsc --noEmit

echo "3/4 Frontend production build..."
npm run build

echo "4/4 End-to-end smoke test (browser → frontend → backend)..."
PW="$(readlink -f /opt/node22/lib/node_modules/playwright 2>/dev/null || true)"
if [ -z "$PW" ] || [ ! -f "$PW/index.js" ]; then
  echo "SKIPPED: Playwright not installed on this machine"
else
  TMP="$(mktemp -d)"
  API_PORT=8765; WEB_PORT=4765
  cleanup() { kill $API_PID $WEB_PID 2>/dev/null || true; rm -rf "$TMP"; }
  trap cleanup EXIT
  # exec so the recorded PID is the server itself and cleanup really stops it
  (cd "$ROOT/backend" && DATABASE_URL="sqlite+aiosqlite:///$TMP/smoke.db" exec python -m uvicorn app.main:app --port $API_PORT > "$TMP/api.log" 2>&1) & API_PID=$!
  (cd "$ROOT/frontend" && API_PROXY_TARGET="http://localhost:$API_PORT" exec node node_modules/vite/bin/vite.js preview --port $WEB_PORT --strictPort > "$TMP/web.log" 2>&1) & WEB_PID=$!
  for i in $(seq 1 40); do curl -sf "http://localhost:$API_PORT/health" >/dev/null && curl -sf "http://localhost:$WEB_PORT/" >/dev/null && break; sleep 0.5; done
  curl -sf -F "file=@$ROOT/backend/tests/fixtures/org_structure_PAX.csv;type=text/csv" "http://localhost:$API_PORT/api/v1/org-data/upload-csv" > /dev/null \
    || { echo "FAIL  could not upload the test CSV"; tail -5 "$TMP/api.log"; exit 1; }
  node "$ROOT/scripts/smoke_e2e.mjs" "http://localhost:$WEB_PORT" "$PW/index.js"
fi

echo "ALL CHECKS PASSED ✅"
