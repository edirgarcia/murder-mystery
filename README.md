# Nyxx Party Games

A browser-based multiplayer party game platform. One FastAPI backend serves room management, game APIs, WebSockets, and production static files for several React/Vite games.

Players join from their phones with a 4-letter room code or QR link. Hosts run the shared lobby flow, start the game, and use a dashboard view where the game needs one.

## Games

| Game | Local Path | API Prefix | Summary |
|---|---|---|---|
| Murder Mystery | `/murder-mystery/` | `/api/mm/games` | Logic-puzzle deduction game where players share clue cards and identify the murderer and weapon. |
| Funny Questions | `/funny-questions/` | `/api/fq/games` | "Most likely to" voting game with configurable spice levels, scoring, and shame mechanics. |
| Werewolf | `/werewolf/` | `/api/ww/games` | Social deduction game with hidden roles, night actions, day votes, and live narration. |
| Prisoner's Dilemma | `/prisoners-dilemma/` | `/api/pd/games` | Team trust/betrayal strategy game with hidden spies and round-by-round accusations. |

## Quick Start

Prerequisites:

- Python 3.11+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/)
- npm

Install dependencies:

```bash
cd backend
uv sync --dev

cd ../frontend
npm install
```

Run the backend and frontend together:

```bash
cd ..
./run.sh
```

Local URLs:

- Main menu: `http://localhost:5173/`
- Murder Mystery: `http://localhost:5173/murder-mystery/`
- Funny Questions: `http://localhost:5173/funny-questions/`
- Werewolf: `http://localhost:5173/werewolf/`
- Prisoner's Dilemma: `http://localhost:5173/prisoners-dilemma/`
- Backend API docs: `http://localhost:8000/docs`

## Running Services Manually

Backend:

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

## Tests And Checks

Backend tests:

```bash
cd backend
uv run pytest tests/ -v
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Architecture

The backend is a single FastAPI app:

- Shared lobby routes create rooms, join players, return game info, and manage common WebSocket connections.
- Each game owns its own state model, routes, scoring/game loop, and response models.
- State is in memory. There is no database, so rooms are ephemeral and do not survive process restarts.
- In production, FastAPI also serves the Vite build output and handles SPA fallbacks for each game path.

The frontend is a multi-entry Vite app:

- `frontend/index.html` is the main menu.
- Each game has its own HTML entry point and React app under `frontend/src/<game>/`.
- Shared frontend helpers live under `frontend/src/shared/`.
- Vite proxies game-prefixed API/WebSocket paths to the backend during development.

## Project Structure

```text
backend/
  app/
    main.py                # FastAPI app, routers, production static serving
    shared/                # Shared lobby, WebSocket, room, and config code
    murder_mystery/        # Murder Mystery game state, routes, and models
    funny_questions/       # Funny Questions prompts, scoring, routes, and models
    werewolf/              # Werewolf roles, game logic, routes, and models
    prisoners_dilemma/     # Prisoner's Dilemma game logic, routes, and models
    puzzle/                # Logic puzzle generation engine for Murder Mystery
  tests/

frontend/
  index.html               # Main menu
  murder-mystery.html      # Murder Mystery entry point
  funny-questions.html     # Funny Questions entry point
  werewolf.html            # Werewolf entry point
  prisoners-dilemma.html   # Prisoner's Dilemma entry point
  src/
    shared/                # Shared API, context, hooks, components, and types
    murder-mystery/
    funny-questions/
    werewolf/
    prisoners-dilemma/

docs/
  architecture.md          # Murder Mystery puzzle engine notes
  audio.md                 # Audio/narration notes
  deployment.md            # Azure Container Apps deployment runbook
```

## Deployment

Production runs as a single Docker container on Azure Container Apps. The container builds the frontend, installs the backend, and serves both from FastAPI.

Current production routes:

- `https://www.nyxxgames.com/`
- `https://www.nyxxgames.com/murder-mystery/`
- `https://www.nyxxgames.com/funny-questions/`
- `https://www.nyxxgames.com/werewolf/`
- `https://www.nyxxgames.com/prisoners-dilemma/`

See [docs/deployment.md](docs/deployment.md) for the full build, push, and Azure Container Apps update flow.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Pydantic, WebSockets, OR-Tools CP-SAT |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Package management | uv, npm |
| Runtime state | In-memory rooms |
| Production | Docker, Azure Container Apps, Azure Container Registry |

