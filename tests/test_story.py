"""Acceptance checks for the first complete story, defined before implementation."""
from dataclasses import asdict, replace
import json

import pytest

from logic import (GUARD_ROUTES, Position, initial_state, state_from_backup,
                   story_action, story_progress, game_now_ms)
from db import apply_action, connect_db, load_game, new_game, restore_game, save_position


def free(**changes):
    return replace(initial_state(), has_key=True, door_open=True, **changes)


def act(state, point, kind='inspect', now=1000):
    return story_action(state, kind, point, now)


def close(state, now=2000):
    if not state.reading: return state
    result = story_action(state, 'close_reading', '', now)
    assert result.accepted
    return result.state


def collect(state, point, zone, x):
    state = replace(state, position=Position(zone, x))
    inspected = act(state, point)
    assert inspected.accepted
    state = close(inspected.state)
    picked = act(state, point, 'take')
    assert picked.accepted
    return picked.state


def crate_ready():
    state = collect(free(), 'tools_chest', 'hold', 510)
    state = collect(state, 'manifest_desk', 'officers', 2380)
    state = collect(state, 'seal_chest', 'captain', 2460)
    state = replace(state, position=Position('kitchen', 1260), reached_kitchen=True)
    state = close(act(state, 'return_crate').state)
    assert story_progress(state)['crate_open']
    state = close(act(state, 'return_crate').state)
    assert story_progress(state)['crate_open']
    return state


def test_collect_is_local_inspected_unique_and_items_are_reusable():
    state = free(position=Position('hold', 510))
    assert not act(state, 'tools_chest', 'take').accepted
    opened = act(state, 'tools_chest')
    assert opened.accepted and opened.state.reading == ''
    taken = act(close(opened.state), 'tools_chest', 'take')
    assert taken.accepted and 'crowbar' in story_progress(taken.state)['items']
    assert not act(taken.state, 'tools_chest', 'take').accepted
    assert not act(replace(state, position=Position('cell',230)), 'tools_chest').accepted
    prepared = crate_ready()
    assert {'crowbar','manifest','seal'} <= set(story_progress(prepared)['items'])


def test_documents_pause_and_resume_a_server_tracked_game_clock():
    state = free(position=Position('cell',205))
    paused = act(state, 'opening_letter', now=10_000).state
    assert game_now_ms(paused, 50_000) == 10_000
    resumed = close(paused, now=50_000)
    assert game_now_ms(resumed, 51_000) == 11_000
    again = story_action(resumed,'journal','',52_000).state
    assert game_now_ms(again,70_000) == 12_000
    assert game_now_ms(close(again,80_000),81_000) == 13_000


def test_crate_needs_open_lid_and_living_cook():
    state = free(position=Position('kitchen',1260))
    result = act(state, 'return_crate')
    assert not result.accepted and not story_progress(result.state).get('crate_open')
    assert not act(close(result.state), 'return_crate', 'finish').accepted
    ready = crate_ready()
    dead = replace(ready,dining_alive=False)
    assert not act(dead,'return_crate').accepted
    confirmed = act(ready,'return_crate')
    assert confirmed.accepted and confirmed.state.reading == 'confirm_crate'
    assert close(confirmed.state).ending == ''
    won = act(confirmed.state,'return_crate','finish')
    assert won.accepted and won.state.ending == 'crate'
    assert won.state.capture_phase == 'none' and won.state.reading == ''


def test_helm_requires_every_opponent_and_ends_immediately():
    state = free(position=Position('aft_deck',1980))
    assert not act(state,'helm','finish').accepted
    for kind in GUARD_ROUTES:
        state = replace(state, **{kind+'_alive':False,kind+'_corpse_x':1900.,kind+'_corpse_y':245.})
    assert not act(state,'helm').accepted  # sleeper counts too
    state = replace(state,sleeper_alive=False)
    prompt = act(state,'helm')
    assert prompt.accepted and prompt.state.reading == ''
    assert prompt.state.ending == 'takeover'


@pytest.mark.parametrize('route',['crate','takeover'])
def test_ending_persists_and_all_stale_actions_are_frozen(tmp_path,route):
    if route=='crate':
        ready=crate_ready(); point='return_crate'
    else:
        ready=free(position=Position('aft_deck',1980),sleeper_alive=False)
        for k in GUARD_ROUTES:
            ready=replace(ready,**{k+'_alive':False,k+'_corpse_x':1900.,k+'_corpse_y':245.})
        point='helm'
    won=act(act(ready,point).state,point,'finish').state
    assert state_from_backup(asdict(won))==won
    path=tmp_path/'ending.sqlite3'
    with connect_db(path) as conn:
        assert restore_game(conn,won,'one')
    with connect_db(path) as conn:
        assert load_game(conn,'one')==won
        before=conn.total_changes
        for kind in ('open','shoot','story_inspect','story_finish','capture','close_reading'):
            result=apply_action(conn,kind,won.position,0,'one',item=point,now_ms=9999)
            assert not result.accepted
        assert not save_position(conn,Position('aft_deck',1950),'one')
        assert conn.total_changes==before and load_game(conn,'one')==won
        assert new_game(conn,'one')==initial_state()


def test_reading_blocks_position_and_story_actions_until_closed(tmp_path):
    paused=act(free(position=Position('cell',205)),'opening_letter').state
    with connect_db(tmp_path/'reading.sqlite3') as conn:
        assert restore_game(conn,paused,'one')
        before=conn.total_changes
        assert not save_position(conn,Position('cell',215),'one')
        assert not apply_action(conn,'shoot',paused.position,0,'one',now_ms=2000).accepted
        assert conn.total_changes==before
        assert apply_action(conn,'close_reading',paused.position,0,'one',now_ms=9000).accepted
        assert load_game(conn,'one').paused_total_ms==8000


def test_old_backups_migrate_and_corrupt_story_is_rejected():
    old=asdict(initial_state())
    for k in ('story_state','ending','reading','paused_at_ms','paused_total_ms'):
        old.pop(k)
    assert state_from_backup(old)==initial_state()
    for corrupt in ('[]','{"items":["invisible_key"]}','{"crate_open":"yes"}','{"items":["crowbar","crowbar"]}'):
        assert state_from_backup({**old,'story_state':corrupt}) is None
    assert state_from_backup({**old,'ending':'made_up'}) is None
    assert state_from_backup({**old,'reading':'confirm_takeover','paused_at_ms':0}) is None


def test_reusable_whistle_changes_look_direction_without_teleporting_or_consumption():
    from logic import guard_pose_at
    state = collect(free(), 'whistle_chest', 'crew_room', 1900)
    # Work on the deck of a known patrol, away from the source after signalling.
    state = replace(state, position=Position('hold',600))
    before = guard_pose_at(state,'patrol',20,10_000)
    signal = story_action(state,'whistle','',10_000)
    assert signal.accepted
    after = guard_pose_at(signal.state,'patrol',20,10_100)
    assert (after.x,after.y) == (before.x,before.y)
    assert after.facing == (1 if 600 >= after.x else -1)
    assert 'whistle' in story_progress(signal.state)['items']
    assert not story_action(signal.state,'whistle','',10_500).accepted
    assert story_action(signal.state,'whistle','',15_000).accepted
