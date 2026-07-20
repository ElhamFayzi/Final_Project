# Petty-Court

## Project structure

```
petty-court/
├── app/
│   ├── app.py          # Flask app entrypoint
│   ├── db.py            # SQLAlchemy setup
│   ├── game_logic/      # Pure game logic (state machine, role assignment); no I/O nor Flask
│   ├── models/           # SQLAlchemy models (Player, Game, Case, Vote, etc.)
│   ├── static/            # CSS, JS, images served to the browser
│   └── templates/         # Jinja templates
├── instance/              # Local instance data (e.g. the SQLite db file)
├── tests/                 # Automated tests
├── requirements.txt
└── README.md
```

Feel free to add to or change the structure