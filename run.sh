#!/usr/bin/env bash
set -e

# Load env vars (e.g. NPM_REMOTE_TOKEN)
if [ -f .env ]; then
  source .env
fi

trap 'kill 0' EXIT

# Single backend serves both games: /api/mm/games and /api/fq/games
(cd backend && uv run uvicorn app.main:app --reload --port 8000) &

# Single Vite dev server serves both SPAs:
#   http://localhost:5173/murder-mystery/   (murder-mystery.html)
#   http://localhost:5173/funny-questions/  (funny-questions.html)
(cd frontend && npm run dev) &

wait
