# Architecture

Streamlit supplies Python state to a local Canvas component. The browser animates movement between server updates and sends discrete actions with request IDs. `action_transport.py` acknowledges retries without repeating a mutation. `db.py` persists each browser player's validated game state in SQLite.

`logic.py` owns map boundaries, patrols, sight, capture, story interactions and backup validation. `voyage.py` handles coins, bribes, rotating watches, guard projectiles, barrel ambushes and captain command. `escort.py` handles cover-aware guides and return paths. `content.py` supplies English story content.

The Canvas component renders characters, the map and ending scenes. UI feedback can be immediate, but successful inventory, kills and endings must come from the server. The `runtime_loader.py` source fingerprint refreshes warm workers after code changes; component caching includes actual HTML/CSS/JS content.

Browser identity and backup are in `game_component/browser_identity.js` and `browser_backup.js`. Both must use the same team save key. The JavaScript client/music globals and database environment variable are also team-specific.

Audio assets are served from `static/music/` with static serving enabled in `.streamlit/config.toml`. They are not sent with every state update. A single music controller survives rerenders, switches between exploration and alert recordings, and pauses when the game is no longer active.

Tests execute server rules and, when Node is installed, compare actual Canvas functions with Python. Install Node to run those parity checks locally. Read CONTRIBUTING before changing state formats or creating a release.

## Cannon finale

`finale.py` owns the mandatory last scene after an escape route: it picks the ten-ball volley from a stored seed, judges the moves the page reports and records `active`, `won` or `lost` in `voyage.finale` (validated in `voyage.valid` and `logic.state_from_backup`). The finale record never replaces `GameState.ending`. `game.js` plays the beach reveal, volley, and rescue epilogue; a loss shows a caught panel with `finale_retry`, which starts a new seeded attempt without changing the route or resetting the save. The `FINALE` timing values stay equal to `finale.py`; tests check that. Ordinary actions are rejected once a route is reached. `finale_start`, `finale_report`, and `finale_retry` are dispatched by `db.apply_action`.
