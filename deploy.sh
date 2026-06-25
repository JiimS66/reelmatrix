#!/usr/bin/env bash
# One command to update the running app: pull latest code, rebuild, restart.
set -e
cd "$(dirname "$0")"

echo "→ Pulling latest code…"
git pull

echo "→ Building + restarting (the first run takes a few minutes)…"
docker compose up -d --build

IP=$(grep -E '^PUBLIC_IP=' .env | cut -d= -f2)
echo ""
echo "✓ Done.  Open  http://${IP}:3000     (API runs at :8000)"
echo "  Logs:  docker compose logs -f"
