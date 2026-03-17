# Architecture

## Overview

The game has two main parts: a **puzzle engine** that generates logic puzzles, and a **web layer** that manages game rooms and serves the UI.

```
Player browsers  <──WebSocket──>  FastAPI  <──>  Puzzle Engine
                 <──REST API───>          <──>  In-Memory Store
```

All state is in-memory. There's no database — restarting the server clears everything. This is intentional for a party game with short-lived sessions.

## Puzzle Engine

The engine lives in `backend/app/puzzle/` and follows a pipeline:

```
schema  →  generator  →  murder  →  clues  →  selector  →  distributor
                           ↑                      ↑
                        solver  ←──────────────────┘
```

### 1. Schema (`schema.py`)

Defines the value pools for each category (nationality, house_color, drink, pet, weapon) with 10 values each. `get_schema(n)` slices the first `n` values from each active category.

**Category scaling** keeps puzzles tractable at higher player counts:

| Players | Categories                                    | Total (+ name) |
|---------|-----------------------------------------------|-----------------|
| 3-4     | weapon, nationality, drink, house_color, pet  | 6               |
| 5-6     | weapon, nationality, drink, house_color        | 5               |
| 7-10    | weapon, nationality, drink                     | 4               |

### 2. Generator (`generator.py`)

Creates a random valid solution by shuffling each category's values across `n` positions. A solution looks like:

```python
{
    "name":        ["Alice", "Bob",    "Charlie", "Diana"],
    "nationality": ["Danish", "British", "German", "Swedish"],
    "weapon":      ["Rope",  "Knife",   "Revolver", "Candlestick"],
    ...
}
```

Position `i` across all categories describes one "person" — e.g., position 0 is Alice, who is Danish, with the Rope.

### 3. Murder Chain (`murder.py`)

Randomly picks a weapon (and therefore a murderer — the person at that weapon's position). Builds a chain of 2-3 `DirectEquality` clues linking weapon → intermediate category → name:

```
"The person with the Rope drinks Coffee."
"The Coffee drinker is Alice."
```

These clues are spread across different cards so no single player can solve the murder alone.

### 4. Clue Types (`clues.py`)

Five clue types, each knowing how to constrain the solver and render as text:

| Type             | Example                                          |
|------------------|--------------------------------------------------|
| `DirectEquality` | "The Danish person lives in the Red house."      |
| `Negation`       | "The Danish person does not drink Coffee."       |
| `PositionClue`   | "The person in house 3 is British."              |
| `Adjacency`      | "The Tea drinker lives next to the Dog owner."   |
| `Ordering`       | "The Danish person lives to the left of the British person." |

`generate_candidates()` produces all valid clues from a solution (hundreds to thousands depending on `n`).

### 5. Solver (`solver.py`)

Uses Google OR-Tools CP-SAT (a C++ constraint solver) instead of pure Python. The key design choice is **inverse permutation variables**:

- Forward: `fwd[cat][pos]` = which value is at position `pos`
- Inverse: `inv[cat][val]` = which position has value `val`
- Linked via `model.AddInverse(fwd, inv)`

This makes constraints very cheap. `DirectEquality("Danish", "Red house")` becomes a single constraint: `inv["nationality"][danish_int] == inv["house_color"][red_int]`.

Solution counting uses `CpSolverSolutionCallback` with `StopSearch()` for early stopping — we only need to know if there are 0, 1, or 2+ solutions.

### 6. Selector (`selector.py`)

Greedy algorithm that picks the minimal set of clues yielding a unique solution:

1. Start with the murder chain clues
2. Sample candidates, pick the one that most reduces the solution count
3. Repeat until unique
4. Prune: try removing each non-murder clue; keep it only if removal breaks uniqueness

### 7. Distributor (`distributor.py`)

Deals clues to player cards. Always adds the next clue to whichever card currently has the fewest clues, so card sizes differ by at most 1. Murder clues are placed on separate cards first.

~20% of non-murder clues are duplicated across cards (also targeting the smallest card), so players have some overlap to verify information.

### 8. Value Mapping (`value_mapping.py`)

Bidirectional string-to-integer mapping per category. CP-SAT requires integer variables, but the rest of the codebase works with strings. This module sits between the two.

## Web Layer

### Backend API

| Endpoint                        | Method | Purpose                    |
|---------------------------------|--------|----------------------------|
| `/api/games`                    | POST   | Create a game room         |
| `/api/games/{code}/join`        | POST   | Join a room                |
| `/api/games/{code}`             | GET    | Room info (phase, players) |
| `/api/games/{code}/start`       | POST   | Host starts the game       |
| `/api/games/{code}/card`        | GET    | Get your clue card         |
| `/api/games/{code}/guess`       | POST   | Submit accusation          |
| `/api/games/{code}/solution`    | GET    | Reveal solution (after game ends) |
| `/api/games/{code}/ws`          | WS     | Real-time events           |

### WebSocket Events

| Event                | Direction      | Data                            |
|----------------------|----------------|---------------------------------|
| `player_joined`      | server → client | `{player_id, player_name}`     |
| `player_disconnected`| server → client | `{player_id, player_name}`     |
| `game_starting`      | server → client | `{message}`                    |
| `game_started`       | server → client | `{message}`                    |
| `guess_made`         | server → client | `{player_name, suspect, correct}` |
| `game_over`          | server → client | `{murderer}`                   |
| `ping` / `pong`      | client ↔ server | keepalive                      |

### Game State (`game_state.py`)

A singleton `GameStore` holds all active `GameRoom` objects in a dict. Each room tracks:
- Players and their WebSocket connections
- Game phase: `lobby` → `generating` → `playing` → `finished`
- Puzzle solution, cards, murder info, and guesses

### Frontend

React SPA with five pages following the game flow:

```
HomePage  →  LobbyPage  →  GamePage  →  GuessPage  →  ResultPage
  /          /lobby/:code   /game/:code  /guess/:code  /result/:code
```

State is managed via React Context (`GameContext`). The WebSocket hook (`useWebSocket`) handles real-time updates. HTTP calls go through `api/http.ts`.
