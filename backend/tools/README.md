# Developer tools

Scripts for **balancing and manually checking** games during development.
None of this is product code: it is not part of the `app` package (so it is
never installed or served), and it is not part of the test suite (pytest only
collects `tests/`). Run everything from `backend/`.

| Tool | Status | Needs |
|---|---|---|
| `trading_city_sim.py` | Usable | Nothing beyond `uv sync --dev` |
| `tc_browser/` | **Work in progress** | Google Chrome installed locally, backend + Vite running |

## Trading City economy simulator

Plays seeded games entirely through the rules engine (no server, no timers,
runs in seconds) and prints economy metrics: auction prices, projects built by
type and timing, VP, end cash, money removed, shortages.

```bash
uv run python -m tools.trading_city_sim                      # defaults, 20 games
uv run python -m tools.trading_city_sim --games 50 --humans 3
uv run python -m tools.trading_city_sim prestige_cash_per_vp=3 cash_per_vp=12
uv run python -m tools.trading_city_sim --compare grand_city_from_round=1
```

- Positional `key=value` arguments override any `BalanceConfig` field
  (`app/trading_city/config.py`); `none` sets a field to `None`.
- `--compare` prints the defaults and your overrides side by side.
- Humans are simulated as **idle**: no lots, no bids, always pass on projects.
  The results describe an AI-driven economy. Real players bid harder, so treat
  cash/price numbers as a rough baseline, not a prediction.

## Headless-Chrome scripts (`tc_browser/`) — work in progress

> **Status: work in progress, not in a final state.** These scripts drive the
> real UI through the Chrome DevTools Protocol. They rely on fixed sleeps for
> rendering, assume local default ports, and may break when the UI changes.
> They are useful for eyeballing screens, not as automated tests. A proper
> setup (e.g. Playwright with real assertions) would replace them.

### Requirements

1. **Google Chrome installed locally.** Start it headless with remote debugging:

   ```bash
   # macOS
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
       --headless=new --remote-debugging-port=9222 \
       --user-data-dir=/tmp/tc-chrome --no-first-run --hide-scrollbars about:blank
   ```

   On Linux use `google-chrome` (or `chromium`) with the same flags.
2. **Backend and Vite running** (`./run.sh` from the repo root). The scripts talk
   to the Vite dev server (`http://localhost:5173`), which proxies the API.
3. Dev dependencies installed (`uv sync --dev`, for `httpx`).

The scripts check Chrome and the frontend first and print these instructions if
either is missing.

### Scripts

```bash
# Phone + TV screenshots of lobby, city selection, lots, auction, projects (~1 min)
uv run python -m tools.tc_browser.screenshots

# One live round vs the AI with real timers (~2-3 min): prints every auction's
# bid sequence and the project order, and screenshots the dashboard
uv run python -m tools.tc_browser.live_ai_game
uv run python -m tools.tc_browser.live_ai_game --ai-priority after_humans
```

Screenshots go to `tools/tc_browser/output/` (git-ignored); change with `--out`.
`--chrome` and `--frontend` override the default URLs.
