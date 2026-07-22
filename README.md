# Petty Court

A Jackbox-style party game where players litigate absurd, petty grievances in front of an AI judge. One device (a laptop, a TV browser) acts as the **big screen**; everyone else joins from their own phone as a **player**. Each round, two players are cast as plaintiff and defendant over a randomly picked petty dispute ("Who left one square of toilet paper on the roll"), write their arguments, and an AI judge hands down a verdict, awards Petty Points, and the rest of the players vote on who they think won. Whoever has the most points when the game ends is crowned pettiest of them all.

## How a game flows

```
LOBBY → CASE_REVEAL → ARGUMENTS → VERDICT → JURY_VOTE → SCOREBOARD ─┐
  ▲                                                                  │
  └──────────────────────── next case ──────────────────────────────┘
                                                                      │
                                                            (or) → FINALE
```

1. **Lobby** : host creates a room and shares the join code; players join by
   name from their own device.
2. **Case reveal** : two players (whoever has litigated the fewest times so
   far) are assigned plaintiff/defendant for a randomly picked prompt.
3. **Arguments** : both litigants write their case on their own phone,
   against a 45-second countdown; everyone else waits as the jury.
4. **Verdict** : the AI judge (Gemini) reads both arguments and returns a
   ruling, reasoning, a winner, and how many Petty Points they're awarded.
   If the judge is unreachable or returns something unparseable, a
   fallback verdict is used instead so the round never crashes.
5. **Jury vote** : everyone who *wasn't* litigating this round votes on who
   they think the judge sided with; guessing right earns a small bonus.
6. **Scoreboard** : standings after the round, before the next case begins.
7. Steps 2–6 repeat until every player has litigated at least
   `target_turns` times (configurable by the host in the lobby), or the
   host ends the game early : then it's **Finale**: a full final leaderboard.

## Tech stack

- **Backend:** Flask + Flask-SQLAlchemy, SQLite
- **Frontend:** HTML/CSS/JS: the browser polls the backend every 1.5s for the current game state and re-renders
- **AI judge:** Google Gemini (`gemini-2.5-flash` by default)
- **Tests:** pytest
- **Deployment:** Gunicorn behind Railway

## Project structure

```
petty-court/
├── app/
│   ├── __init__.py         # create_app() factory: config, db.init_app(), db.create_all(), blueprint registration
│   ├── db.py                # db = SQLAlchemy() instance
│   ├── llm_client.py          # Only place that talks to the Gemini API over the network
│   ├── game_logic/              # Pure game rules + DB orchestration
│   │   ├── state_machine.py       # The phase graph (LOBBY → ... → FINALE) and legal transitions — no I/O
│   │   ├── role_assignment.py     # Picks each round's plaintiff/defendant fairly — no I/O
│   │   ├── scoring.py             # Turns a verdict + jury votes into points earned — no I/O
│   │   ├── judge.py               # Builds the judge prompt, parses/validates the verdict, fallback verdict — no I/O
│   │   ├── prompts.py             # The bank of petty case prompts
│   │   ├── tokens.py              # Join code / auth token generation
│   │   ├── rooms.py               # DB-orchestration layer: create/join rooms, advance phases, score, etc.
│   │   └── state_view.py          # Builds the single JSON blob every client polls and renders from
│   ├── models/                  # SQLAlchemy models: Game, Player, Case, Vote
│   ├── routes/                  # Thin Flask blueprint — parses requests, calls game_logic/, returns JSON
│   ├── static/
│   │   ├── host/                  # Big-screen shell (host.html/css/js)
│   │   ├── player/                # Phone shell (player.html/css/js)
│   │   └── shared/                 # Shared theme, avatar rendering, images
│   └── templates/
│       └── index.html             # Landing page: "I'm the Big Screen" / "I'm a Player"
├── instance/                    # Local SQLite db file lives here (gitignored)
├── tests/                       # pytest suite, mirrors the app/ layout
├── requirements.txt
├── Procfile                      # Gunicorn start command, used by Railway
└── run.py                        # Local dev entrypoint
```

The `game_logic/` split is deliberate: `state_machine.py`, `role_assignment.py`, `scoring.py`, and `judge.py` are pure functions with no database or network access, so they're fast and simple to unit test in isolation. `rooms.py` is where those pure pieces get wired up to actual `Game`/`Player`/`Case`/`Vote` rows. `routes/rooms.py` stays a thin HTTP layer on top of `rooms.py`.

## Running it locally

**Requirements:** Python 3.13+ (a `.venv` is expected at the repo root).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export GEMINI_API_KEY="your-key-here"
python run.py                            # serves on http://localhost:5000
```

Then open `http://localhost:5000` and choose **I'm the Big Screen** on one
device/tab and **I'm a Player** on others (or other tabs, for local testing).

> macOS note: port 5000 is sometimes claimed by the AirPlay Receiver system
> service, which will make every request 403. If that happens, run with a
> different port instead: `PORT=5050 python run.py`.

### Environment variables

| Variable          | Required | Default            | Purpose                                                                 |
|--------------------|:--------:|---------------------|--------------------------------------------------------------------------|
| `GEMINI_API_KEY`   | No       | —                    | Google Gemini API key. Without it, every verdict silently uses the fallback verdict (a random winner, 0 damages) instead of a real AI ruling |
| `GEMINI_MODEL`     | No       | `gemini-2.5-flash`   | Overrides which Gemini model is called.                                  |
| `PORT`             | No       | `5000`               | Port the dev server (or gunicorn, in production) binds to.               |

There is no `.env` loading built in; export these in your shell (or set
them in Railway's environment settings for deployment).

## Running tests

```bash
pytest        # or: pytest -v
```

The suite uses an in-memory SQLite database (see `tests/conftest.py`), so it needs no setup and leaves nothing behind. Tests exercising the judge/verdict path inject a fake client rather than calling the real Gemini API.

## API overview

All routes are under `/api/rooms` and return JSON. Every response includes `"success": true/false`; on failure, an `"error"` message explains why. `GET /api/rooms/<code>` is the single endpoint every client polls; its response shape is built by `state_view.build_state()` and varies by phase (e.g. `arguments_deadline` only appears during `arguments`, `score_rows` only during `scoreboard`/`finale`).

| Method & path                        | Who calls it | What it does                                  |
|----------------------------------------|--------------|------------------------------------------------|
| `POST /api/rooms`                       | Host         | Create a room, returns `join_code` + `host_token` |
| `POST /api/rooms/<code>/join`           | Player       | Join by name, returns `player_token`             |
| `POST /api/rooms/<code>/leave`          | Player       | Leave the room                                     |
| `GET /api/rooms/<code>`                 | Everyone     | Poll the current game state                        |
| `POST /api/rooms/<code>/start`          | Host         | Lobby → first case                                  |
| `POST /api/rooms/<code>/argue`          | Host         | Case reveal → arguments (starts the 45s timer)        |
| `POST /api/rooms/<code>/argument`       | Player       | Submit your argument text                              |
| `POST /api/rooms/<code>/verdict`        | Host         | Arguments → verdict (calls the AI judge)                 |
| `POST /api/rooms/<code>/deliberate`     | Host         | Verdict → jury vote                                        |
| `POST /api/rooms/<code>/vote`           | Player       | Cast a jury vote (jurors only, not litigants)                |
| `POST /api/rooms/<code>/tally`          | Host         | Jury vote → scoreboard (applies score deltas)                  |
| `POST /api/rooms/<code>/settings`       | Host         | Update `target_turns` mid-lobby                                  |
| `POST /api/rooms/<code>/next-case`      | Host         | Scoreboard → next case, or → finale if the game is complete       |
| `POST /api/rooms/<code>/end`            | Host         | End the game immediately and jump to the finale                     |

Host-only routes require `host_token` in the JSON body; player routes require `token`. There are no cookies or sessions — the host and each player hold their own token in `localStorage` and send it with every request.

## Deployment

The app ships with a `Procfile` (`gunicorn run:app ...`), which Railway
picks up automatically (no separate Railway config file is needed). Set
`GEMINI_API_KEY` (and optionally `GEMINI_MODEL`) in the Railway project's
environment variables.

SQLite lives on disk at `instance/petty_court.db`, created automatically via `db.create_all()` on startup.

## Authors

- [Elham Fayzi](https://github.com/ElhamFayzi)
- [Nicole Jallim](https://github.com/Nicole-Jallim)
- [Ramir Caba](https://github.com/CCRamir)
- [riyap10](https://github.com/riyap10)
