#!/usr/bin/env bash
# Checks a running `docker compose up`: API health, seeded demo data, samples and the UI. Spends no tokens.
set -euo pipefail

API=${API:-http://localhost:8000}
UI=${UI:-http://localhost:5173}

curl -fsS "$API/health" | grep -q '"status":"ok"'
echo "ok: API health"

count=$(curl -fsS "$API/api/submissions" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)))')
[ "$count" -gt 0 ]
echo "ok: $count demo candidates"

samples=$(curl -fsS "$API/api/samples" | python3 -c 'import json, sys; print(len(json.load(sys.stdin)))')
[ "$samples" -gt 0 ]
echo "ok: $samples samples"

curl -fsS "$UI/" | grep -q '<div id="root">'
echo "ok: UI served"

origin=$(curl -fsS -o /dev/null -D - -H "Origin: $UI" "$API/health" | tr -d '\r' | awk 'tolower($1) == "access-control-allow-origin:" {print $2}')
[ "$origin" = "$UI" ]
echo "ok: CORS allows the UI"
