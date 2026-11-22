# Team Plot Twist

**Version 1.0.0** · A cooperative class project: escape from a pirate ship through exploration, stealth, disguise or combat.

Start with [START_HERE.md](START_HERE.md). It explains how to download the code, run the game, and contribute with GitHub Desktop.

## Run the game

Install [Python 3.12](https://www.python.org/downloads/) and [uv](https://docs.astral.sh/uv/getting-started/installation/). Open a terminal in this folder:

```bash
uv sync --locked
uv run streamlit run app.py --server.port 8535
```

Open **http://localhost:8535**. To preview an escape ending and its cannon plot twist, start with `TEAM_PLOT_TWIST_DEV=1` (for example `TEAM_PLOT_TWIST_DEV=1 uv run streamlit run app.py --server.port 8535`); a **Play escape ending → plot twist** button appears next to New Game. It only appears in a local development run and uses an isolated save. On a Mac you can also run `run-team.command`; on Windows run `run-team.bat` after installing uv.

```bash
uv run pytest -q
```

## Single player or multiplayer

Choose **Single player** or **Multiplayer** above the game. In multiplayer one player presses **Create room** and shares the six-letter code; the other enters it and presses **Join**. Both start in the cell and see each other move live. You share one ship: when one player steals the key or opens the cell, it happens for both, and the same goes for items, coins, chests, the crew, alarms and the ending. If a guard catches one of you, that player is taken back to the cell, the door is locked (you keep the key) and the crew search the ship for the other player for 30 seconds, starting where they were last seen. Reading a letter does not pause the game in multiplayer, and Restart restarts the ship for both. Setup of the Ably key is described in [CONTRIBUTING.md](CONTRIBUTING.md#multiplayer-setup-ably).

## Six escape routes

- **Takeover:** Defeat every opponent and use the helm.
- **Crate 07:** Return crate 07 waits on the middle deck between the two barrels. Open it with a crowbar or bribe the cook. Keep the cook alive and wait for the next port.
- **Dinghy:** Find a sail and rope, or bring a sail and bribe the boatswain.
- **Command:** Ambush the officer from a barrel, equip the captain uniform from the cabin chest, let any search settle, and command the helm with other crew still alive.
- **Drugged stew:** Take the sleeping pills from the sea chest in the cabin and crush them into the galley stew. Five seconds later the cook serves it, the whole crew eats in the mess hall and falls asleep for two minutes. Take the dinghy or the helm before they wake. A gunshot or the cannon wakes them.
- **Castaway:** Swallow the sleeping pills on the floor of your own cell. The crew think you are dead and throw you overboard in a barrel; after four days adrift you wash up on a deserted island.

## The last escape

Each of the six escape routes ends with its own scene, followed automatically by the mandatory cannon finale. The finale is the last scene of that route and does not change which ending you reached. Cheerful music plays as you celebrate on the beach, then cuts to the dramatic guard theme when the plot twist text reveals the guards are back. Dodge ten cannonballs fired about once a second: **W / ↑** jumps low shots and **Space / S / ↓** ducks high ones. You have three lives. Win, and cheerful music starts for the dog’s arrival in a small boat and the rescue epilogue, "Free at last"; your original ending remains recorded. If the guards catch you, choose **Try again** for a new volley. The game never resets automatically. **New Game** asks for confirmation before replacing your save. Details are in [specs/cannon-finale.md](specs/cannon-finale.md).

## Things to do aboard

- **Telescope:** Climb the mast and press F at the telescope. A/D look around the horizon.
- **Cannon:** Hold a lit lamp at the deck cannon and press F. The blast brings every pirate running to the cannon, which makes it a distraction if you hide in time.
- **Rats** scurry around the hold and run from anyone who comes close.

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
- `finale.py`: The cannon finale (volley, judging, saves).
- `content.py`: Items, clues, roles and ending text.
- `db.py`: Save storage and migrations.
- `action_transport.py`: Safe request acknowledgements and retries.
- `game_component/`: Canvas drawing, controls, music and browser saves.
- `tests/`: Rules, saves, interactions and browser-rule parity tests.

Local saves live in `data/team-progress.sqlite3` and stay out of Git. Use `TEAM_PLOT_TWIST_DB` for an alternative database. Browser saves and music preferences use team-specific keys. No player saves are included in the source package.

Music credits and asset details are in [static/music/README.md](static/music/README.md).
