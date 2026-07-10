#!/bin/bash
# run_checks.sh — run everything; exit non-zero on any failure.
# Owner usage: type ./run_checks.sh and press Enter — you want to see "ALL CHECKS PASSED".
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "1/3 Backend tests..."
cd "$ROOT/backend"
python -m pytest tests/ -q

echo "2/3 Frontend type check..."
cd "$ROOT/frontend"
npx tsc --noEmit

echo "3/3 Frontend production build..."
npm run build

echo "ALL CHECKS PASSED ✅"
