# Claude Code Instructions

## Commit Guidelines
- Never add "Co-Authored-By" lines to commit messages

## Architecture: Multi-Game Platform

This project is the first of multiple games that will share a base URL (e.g., `example.com/murder-mystery`, `example.com/trivia`). Each game has its own `base` path configured in `vite.config.ts`.

**When a second game is added**, extract the following shared infrastructure into reusable packages (monorepo with `packages/` + `apps/`):

### Backend (shared Python package)
- `GameStore` — room creation, join, player management, room lookup (`app/game_state.py`)
- Lobby routes — create, join, get info (`app/routes/lobby.py`)
- WebSocket broadcast + reconnection (`app/routes/ws.py`)
- Base models — `GamePhase`, `PlayerInfo`, room model (`app/models.py`)
- Phase state machine — lobby → playing → finished

### Frontend (shared npm packages)
- `useWebSocket` hook (`src/hooks/useWebSocket.ts`)
- `GameContext` pattern — room state, player identity, session persistence (`src/context/GameContext.tsx`)
- `HomePage` flow — create/join with code or QR scan (`src/pages/HomePage.tsx`)
- `LobbyPage` / `PlayerList` — waiting room with live player list
- Host dashboard shell — player list + controls + start button

### What stays game-specific
- Game logic (e.g., puzzle engine, question system)
- Game-specific pages (card view, guess page, results)
- Game-specific WebSocket event handlers
