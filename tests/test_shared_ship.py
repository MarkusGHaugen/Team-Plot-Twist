"""Multiplayer: one shared ship, personal bodies, and capture back to the cell."""
import json
from dataclasses import asdict, replace

import logic as L
import shared_ship as S
from db import connect_db, load_game, new_game, _write_game
from logic import Position, initial_state, story_progress, state_from_backup


def outside(**changes):
    return replace(initial_state(), has_key=True, door_open=True, position=Position('hold', 700), **changes)


def story(state, **values):
    return replace(state, story_state=json.dumps({**story_progress(state), **values}))


def test_opening_the_cell_opens_it_for_the_partner_too():
    a0 = initial_state()
    a1 = replace(a0, has_key=True, door_open=True, position=Position('cell', 370))
    b = replace(initial_state(), position=Position('cell', 200), facing='left')
    shared = S.apply_world(b, S.world_changes(a0, a1))
    assert shared.has_key and shared.door_open
    assert shared.position == Position('cell', 200) and shared.facing == 'left'
    assert state_from_backup(asdict(shared)) == shared


def test_personal_parts_stay_with_each_player():
    a0 = outside()
    a1 = replace(a0, hidden_barrel='barrel_hold_a', disguised=True, held_item='cell_key',
                 position=Position('hold', 710), facing='left', capture_phase='active', reading='tools_chest')
    assert S.world_changes(a0, a1) == {}


def test_only_what_changed_is_copied_so_players_do_not_undo_each_other():
    base = outside()
    # The partner already took the lamp; our action (opening the chest) knows nothing about it.
    partner = replace(base, has_lamp=True, lamp_revealed=True)
    ours_before, ours_after = base, replace(base, chest_open=True, has_blue_key=True)
    merged = S.apply_world(partner, S.world_changes(ours_before, ours_after))
    assert merged.chest_open and merged.has_blue_key and merged.has_lamp


def test_story_items_and_coins_are_shared_but_crouching_and_health_are_not():
    a0 = story(outside(), voyage={'coins': 0, 'claimed': [], 'paid': [], 'armed': False, 'duck': False,
                                  'hp': 2, 'shots': [], 'next_fire': {}})
    v = story_progress(a0)['voyage']
    a1 = story(a0, items=['crowbar'], inspected=['tools_chest'],
               voyage={**v, 'coins': 2, 'claimed': ['coins_hold'], 'duck': True, 'hp': 1})
    b = story(outside(), voyage={**v, 'hp': 2})
    merged = story_progress(S.apply_world(b, S.world_changes(a0, a1)))
    assert merged['items'] == ['crowbar'] and merged['inspected'] == ['tools_chest']
    assert merged['voyage']['coins'] == 2 and merged['voyage']['claimed'] == ['coins_hold']
    assert merged['voyage']['hp'] == 2 and not merged['voyage'].get('duck')


def test_removed_keys_are_removed_for_the_partner():
    a0 = story(outside(), voyage={'feast': {'x': 1}, 'coins': 0})
    a1 = story(outside(), voyage={'coins': 0})
    b = story(outside(), voyage={'feast': {'x': 1}, 'coins': 0})
    assert 'feast' not in story_progress(S.apply_world(b, S.world_changes(a0, a1)))['voyage']


def test_a_partner_cannot_keep_holding_an_item_the_team_lost():
    a0 = outside(has_lamp=True, lamp_revealed=True)
    a1 = replace(a0, has_lamp=False)
    b = replace(a0, held_item='lamp', lamp_lit=True)
    merged = S.apply_world(b, S.world_changes(a0, a1))
    assert merged.held_item == 'none' and not merged.lamp_lit


def test_an_ending_ends_the_game_for_both():
    a0 = outside()
    b = replace(outside(), reading='tools_chest', paused_at_ms=5)
    merged = S.apply_world(b, S.world_changes(a0, replace(a0, ending='crate')))
    assert merged.ending == 'crate' and not merged.reading and merged.paused_at_ms == 0


def test_caught_player_goes_back_to_the_locked_cell_and_the_crew_search_30_seconds():
    before = story(outside(disguised=True, held_item='cell_key', capture_phase='active', capture_guard='patrol',
                           capture_guard_zone='hold', capture_guard_value=720.),
                   items=['crowbar'], voyage={'coins': 1, 'claimed': ['coins_hold'], 'duck': True})
    partner_seen = Position('mid', 700)
    jailed = S.jailed(before, 10., 50_000, partner_seen)
    assert jailed.position == initial_state().position and jailed.capture_phase == 'none'
    assert not jailed.door_open and jailed.has_key, 'the door is locked; the team keeps its key'
    assert not jailed.disguised and jailed.held_item == 'none'
    assert jailed.alert_started_ms == 50_000 and jailed.alert_until_ms == 50_000 + S.SEARCH_MS
    paths = json.loads(jailed.alert_paths)
    assert any([700.0, 365.0] in path for path in paths.values()), 'the search starts where the partner was seen'
    assert story_progress(jailed)['items'] == ['crowbar'] and story_progress(jailed)['voyage']['coins'] == 1
    assert not story_progress(jailed)['voyage'].get('duck'), 'the caught player stands up again'
    assert state_from_backup(asdict(jailed)) is not None


def test_the_partner_sees_the_locked_door_and_the_search():
    before = outside(capture_phase='active', capture_guard='patrol', capture_guard_zone='hold', capture_guard_value=720.)
    jailed = S.jailed(before, 10., 50_000, Position('mid', 700))
    partner = replace(outside(), position=Position('mid', 700))
    merged = S.apply_world(partner, S.world_changes(before, jailed))
    assert not merged.door_open and merged.alert_until_ms == 50_000 + S.SEARCH_MS
    assert merged.position == Position('mid', 700) and merged.capture_phase == 'none'


def test_reading_never_pauses_the_shared_ship_and_closing_adds_no_time():
    letter = L.STORY_POINTS['opening_letter']
    s = replace(initial_state(), position=Position(letter['zone'], letter['x']))
    opened = L.story_action(s, 'inspect', 'opening_letter', 10_000).state
    assert opened.reading and opened.paused_at_ms
    unpaused = S.unpaused(s, opened)
    assert unpaused.paused_at_ms == 0
    closed = L.story_action(unpaused, 'close_reading', '', 99_000).state
    assert closed.paused_total_ms == s.paused_total_ms


def test_rooms_join_share_and_restart(tmp_path):
    with connect_db(tmp_path / 'room.sqlite3') as conn:
        info = S.join(conn, 'ABC234', 'a' * 32, 1_000)
        assert info == {'epoch_ms': 1_000, 'generation': 0, 'version': 0}
        a0 = load_game(conn, 'a' * 32)
        a1 = replace(a0, has_key=True, door_open=True)
        _write_game(conn, a1, 'a' * 32)
        # A newcomer starts in the cell, on the ship as it is now.
        assert S.join(conn, 'ABC234', 'b' * 32, 9_000)['epoch_ms'] == 1_000
        b = load_game(conn, 'b' * 32)
        assert b.door_open and b.has_key and b.position == initial_state().position
        a2 = replace(a1, chest_open=True, has_blue_key=True)
        _write_game(conn, a2, 'a' * 32)
        assert S.share(conn, 'ABC234', 'a' * 32, a1, a2)
        assert load_game(conn, 'b' * 32).chest_open
        assert S.room_info(conn, 'ABC234')['version'] == 1
        assert not S.share(conn, 'ABC234', 'a' * 32, a2, replace(a2, position=Position('hold', 650)))
        S.restart(conn, 'ABC234', 20_000)
        assert load_game(conn, 'b' * 32) == initial_state() == load_game(conn, 'a' * 32)
        assert S.room_info(conn, 'ABC234') == {'epoch_ms': 20_000, 'generation': 1, 'version': 2}
        assert S.members(conn, 'ABC234') == ['a' * 32, 'b' * 32]


def test_server_and_browser_place_the_searching_crew_alike_for_30_seconds():
    import math
    import pytest
    from test_canvas_rules import canvas, NODE
    if NODE is None:
        pytest.skip('Node runs the Canvas rules')
    before = outside(capture_phase='active', capture_guard='patrol', capture_guard_zone='hold', capture_guard_value=720.)
    s = S.jailed(before, 10., 50_000, Position('mid', 700))
    times = [50_000, 57_000, 66_000, 71_000, 79_500]
    kinds = [k for k in json.loads(s.alert_paths)]
    pose = lambda k, t: L.search_pose_at(s, k, t)
    expected = {str(t): {k: [pose(k, t).x, pose(k, t).y] for k in kinds} for t in times}
    data = {**asdict(s), 'story': story_progress(s), 'rules': L.MAP_CONFIG}
    actual = canvas(r'''(()=>{const out={};for(const t of input.times){const d={...input.d,paused_at_ms:t,paused_total_ms:0};
      out[t]={};for(const k of input.kinds){const p=searchPose(d,k);out[t][k]=[p.x,p.y];}}return out;})()''',
                    {'d': data, 'times': times, 'kinds': kinds})
    for t in map(str, times):
        for k in kinds:
            assert math.dist(expected[t][k], actual[t][k]) < .05, (t, k, expected[t][k], actual[t][k])
