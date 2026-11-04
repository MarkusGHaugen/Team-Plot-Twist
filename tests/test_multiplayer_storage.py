import sqlite3

from db import apply_action, claim_legacy, connect_db, load_game, new_game, restore_game
from logic import Position, guard_time, state_from_backup


def test_players_have_independent_saves_and_resets(tmp_path):
    with connect_db(tmp_path / "players.sqlite3") as conn:
        new_game(conn, "player-a")
        new_game(conn, "player-b")
        moment = guard_time("hold_out", 0.05)
        result = apply_action(conn, "steal", Position("cell", 374), moment, "player-a")
        assert result.accepted
        result = apply_action(conn, "open", Position("cell", 374), moment, "player-a")
        assert result.accepted
        assert not load_game(conn, "player-b").has_key
        assert not load_game(conn, "player-b").door_open
        new_game(conn, "player-b")
        assert load_game(conn, "player-a").has_key
        assert load_game(conn, "player-a").door_open


def test_browser_backup_restores_only_when_server_save_is_missing(tmp_path):
    payload = {
        "position": {"zone": "kitchen", "value": 1120},
        "has_key": True,
        "door_open": True,
        "reached_kitchen": True,
    }
    state = state_from_backup(payload)
    assert state is not None
    db_path = tmp_path / "players.sqlite3"
    with connect_db(db_path) as conn:
        assert restore_game(conn, state, "player-a")
        assert not restore_game(conn, state, "player-a")
        assert load_game(conn, "player-b") is None

    with connect_db(db_path) as conn:
        assert load_game(conn, "player-a") == state
        new_game(conn, "player-a")
        assert not restore_game(conn, state, "player-a")
        assert not load_game(conn, "player-a").has_key


def test_invalid_browser_backups_are_rejected():
    valid = {
        "position": {"zone": "cell", "value": 374},
        "has_key": False,
        "door_open": False,
        "reached_kitchen": False,
    }
    assert state_from_backup(valid) is not None
    assert state_from_backup({**valid, "position": {"zone": "kitchen", "value": 1100}}) is None
    assert state_from_backup({**valid, "door_open": True}) is None
    assert state_from_backup({**valid, "has_key": "yes"}) is None
    assert state_from_backup({**valid, "position": {"zone": "cell", "value": float("nan")}}) is None


def test_old_single_player_database_is_migrated_and_claimed(tmp_path):
    db_path = tmp_path / "old.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE progress (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                zone TEXT NOT NULL, position_value REAL NOT NULL,
                has_key INTEGER NOT NULL, door_open INTEGER NOT NULL,
                reached_kitchen INTEGER NOT NULL
            )"""
        )
        conn.execute("INSERT INTO progress VALUES (1, 'cell', 374, 1, 1, 0)")
    with connect_db(db_path) as conn:
        assert load_game(conn, "local").has_key
        assert claim_legacy(conn, "player-a")
        assert load_game(conn, "local") is None
        assert load_game(conn, "player-a").position == Position("cell", 374)
        assert not claim_legacy(conn, "player-b")
