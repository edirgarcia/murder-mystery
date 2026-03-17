# Murder Mystery Party Game

A multiplayer party game where players receive clue cards and work together to figure out who committed the murder — and with what weapon.

Each game generates a unique logic puzzle (think Zebra/Einstein puzzle). Clues are distributed across player cards so no one person has the full picture. Players share information verbally, piece together the solution, and make their accusation.

## Quick Start

**Prerequisites:** Python 3.11+, Node.js 18+, [uv](https://docs.astral.sh/uv/)

```bash
# Install dependencies
cd backend && uv sync --dev && cd ..
cd frontend && npm install && cd ..

# Run both servers
./run.sh
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## How to Play

1. One player creates a game and shares the 4-letter room code
2. Other players join using the code (4-10 players)
3. The host starts the game — a puzzle is generated and clue cards are dealt
4. Each player sees their card with a subset of clues
5. Talk to each other, share clues, and deduce who has the murder weapon
6. When ready, each player makes an accusation
7. Once everyone has guessed, the solution is revealed

## Running Individually

**Backend:**
```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**Tests:**
```bash
cd backend
uv run pytest tests/ -v
```

## Project Structure

```
backend/
  app/
    puzzle/       # Puzzle generation engine
    routes/       # API endpoints + WebSocket
    config.py     # Player limits, CORS origins
    game_state.py # In-memory game rooms
    models.py     # Pydantic request/response models
    main.py       # FastAPI app entry point
  tests/
frontend/
  src/
    pages/        # Home, Lobby, Game, Guess, Result
    components/   # CharacterCard, ClueList, PlayerList
    context/      # React context for game state
    hooks/        # WebSocket hook
    api/          # HTTP client functions
    types/        # TypeScript interfaces
```

See [docs/architecture.md](docs/architecture.md) for a deeper look at how the puzzle engine works.

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | FastAPI, OR-Tools CP-SAT, Pydantic  |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Realtime | WebSockets (native FastAPI)         |
| State    | In-memory (ephemeral, no database)  |
| Packages | uv (Python), npm (JS)               |
