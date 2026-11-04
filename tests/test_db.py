import sqlite3

from db import apply_action, connect_db, load_game, new_game, save_position
from logic import Position, guard_time


def test_rejected_actions_do_not_write_progress(tmp_path):
    db_path = tmp_path / "game.sqlite3"
    with connect_db(db_path) as conn:
        new_game(conn)
        initial = load_game(conn)
        before = conn.total_changes
        result = apply_action(conn, "steal", Position("cell", 374), guard_time("lower_down", 0.3))
        assert not result.accepted
        assert conn.total_changes == before
        assert load_game(conn) == initial

        result = apply_action(conn, "open", Position("cell", 374), 0)
        assert not result.accepted
        assert conn.total_changes == before
        assert load_game(conn) == initial

        assert not save_position(conn, Position("hold", 450))
        assert conn.total_changes == before


def test_success_duplicate_persistence_and_new_game(tmp_path):
    db_path = tmp_path / "game.sqlite3"
    with connect_db(db_path) as conn:
        new_game(conn)
        moment = guard_time("hold_out", 0.05)
        got_key = apply_action(conn, "steal", Position("cell", 374), moment)
        assert got_key.accepted
        after_key = conn.total_changes
        duplicate = apply_action(conn, "steal", Position("cell", 374), moment)
        assert not duplicate.accepted
        assert conn.total_changes == after_key
        opened = apply_action(conn, "open", Position("cell", 374), moment)
        assert opened.accepted
        assert opened.state.has_key and opened.state.door_open
        for position in (Position("hold", 440), Position("lower_stair", .5),
                         Position("mid", 540), Position("dining", 920),
                         Position("upper_stair", .5), Position("kitchen", 1120)):
            assert save_position(conn, position)

    # A fresh connection represents a full app restart, not the same session.
    with connect_db(db_path) as conn:
        restored = load_game(conn)
        assert restored.has_key and restored.door_open
        assert restored.position == Position("kitchen", 1120)
        assert restored.reached_kitchen
        new_game(conn)
        reset = load_game(conn)
        assert not reset.has_key and not reset.door_open
        assert reset.position.zone == "cell"
        assert not reset.reached_kitchen


def test_missing_game_is_none(tmp_path):
    with connect_db(tmp_path / "empty.sqlite3") as conn:
        assert load_game(conn) is None
