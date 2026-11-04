"""The new player choices and guard response, written before implementation."""
from dataclasses import asdict, replace
import sqlite3

import pytest

from db import apply_action, connect_db, load_game, new_game, restore_game
from logic import (BARRELS, CRATES, Position, can_guard_see, capture_paths,
    change_outfit, finish_capture, guard_notices_door, guard_time, initial_state,
    raise_alert, route_points, search_crate, select_item, shoot_guard,
    start_capture, state_from_backup, toggle_barrel, toggle_wardrobe,
    with_position, take_lamp)


def free(**kwargs):
    return replace(initial_state(), has_key=True, door_open=True, **kwargs)


def test_every_round_barrel_hides_and_releases_without_moving():
    for barrel_id, zone, x in BARRELS:
        state = free(position=Position(zone, x + 20))
        hidden = toggle_barrel(state)
        assert hidden.accepted and hidden.state.hidden_barrel == barrel_id
        assert hidden.state.position == Position(zone, x)
        assert with_position(hidden.state, Position(zone, x + 10)) is None
        assert not can_guard_see(hidden.state, guard_time('hold_out', .30))
        exited = toggle_barrel(hidden.state)
        assert exited.accepted and not exited.state.hidden_barrel
        assert exited.state.position == Position(zone, x)
    assert not toggle_barrel(free(position=Position('hold', 500))).accepted


def test_every_visible_crate_is_searchable_with_lamp_only_in_right_hold_crate():
    for name, zone, x in CRATES:
        state = free(position=Position(zone, x))
        result = search_crate(state)
        assert result.accepted
        if name == 'crate_hold_b':
            assert result.state.lamp_revealed and not result.state.has_lamp
            taken = take_lamp(result.state)
            assert taken.accepted and taken.state.held_item == 'lamp'
            assert not search_crate(taken.state).accepted
        else:
            assert result.state == state and 'empty' in result.message.lower()
    assert not search_crate(free(position=Position('cabin', 300))).accepted


def test_wardrobe_outfit_and_inventory_choice():
    state = free(position=Position('cabin', 460), has_blue_key=True,
                 chest_open=True, has_pistol=True, held_item='pistol')
    assert not change_outfit(state).accepted
    opened = toggle_wardrobe(state)
    assert opened.accepted and opened.state.wardrobe_open
    disguised = change_outfit(opened.state)
    assert disguised.accepted and disguised.state.disguised
    assert not can_guard_see(disguised.state, guard_time('dining_out', .99))
    assert change_outfit(disguised.state).state.disguised is False
    selected = select_item(disguised.state, 'blue_key')
    assert selected.accepted and selected.state.held_item == 'blue_key'
    assert not shoot_guard(selected.state, guard_time('hold_out', .35)).accepted
    assert select_item(selected.state, 'pistol').state.held_item == 'pistol'
    assert not select_item(selected.state, 'unknown').accepted
    assert not select_item(replace(state, has_pistol=False), 'pistol').accepted


def test_guard_sees_only_forward_same_height_unblocked_and_without_disguise():
    moment = guard_time('hold_out', .3)
    from logic import guard_pose
    guard_x = guard_pose(moment).x
    visible = free(position=Position('hold', guard_x + 90))
    assert can_guard_see(visible, moment)
    assert not can_guard_see(replace(visible, position=Position('hold', guard_x - 90)), moment)
    assert not can_guard_see(replace(visible, position=Position('mid', 700)), moment)
    assert not can_guard_see(replace(visible, position=Position('cell', 374)), moment)
    assert not can_guard_see(replace(visible, disguised=True), moment)
    reverse = guard_time('hold_return', .3)
    back_x = guard_pose(reverse).x
    assert can_guard_see(replace(visible, position=Position('chest_room', back_x - 80)), reverse)
    assert not can_guard_see(replace(visible, position=Position('chest_room', back_x + 80)), reverse)
    assert not can_guard_see(replace(visible, patrol_alive=False, patrol_corpse_x=guard_x,
                                     patrol_corpse_y=500), moment)


def test_door_alarm_is_once_per_opening_and_expires_after_twenty_seconds():
    state = free(position=Position('hold', 700))
    moment = guard_time('cell_return', .5)
    assert guard_notices_door(state, moment)
    alarm = raise_alert(state, moment, 1_000_000)
    assert alarm.accepted and alarm.state.door_alerted
    assert alarm.state.alert_started_ms == 1_000_000
    assert alarm.state.alert_until_ms == 1_020_000
    assert not guard_notices_door(alarm.state, moment)
    assert not raise_alert(alarm.state, moment, 1_021_000).accepted
    closed = replace(alarm.state, position=Position('hold', 425))
    from logic import open_door
    shut = open_door(closed)
    assert shut.accepted and not shut.state.door_alerted
    assert not guard_notices_door(replace(shut.state, door_open=True,
                                         patrol_alive=False), moment)


def test_capture_route_is_continuous_and_final_reset_is_full_run(tmp_path):
    moment = guard_time('hold_out', .3)
    from logic import guard_pose
    p = guard_pose(moment)
    state = free(position=Position('hold', p.x + 90), has_blue_key=True,
                 chest_open=True, has_pistol=True, held_item='pistol',
                 wardrobe_open=True, sleeper_alive=False)
    started = start_capture(state, moment)
    assert started.accepted and started.state.capture_phase == 'active'
    approach, escort = capture_paths(started.state)
    assert approach[0] == pytest.approx((p.x, p.y))
    assert approach[-1] == pytest.approx((state.position.value, 500))
    assert escort[0] == approach[-1]
    assert escort[-1] == (230., 500.)
    for path in (approach, escort):
        for a,b in zip(path,path[1:]):
            assert abs(a[0]-b[0]) <= 900
            assert (a[1] == b[1] or (abs(a[0]-b[0]) / abs(a[1]-b[1])) == pytest.approx(100/135))
    from_kitchen = route_points(Position('kitchen',1210),Position('cell',230))
    assert from_kitchen == [(1210.,245.),(1040.,245.),(920.,365.),
                            (540.,365.),(440.,500.),(230.,500.)]
    reset = finish_capture(started.state)
    assert reset.accepted and reset.state == initial_state()
    assert not finish_capture(reset.state).accepted
    with connect_db(tmp_path/'capture.sqlite3') as conn:
        assert restore_game(conn,started.state,'browser')
        assert apply_action(conn,'capture_complete',started.state.position,0,'browser').accepted
        assert load_game(conn,'browser') == initial_state()
    with connect_db(tmp_path/'capture.sqlite3') as conn:
        assert load_game(conn,'browser') == initial_state()


def test_new_fields_persist_migrate_and_rejected_actions_do_not_write(tmp_path):
    old_path = tmp_path / 'old.sqlite3'
    with sqlite3.connect(old_path) as conn:
        conn.execute('''CREATE TABLE progress (player_id TEXT PRIMARY KEY, zone TEXT NOT NULL,
          position_value REAL NOT NULL, has_key INTEGER NOT NULL, door_open INTEGER NOT NULL,
          reached_kitchen INTEGER NOT NULL, has_blue_key INTEGER NOT NULL,
          chest_open INTEGER NOT NULL, has_pistol INTEGER NOT NULL, in_hammock INTEGER NOT NULL,
          patrol_alive INTEGER NOT NULL, sleeper_alive INTEGER NOT NULL,
          patrol_corpse_x REAL, patrol_corpse_y REAL, facing TEXT NOT NULL)''')
        conn.execute("INSERT INTO progress VALUES ('friend','chest_room',1120,1,1,0,1,1,1,0,1,1,NULL,NULL,'left')")
    with connect_db(old_path) as conn:
        old = load_game(conn,'friend')
        assert old.has_pistol and old.held_item == 'pistol'
        before = conn.total_changes
        assert not apply_action(conn,'select_item',Position('chest_room',1120),0,'friend',item='bogus').accepted
        assert conn.total_changes == before
        assert apply_action(conn,'select_item',Position('chest_room',1120),0,'friend',item='blue_key').accepted
        assert load_game(conn,'friend').held_item == 'blue_key'
    with connect_db(old_path) as conn:
        assert load_game(conn,'friend').held_item == 'blue_key'
    legacy = {'position':{'zone':'cell','value':374},'has_key':True,
              'door_open':True,'reached_kitchen':False}
    assert state_from_backup(legacy).held_item == 'cell_key'
    full = replace(free(position=Position('hold',710)),hidden_barrel='barrel_hold_a',
                   has_blue_key=True,held_item='blue_key',door_alerted=True,
                   alert_started_ms=100,alert_until_ms=20100)
    assert state_from_backup(asdict(full)) == full
    with connect_db(tmp_path/'fresh.sqlite3') as conn:
        assert restore_game(conn,full,'browser')
        assert load_game(conn,'browser') == full
        new_game(conn,'browser')
        assert load_game(conn,'browser') == initial_state()
