# Team Plot Twist

**Version 1.0.0** · A cooperative class project: escape from a pirate ship through exploration, stealth, disguise or combat.

Start with [START_HERE.md](START_HERE.md). It explains how to download the code, run the game, and contribute with GitHub Desktop.

## Run the game

Install [Python 3.12](https://www.python.org/downloads/) and [uv](https://docs.astral.sh/uv/getting-started/installation/). Open a terminal in this folder:

```bash
uv sync --locked
uv run streamlit run app.py --server.port 8535
```

Open **http://localhost:8535**. On a Mac you can also run `run-team.command`; on Windows run `run-team.bat` after installing uv.

```bash
uv run pytest -q
```

## Four escape routes

- **Takeover:** Defeat every opponent and use the helm.
- **Crate 07:** Open the crate with a crowbar or bribe the cook. Keep the cook alive and wait for the next port.
- **Dinghy:** Find a sail and rope, or bring a sail and bribe the boatswain.
- **Command:** Ambush the officer from a barrel, equip the captain uniform from the cabin chest, let any search settle, and command the helm with other crew still alive.

## Controls

| Key | Action |
| --- | --- |
| A/D or Left/Right | Walk |
| W/Up; Down | Climb; descend |
| E | Take, steal, change clothes or ambush passing crew from a barrel |
| F | Inspect, use, hide or close a document |
| Space | Crouch / stand |
| R | Shoot with the selected pistol |
| T | Bribe a nearby helper |
| I; J | Inventory; journal |
| L; B | Toggle the held lamp; use an owned whistle |

Use the toolbar for music, volume, fullscreen and confirmed restart. Each round barrel can conceal one body. Carried keys are collected automatically during an ambush.

## Working together

Keep the GitHub repository **private** and invite only the project group as collaborators. Each person works on a feature branch and opens a pull request before merging to `main`. Read [CONTRIBUTING.md](CONTRIBUTING.md) for the steps and versioning rules.

A ZIP is convenient for trying the game. A Git clone is the best way to receive and contribute updates. This project has its own version history and does not automatically sync with another project.

## Code map

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

- `app.py`: Streamlit UI and component messages.
- `logic.py`, `voyage.py`, `escort.py`: Authoritative rules, combat and routes.
- `content.py`: Items, clues, roles and ending text.
- `db.py`: Save storage and migrations.
- `action_transport.py`: Safe request acknowledgements and retries.
- `game_component/`: Canvas drawing, controls, music and browser saves.
- `tests/`: Rules, saves, interactions and browser-rule parity tests.

Local saves live in `data/team-progress.sqlite3` and stay out of Git. Use `TEAM_PLOT_TWIST_DB` for an alternative database. Browser saves and music preferences use team-specific keys. No player saves are included in the source package.

Music credits and asset details are in [static/music/README.md](static/music/README.md).
