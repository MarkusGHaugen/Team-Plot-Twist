"""Sleeping pills: a drugged meal for the whole crew, or a fake death in the cell."""
import json, math
import re
import sqlite3
from contextlib import closing
from dataclasses import asdict, replace
import pytest
import logic as L
from logic import Position, initial_state, story_action, story_progress, state_from_backup, guard_pose_at, can_guard_see
import feast
from feast import drug_stew, SERVE_DELAY_MS, SLEEP_MS, SEATS
from voyage import voyage_action, watch_pose
from test_canvas_rules import canvas, NODE

CREW = feast.ORDER


def free(zone='kitchen', x=1200., items=('sleeping_pills',), watch=True, **changes):
    voyage = {'watch_start': 0} if watch else {}
    s = replace(initial_state(), has_key=True, door_open=True, reached_kitchen=True,
                position=Position(zone, x), story_state=json.dumps({'items': list(items), 'voyage': voyage}), **changes)
    return s


def accepted(r):
    assert r.accepted, r.message
    return r.state


def drugged(now=10_000, elapsed=10., **kw):
    return accepted(drug_stew(free(**kw), elapsed, now))


def poses(s, now, elapsed0=10., now0=10_000):
    return {k: guard_pose_at(s, k, elapsed0 + (now - now0) / 1000, now) for k in CREW}


def test_pills_are_taken_from_the_sea_chest_in_the_cabin():
    p = L.STORY_POINTS['pill_chest']
    s = free(p['zone'], p['x'], items=())
    s = accepted(story_action(s, 'inspect', 'pill_chest', 1000))
    s = accepted(story_action(s, 'take', 'pill_chest', 1100))
    assert 'sleeping_pills' in story_progress(s)['items']
    assert state_from_backup(asdict(s)) is not None


def test_stew_needs_pills_the_pot_a_living_cook_and_calm():
    assert not drug_stew(free(items=()), 0, 1000).accepted
    assert not drug_stew(free(x=1300.), 0, 1000).accepted
    assert not drug_stew(free(dining_alive=False, dining_corpse_x=1.0, dining_corpse_y=365.), 0, 1000).accepted
    assert not drug_stew(free(alert_started_ms=500, alert_until_ms=500 + L.ALERT_DURATION_MS), 0, 1000).accepted
    s = drugged()
    assert not drug_stew(s, 0, 20_000).accepted        # once per game
    assert state_from_backup(asdict(s)) is not None


def test_cook_serves_after_five_seconds_then_everyone_eats_sleeps_and_wakes():
    s = drugged()
    f = story_progress(s)['voyage']['feast']
    before = poses(s, 10_000 + SERVE_DELAY_MS - 1)
    assert not any(p.segment.startswith('feast_') for p in before.values())
    assert guard_pose_at(s, 'dining', 15., f['gather'] + 100).segment == 'feast_serve'
    # The cook fetches the pot from the galley before sitting down.
    cook = f['paths']['dining']
    assert [1200.0, 245.0] in cook and cook[-1] == [SEATS['dining'], 365.0]
    first_sleep = min(f['sleep'].values())
    eating = poses(s, first_sleep - 1)
    assert all(p.segment == 'feast_eat' and (p.x, p.y) == (SEATS[k], 365.) for k, p in eating.items())
    last_sleep = max(f['sleep'].values())
    asleep = poses(s, last_sleep + 1)
    assert all(p.segment == 'feast_sleep' for p in asleep.values())
    assert feast.crew_asleep(s, last_sleep + 1) and not feast.crew_asleep(s, first_sleep - 1)
    # Nobody notices you while they sleep, even standing right in front of them.
    near = replace(s, position=Position('dining', SEATS['patrol'] + 40))
    assert not can_guard_see(near, 0, 'patrol', last_sleep + 1)
    # Two minutes later they wake and walk back.
    woke = poses(s, last_sleep + SLEEP_MS + 2000)
    assert not any(p.segment in ('feast_sleep', 'feast_eat') for p in woke.values())
    assert any(p.segment == 'feast_return' for p in woke.values())
    assert first_sleep + SLEEP_MS - last_sleep < SLEEP_MS


def test_after_the_meal_everyone_continues_from_where_they_left():
    s = drugged()
    f = story_progress(s)['voyage']['feast']
    for k in CREW:
        done = feast.back(f, k)
        origin = f['returns'][k][-1]
        just_before = guard_pose_at(s, k, 0, int(done) - 1)
        after = guard_pose_at(s, k, 0, int(done) + 1)
        assert math.dist((just_before.x, just_before.y), origin) < 2, k
        assert math.dist((after.x, after.y), origin) < 3, (k, after)
        assert not after.segment.startswith('feast_'), k


def test_the_helm_wins_only_while_the_whole_crew_sleeps():
    s = drugged()
    f = story_progress(s)['voyage']['feast']
    helm = L.STORY_POINTS['helm']
    at_helm = replace(s, position=Position(helm['zone'], helm['x']))
    last_sleep = max(f['sleep'].values())
    assert not voyage_action(at_helm, 'inspect', 'helm', last_sleep - 1).accepted
    won = voyage_action(at_helm, 'inspect', 'helm', last_sleep + 1)
    assert won.accepted and won.state.ending == 'lullaby'
    assert state_from_backup(asdict(won.state)) is not None
    first_wake = min(f['sleep'].values()) + SLEEP_MS
    assert not voyage_action(at_helm, 'inspect', 'helm', first_wake + 1).accepted


def test_a_gunshot_wakes_the_crew_and_ends_the_meal():
    s = drugged()
    f = story_progress(s)['voyage']['feast']
    now = max(f['sleep'].values()) + 1000
    armed = replace(s, has_pistol=True, chest_open=True, has_blue_key=True, held_item='pistol',
                    position=Position('dining', 900.), facing='left')
    shot = L.shoot_guard(armed, 0, now)
    assert shot.accepted
    v = story_progress(shot.state)['voyage']
    assert 'feast' not in v and v['stew_drugged']
    assert v['watch_start'] == feast.watch_shift(f)          # the watch rotation keeps its pause
    assert not feast.crew_asleep(shot.state, now + 1)
    assert state_from_backup(asdict(shot.state)) is not None


def test_watch_pair_join_the_meal_and_resume_their_rotation():
    s = drugged()
    f = story_progress(s)['voyage']['feast']
    assert f['watch'] and 'cargo' not in f['resume'] and 'sleeper' not in f['resume']
    pose, sleeping = watch_pose(s, 'sleeper', max(f['sleep'].values()) + 1)
    assert pose.segment == 'feast_sleep' and sleeping


def test_swallowing_the_pills_in_the_cell_ends_in_the_castaway_ending():
    p = L.STORY_POINTS['cell_floor']
    cell = free('cell', p['x'])
    assert not story_action(free('cell', p['x'], items=()), 'inspect', 'cell_floor', 1000).accepted
    asked = accepted(story_action(cell, 'inspect', 'cell_floor', 1000))
    assert asked.reading == 'confirm_castaway'
    won = accepted(story_action(asked, 'finish', 'cell_floor', 2000))
    assert won.ending == 'castaway'
    assert state_from_backup(asdict(won)) is not None
    # The floor point does not cover the letter or the door.
    assert p['x'] - p['reach'] > L.STORY_POINTS['opening_letter']['x'] + L.STORY_POINTS['opening_letter']['reach']
    assert p['x'] + p['reach'] < L.CELL_KEY_PLAYER_MIN


@pytest.mark.parametrize('legacy', [False, True], ids=['fresh', 'four-ending-save'])
@pytest.mark.parametrize('ending', ['castaway', 'lullaby'])
def test_sleeping_pill_endings_persist(tmp_path, legacy, ending):
    from db import apply_action, connect_db, load_game, restore_game

    path = tmp_path / 'game.sqlite3'
    if ending == 'castaway':
        floor = L.STORY_POINTS['cell_floor']
        saved = accepted(story_action(free('cell', floor['x']), 'inspect', 'cell_floor', 1000))
        action, point, now = 'story_finish', 'cell_floor', 2000
    else:
        helm = L.STORY_POINTS['helm']
        saved = replace(drugged(), position=Position(helm['zone'], helm['x']))
        now = max(story_progress(saved)['voyage']['feast']['sleep'].values()) + 1
        action, point = 'story_inspect', 'helm'

    if legacy:
        with closing(connect_db(tmp_path / 'schema.sqlite3')) as conn:
            schema = conn.execute("SELECT sql FROM sqlite_master WHERE name='progress'").fetchone()[0]
        schema, matches = re.subn(
            r'CHECK \(ending IN \([^)]*\)\)',
            "CHECK (ending IN ('','takeover','crate','dinghy','command'))",
            schema,
        )
        assert matches == 1
        with closing(sqlite3.connect(path)) as conn:
            conn.execute(schema)
            assert restore_game(conn, saved, 'player')
            assert restore_game(conn, initial_state(), 'other-player')

    with closing(connect_db(path)) as conn:
        if not legacy:
            assert restore_game(conn, saved, 'player')
        assert load_game(conn, 'player') == saved
        result = apply_action(conn, action, saved.position, 0, 'player', item=point, now_ms=now)
        assert result.accepted and result.state.ending == ending

    with closing(connect_db(path)) as conn:
        assert load_game(conn, 'player') == result.state
        if legacy:
            assert load_game(conn, 'other-player') == initial_state()


def test_endings_are_numbered_out_of_six():
    from content import ENDINGS
    assert len(ENDINGS) == 6 and all(e['subtitle'].split(' · ')[0].endswith('of 6') for e in ENDINGS.values())


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas rules')
def test_canvas_draws_the_same_meal_as_the_server():
    s = drugged()
    f = story_progress(s)['voyage']['feast']
    times = sorted({f['gather'] + 50, f['gather'] + 3000, min(f['sleep'].values()) - 5, max(f['sleep'].values()) + 5,
                    min(f['sleep'].values()) + SLEEP_MS + 4000, int(max(feast.back(f, k) for k in CREW)) + 2000})
    expected = {str(t): {k: [round(p.x, 3), round(p.y, 3), p.segment] for k, p in poses(s, t).items()} for t in times}
    d = {**asdict(s), 'story': story_progress(s), 'rules': L.MAP_CONFIG,
         'guard_routes': {k: [asdict(x) for x in r] for k, r in L.GUARD_ROUTES.items()}}
    d['rules'] = {**L.MAP_CONFIG, 'watch_path': L.route_points(Position('cabin', 300), Position('chest_room', 1320))}
    actual = canvas(r'''(()=>{const out={};for(const t of input.times){
      const d={...input.d,paused_at_ms:t,paused_total_ms:0,guard_started_ms:t-(10+(t-10000)/1000)*1000};
      out[t]={};for(const k of input.crew){const p=k==='sleeper'?watchCrew(d,k):guardPose(d,k);out[t][k]=[Math.round(p.x*1000)/1000,Math.round(p.y*1000)/1000,p.name];}}
      return out;})()''', {'d': d, 'times': times, 'crew': list(CREW)})
    for t in map(str, times):
        for k in CREW:
            ex, ac = expected[t][k], actual[t][k]
            assert math.dist(ex[:2], ac[:2]) < .05, (t, k, ex, ac)
            if ex[2].startswith('feast_'):
                assert ac[2] == ex[2], (t, k, ex, ac)


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas rules')
def test_castaway_cutscene_drifts_four_days_and_washes_ashore():
    result = canvas(r'''[1,5,6.2,9,12.6,16,19.5,23,26,27.9].map(t=>castawayMotion(1000,560,t))''', {})
    phases = [m['phase'] for m in result]
    assert phases == ['cell', 'overboard', 'overboard', 'adrift', 'adrift', 'adrift', 'adrift', 'ashore', 'ashore', 'ashore']
    assert [m['day'] for m in result[3:7]] == [1, 2, 3, 4]
    assert result[4]['storm'] > .5 and result[3]['storm'] == 0         # day two is the storm
    final = result[-1]
    assert final['island'] == 1 and final['tip'] == 1 and final['out'] > .9
    assert abs(final['barrel']['y'] - final['shore']) < 1                # the barrel lies on the beach


def test_new_actions_go_through_the_saved_game(tmp_path):
    from db import connect_db, restore_game, apply_action, load_game
    s = free()
    with connect_db(tmp_path / 'pills.sqlite3') as c:
        assert restore_game(c, s, 'p')
        r = apply_action(c, 'drug_stew', s.position, 10., 'p', now_ms=10_000)
        assert r.accepted, r.message
        saved = load_game(c, 'p')
        assert story_progress(saved)['voyage']['feast']['gather'] == 10_000 + SERVE_DELAY_MS
    deck = replace(free('upper_deck', 300.), has_lamp=True, lamp_revealed=True, lamp_lit=True, held_item='lamp')
    with connect_db(tmp_path / 'cannon.sqlite3') as c:
        assert restore_game(c, deck, 'c')
        r = apply_action(c, 'fire_cannon', deck.position, 0., 'c', now_ms=5_000)
        assert r.accepted, r.message
        assert 'cannon_fired' in story_progress(load_game(c, 'c'))['voyage']


def test_meal_plan_never_fails_on_an_off_route_pose_and_fits_the_save():
    import feast as F
    assert F._walkable(1128.07, 343.94).zone in L.STAIRS or F._walkable(1128.07, 343.94).zone in L.FLOORS
    s0 = free(items=['sleeping_pills', 'crowbar', 'rope', 'sail', 'whistle', 'manifest', 'seal'])
    v = {'watch_start': 0, 'coins': 2, 'claimed': ['coins_hold', 'coins_provisions', 'coins_chart', 'coins_crew'],
         'paid': ['cook'], 'cannon_fired': 5}
    p = story_progress(s0)
    p['inspected'] = [k for k in L.STORY_POINTS if L.STORY_POINTS[k]['kind'] != 'telescope']
    p['voyage'] = v
    s0 = replace(s0, story_state=json.dumps(p))
    assert L.valid_story_state(s0.story_state)
    longest = 0
    for t in range(0, 210_000, 3_000):
        r = drug_stew(s0, t / 1000, t + 1000)
        assert r.accepted, r.message
        longest = max(longest, len(r.state.story_state))
        assert L.valid_story_state(r.state.story_state)
    assert longest < 12_000
