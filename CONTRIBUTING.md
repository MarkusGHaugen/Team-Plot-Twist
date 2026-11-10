# Contributing to Team Plot Twist

## Branches and reviews

Use one branch per change: `feature/short-description` or `fix/short-description`. Update `main` before creating a branch. Tell the group which files you plan to edit; `game_component/game.js` and `logic.py` are common conflict points. Keep changes small, test them, and open a pull request. Another group member should review before merge.

The server decides inventory, damage, endings and save validation. Canvas draws and requests actions. A visual change must not silently bypass a game rule. Add useful tests when changing rules or save formats, and keep older saves compatible where possible.

```bash
uv run pytest -q
```

Do not commit player databases, virtual environments, credentials, local logs or exported archives. Review the file list in GitHub Desktop before each commit. Audio assets keep their creator credits; do not assume they have a general redistribution licence.

## Versions

The initial group release is **1.0.0**. Use **1.0.1** for a small fix, **1.1.0** for a new feature, and discuss a major version change before breaking save compatibility.

Before a release:

1. Update `version` in `pyproject.toml`.
2. Run `uv lock` so `uv.lock` records the same project version.
3. Add the changes and validation to `CHANGELOG.md`.
4. Run tests and play through the affected route.
5. Merge the reviewed release, then tag it, for example `v1.0.1`.

To make a source ZIP from the current tracked files:

```bash
uv run python scripts/package_release.py
```

The file appears in `dist/`. For an extracted ZIP without Git metadata, the script uses the included release file manifest; new files should be added through a proper Git clone before exporting a later release.

## Deployment

Use this repository for a separate Streamlit app if the group wants an online version. Keep `app.py` as the entry point, Python 3.12, `uv.lock`, and static serving enabled. Do not reuse another project's database path, deployment settings or secrets. A deployment is a separate step from merging and requires the owner's coordination.

The online game is at https://team-plot-twist.streamlit.app and updates itself from `main`.

## Keeping online play fast

Online, every request to the server is a round trip of roughly half a second, while on your own machine it is almost instant. Keep this in mind:

- Each `setTriggerValue`/`setStateValue` in `game.js` runs `app.py` on the server. Do not add timers that call the server regularly; compute what you can in the Canvas and only ask the server when a rule must decide. `crewTickNeeded` shows the pattern.
- Avoid `st.rerun()` in the play loop. Apply actions in a widget callback, as `apply_game_action` does, so one run is enough.
- Everything passed to the component's `data` is sent on every run. Keep it small, and keep large fixed code or text out of it. `game.js` is served from `static/build/` for that reason.
- Start animations in the Canvas at once, then let the server confirm.
- Test new interactions in the online version as well, not only locally.
