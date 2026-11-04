from dataclasses import asdict, replace
import sqlite3

import pytest

from db import apply_action, connect_db, load_game, new_game, restore_game
from logic import (
    GUARD_CYCLE_SECONDS,
    GUARD_SEGMENTS,
    Position,
    advance_player,
    guard_pose,
    guard_time,
    initial_state,
    key_prompt,
    open_door,
    position_xy,
    shoot_guard,
    state_from_backup,
    steal_blue_key,
    take_pistol,
    toggle_hammock,
    unlock_chest,
    with_position,
)


def unlocked():
    return replace(initial_state(), has_key=True, door_open=True)


def walk(start, horizontal=0, vertical=0, seconds=3):
    p = start
    for _ in range(int(seconds * 10)):
        p = advance_player(p, True, horizontal, vertical, 0.1)
    return p


def test_all_drawn_rooms_are_connected_by_walking_and_stairs():
    p = walk(Position("cell", 374), 1, seconds=.5)
    assert p.zone == "hold"
    p = walk(p, 1)
    assert p.zone == "chest_room"
    p = walk(p, -1)
    assert p.zone == "hold"
    p = walk(Position("hold", 440), vertical=1)
    assert p.zone == "mid"
    p = walk(p, -1)
    assert p.zone == "cabin"
    p = walk(p, 1)
    assert p.zone == "mid"
    p = walk(p, 1)
    assert p.zone == "dining"
    p = walk(Position("dining", 920), vertical=1)
    assert p.zone == "kitchen"
    p = walk(p, -1)
    assert p.zone == "upper_deck"
    p = walk(p, 1)
    assert p.zone == "kitchen"
    assert position_xy(Position("cabin", 300))[1] == 365
    assert position_xy(Position("chest_room", 1200))[1] == 500


def test_patrol_repeats_full_route_without_teleporting():
    names = [segment.name for segment in GUARD_SEGMENTS]
    assert names.index("cell_pass") < names.index("hold_out") < names.index("hold_return")
    assert names.index("hold_return") < names.index("dining_return")
    assert guard_pose(guard_time("hold_out", .98)).x > 1200
    assert guard_pose(guard_time("dining_return", .5)).y == pytest.approx(365)
    for a, b in zip(GUARD_SEGMENTS, GUARD_SEGMENTS[1:]):
        assert (a.x2, a.y2) == pytest.approx((b.x1, b.y1))
    assert (GUARD_SEGMENTS[-1].x2, GUARD_SEGMENTS[-1].y2) == pytest.approx(
        (GUARD_SEGMENTS[0].x1, GUARD_SEGMENTS[0].y1)
    )
    assert guard_pose(0).x == pytest.approx(guard_pose(GUARD_CYCLE_SECONDS).x)


def test_cell_key_window_is_three_sprite_widths_both_directions():
    state = replace(initial_state(), position=Position("cell", 374))
    for segment in ("hold_out", "hold_return"):
        near = guard_time(segment, .04)
        far = guard_time(segment, .45)
        if segment == "hold_return":
            near, far = guard_time(segment, .96), guard_time(segment, .55)
        assert key_prompt(state, near)
        assert not key_prompt(state, far)
    assert not key_prompt(state, guard_time("lower_up", .5))
    assert not key_prompt(state, guard_time("lower_down", .5))


def test_cell_door_toggles_from_both_sides_but_not_on_a_character():
    state = replace(initial_state(), has_key=True, position=Position("cell", 374))
    opened = open_door(state)
    assert opened.accepted and opened.state.door_open
    across = replace(opened.state, position=Position("hold", 425))
    closed = open_door(across)
    assert closed.accepted and not closed.state.door_open
    assert closed.state.has_key
    assert advance_player(Position("hold", 425), False, -1, 0, 1).value >= 410
    assert not open_door(replace(opened.state, position=Position("hold", 397))).accepted
    assert with_position(closed.state, Position("lower_stair", .5)) is not None
    assert with_position(closed.state, Position("cabin", 300)) is not None


def test_sleeper_blue_key_hammock_and_chest_pistol_flow():
    cabin = replace(unlocked(), position=Position("cabin", 300))
    blue = steal_blue_key(cabin)
    assert blue.accepted and blue.state.has_blue_key
    assert not steal_blue_key(blue.state).accepted
    asleep = toggle_hammock(blue.state)
    assert asleep.accepted and asleep.state.in_hammock
    assert advance_player(asleep.state.position, True, 1, 0, 1) == asleep.state.position
    awake = toggle_hammock(asleep.state)
    assert awake.accepted and not awake.state.in_hammock
    chest = replace(awake.state, position=Position("chest_room", 1120))
    assert not take_pistol(chest).accepted
    opened = unlock_chest(chest)
    assert opened.accepted and opened.state.chest_open and opened.state.has_blue_key
    pistol = take_pistol(opened.state)
    assert pistol.accepted and pistol.state.has_pistol
    assert not take_pistol(pistol.state).accepted


def test_shot_direction_height_wall_and_persistent_corpses():
    base = replace(unlocked(), has_blue_key=True, chest_open=True, has_pistol=True,
                   held_item="pistol")
    near_patrol = replace(base, position=Position("hold", 650), facing="right")
    moment = guard_time("hold_out", .35)
    hit = shoot_guard(near_patrol, moment)
    assert hit.accepted and not hit.state.patrol_alive
    assert hit.state.patrol_corpse_y == 500
    assert not shoot_guard(hit.state, moment).state.patrol_alive
    assert shoot_guard(replace(near_patrol, facing="left"), moment).state.patrol_alive
    assert shoot_guard(replace(base, position=Position("cabin", 210), facing="right"), moment).state.sleeper_alive is False
    assert shoot_guard(replace(base, position=Position("kitchen", 1100), facing="left"), moment).state.patrol_alive
    blocked = replace(base, door_open=False, position=Position("cell", 374), facing="right")
    assert shoot_guard(blocked, guard_time("cell_pass", .5)).state.patrol_alive


def test_old_and_new_saves_migrate_without_losing_existing_progress(tmp_path):
    path = tmp_path / "old.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE progress (player_id TEXT PRIMARY KEY, zone TEXT NOT NULL,
            position_value REAL NOT NULL, has_key INTEGER NOT NULL, door_open INTEGER NOT NULL,
            reached_kitchen INTEGER NOT NULL)""")
        conn.execute("INSERT INTO progress VALUES ('friend', 'kitchen', 1120, 1, 1, 1)")
    with connect_db(path) as conn:
        old = load_game(conn, "friend")
        assert old.position == Position("kitchen", 1120) and old.has_key
        assert old.patrol_alive and old.sleeper_alive
        assert not old.has_blue_key and not old.has_pistol
        new_game(conn, "other")
        assert load_game(conn, "friend") == old
    legacy_backup = state_from_backup({"position": {"zone": "cell", "value": 374},
        "has_key": True, "door_open": True, "reached_kitchen": False})
    assert legacy_backup is not None and not legacy_backup.has_blue_key
    with connect_db(tmp_path / "restore.sqlite3") as conn:
        assert restore_game(conn, legacy_backup, "friend")


def test_action_persistence_and_rejections_for_new_items(tmp_path):
    path = tmp_path / "actions.sqlite3"
    with connect_db(path) as conn:
        new_game(conn, "one")
        before = conn.total_changes
        denied = apply_action(conn, "take_pistol", Position("cell", 230), 0, "one")
        assert not denied.accepted and conn.total_changes == before
        moment = guard_time("hold_out", .04)
        assert apply_action(conn, "steal", Position("cell", 374), moment, "one").accepted
        assert apply_action(conn, "open", Position("cell", 374), moment, "one").accepted
        assert apply_action(conn, "steal_blue", Position("cabin", 300), moment, "one").accepted
        assert apply_action(conn, "unlock_chest", Position("chest_room", 1120), moment, "one").accepted
        assert apply_action(conn, "take_pistol", Position("chest_room", 1120), moment, "one").accepted
        assert not load_game(conn, "other")
    with connect_db(path) as conn:
        state = load_game(conn, "one")
        assert state.has_key and state.has_blue_key and state.has_pistol and state.chest_open
        new_game(conn, "one")
        assert not load_game(conn, "one").has_blue_key


def test_new_browser_backup_recovers_all_progress_after_server_database_reset(tmp_path):
    original = replace(unlocked(), position=Position("chest_room", 1120),
        has_blue_key=True, chest_open=True, has_pistol=True,
        patrol_alive=False, sleeper_alive=False,
        patrol_corpse_x=433.0, patrol_corpse_y=500.0, facing="left")
    payload = asdict(original)
    restored = state_from_backup(payload)
    assert restored == original
    with connect_db(tmp_path / "fresh.sqlite3") as conn:
        assert restore_game(conn, restored, "browser-one")
        assert not restore_game(conn, restored, "browser-one")
        assert load_game(conn, "browser-one") == original
        assert load_game(conn, "browser-two") is None


def test_rejected_closed_door_and_wrong_chest_key_leave_database_unchanged(tmp_path):
    with connect_db(tmp_path / "reject.sqlite3") as conn:
        new_game(conn, "one")
        before = conn.total_changes
        assert not apply_action(conn, "unlock_chest", Position("chest_room", 1120), 0, "one").accepted
        assert not apply_action(conn, "open", Position("cell", 374), 0, "one").accepted
        assert conn.total_changes == before
        assert load_game(conn, "one") == initial_state()
