# Team Plot Twist

## Layout
- `app.py`: Streamlit UI and component protocol.
- `logic.py`, `voyage.py`, `escort.py`: Authoritative game rules and movement.
- `content.py`: Authored text and item definitions; `db.py`: SQLite storage/migration.
- `game_component/`: Canvas, controls, music, browser identity and backup.

Run `uv sync --locked`, `uv run streamlit run app.py --server.port 8535`, and `uv run pytest -q`.
Use `TEAM_PLOT_TWIST_DB` for an isolated test database.

## Collaboration
- Work on feature branches. Preserve tests and explain intentional expectation changes.
- Write acceptance notes and meaningful tests before new gameplay workflows.
- Keep game rules and save validation on the server. Rejected or ordinary completed-game actions must not alter saves.
- Keep team-specific browser keys, component names and database settings independent.
- Do not add private predecessor history, personal notes, databases or secrets to this repository.
- Run appropriate tests and verify visible changes in a browser.
- Do not deploy merely to verify a local change. Coordinate releases with the group owner.
