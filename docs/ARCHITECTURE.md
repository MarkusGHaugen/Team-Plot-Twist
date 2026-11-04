# Architecture

Streamlit supplies Python state to a local Canvas component. The browser animates movement between server updates and sends discrete actions with request IDs. `action_transport.py` acknowledges retries without repeating a mutation. `db.py` persists each browser player's validated game state in SQLite.

`logic.py` owns map boundaries, patrols, sight, capture, story interactions and backup validation. `voyage.py` handles coins, bribes, rotating watches, guard projectiles, barrel ambushes and captain command. `escort.py` handles cover-aware guides and return paths. `content.py` supplies English story content.

The Canvas component renders characters, the map and ending scenes. UI feedback can be immediate, but successful inventory, kills and endings must come from the server. The `runtime_loader.py` source fingerprint refreshes warm workers after code changes; component caching includes actual HTML/CSS/JS content.

Browser identity and backup are in `game_component/browser_identity.js` and `browser_backup.js`. Both must use the same team save key. The JavaScript client/music globals and database environment variable are also team-specific.

Audio assets are served from `static/music/` with static serving enabled in `.streamlit/config.toml`. They are not sent with every state update. A single music controller survives rerenders, switches between exploration and alert recordings, and pauses when the game is no longer active.

Tests execute server rules and, when Node is installed, compare actual Canvas functions with Python. Install Node to run those parity checks locally. Read CONTRIBUTING before changing state formats or creating a release.
