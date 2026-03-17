#!/usr/bin/env bash
set -e

# Load env vars (e.g. NPM_REMOTE_TOKEN)
if [ -f .env ]; then
  source .env
fi

trap 'kill 0' EXIT

# Backend
(cd backend && uv run uvicorn app.main:app --reload --port 8000) &

# Frontend
(cd frontend && npm run dev) &

wait
