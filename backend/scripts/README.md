# Scripts

## pregenerate.py

Pre-generates puzzles for every `(player_count, difficulty)` configuration and saves them as JSON files to `backend/data/puzzles/`.

### What it does

- Iterates over all player counts (4–12) and difficulties (easy, medium, hard, harder, hardest)
- Generates 3 puzzles per configuration (135 total)
- Saves each as `{n}p_{difficulty}_{i}.json` (e.g., `4p_medium_0.json`)
- Skips files that already exist, so it's safe to re-run after a partial run
- Uses deterministic seeds for reproducibility
- Uses placeholder player names (`Player 1`, `Player 2`, etc.) — real names need to be swapped in at load time

### How to run

```sh
cd backend
uv run python scripts/pregenerate.py
```

### Caveats

- **Slow for large/hard configs.** Higher player counts (10–12) with harder/hardest difficulty can take minutes per puzzle. The full run may take over an hour.
- **Placeholder names only.** The generated puzzles use generic names. Loading logic to substitute real player names into the solution, clues, and cards is not yet implemented.
- **No integration with the game server.** The server does not yet load pre-generated puzzles from disk. This is generation-only for now.
