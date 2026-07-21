# Petty-Court

## Project structure

```
petty-court/
├── app/
│   ├── __init__.py      # create_app() factory: config, db.init_app(), db.create_all(), blueprint registration
│   ├── db.py              # db = SQLAlchemy() instance
│   ├── game_logic/         # State machine + role assignment (pure, no I/O) and room/token logic (touches the db)
│   ├── models/               # SQLAlchemy models (Game, Player, Case, Vote)
│   ├── routes/                 # Flask blueprints; parse the request, call into game_logic/, return a response
│   ├── static/                   # CSS, JS, images served to the browser
│   │   └── host/                   # Big-screen shell (host.html/js/css)
│   └── templates/                   # Jinja templates
├── instance/                          # Local instance data (e.g. the SQLite db file) — gitignored
├── tests/                               # Automated tests
├── requirements.txt
├── run.py                                # Entrypoint — creates the app, runs the dev server
└── README.md
```

Feel free to add to or change the structure.

You can run tests by running `pytest` or `pytest -v` at the repo root.
