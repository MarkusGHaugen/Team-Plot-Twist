"""Acceptance tests written before the expanded ship implementation."""
from dataclasses import asdict, replace
from math import hypot
import sqlite3

import pytest

from db import apply_action, connect_db, load_game, new_game, restore_game
from logic import (BARRELS, CRATES, FLOORS, STAIRS, GUARD_ROUTES, GUARD_STYLES,
    Position, advance_player, initial_state, guard_time, guard_pose_at,
    notice_wardrobe, inspect_disguise, search_crate, take_lamp,
    state_from_backup, route_points, position_xy, can_guard_see, toggle_barrel,
    start_capture, shoot_guard, capture_paths)


def free(**changes):
    return replace(initial_state(), has_key=True, door_open=True, reached_kitchen=True, **changes)


def test_wardrobe_is_seen_on_real_route_with_player_absent_and_remembered():
    state = free(position=Position('hold', 710), disguised=True,
                 wardrobe_open=True, wardrobe_contents='player_clothes')
    times = [guard_time('cabin_visit', i/100) for i in range(101)]
    notices = [notice_wardrobe(state, t, 1_000_000) for t in times]
    assert sum(r.accepted for r in notices) >= 20  # not a fleeting frame
    noticed = next(r.state for r in notices if r.accepted)
    assert noticed.wardrobe_suspected
    assert not notice_wardrobe(replace(state, wardrobe_open=False),times[50],1_000_000).accepted
    assert not notice_wardrobe(replace(state, disguised=False,wardrobe_contents='uniform'),times[50],1_000_000).accepted
    assert not notice_wardrobe(replace(state, patrol_alive=False),times[50],1_000_000).accepted
    assert not notice_wardrobe(state,guard_time('hold_out',.5),1_000_000).accepted
    assert not notice_wardrobe(noticed,times[50],1_000_000).accepted
    assert state_from_backup(asdict(noticed)) == noticed


def test_investigation_freezes_guard_escape_resets_timer_and_more_than_two_seconds_captures():
    t = guard_time('cabin_visit', .5)
    state = free(position=Position('cabin',460), disguised=True,
                 wardrobe_contents='player_clothes', wardrobe_suspected=True)
    first = inspect_disguise(state,t,1_000_000)
    assert first.accepted and first.state.suspect_started_ms == 1_000_000
    a = guard_pose_at(first.state,'patrol',t,1_000_000)
    b = guard_pose_at(first.state,'patrol',t+1.9,1_001_900)
    assert (a.x,a.y) == (b.x,b.y)
    assert inspect_disguise(first.state,t+2,1_002_000).state.capture_phase == 'none'
    escaped = inspect_disguise(replace(first.state,position=Position('mid',700)),t+1.9,1_001_900)
    assert escaped.accepted and not escaped.state.suspect_started_ms
    assert escaped.state.wardrobe_suspected
    resumed = guard_pose_at(escaped.state,'patrol',t+1.9,1_001_900)
    assert (resumed.x,resumed.y) == pytest.approx((a.x,a.y))
    caught = inspect_disguise(first.state,t+2.01,1_002_010)
    assert caught.accepted and caught.state.capture_phase == 'active'
    assert capture_paths(caught.state)[1][-1] == (230.,500.)
    for alternative in (replace(state,wardrobe_suspected=False),
                        replace(state,patrol_alive=False),
                        replace(state,position=Position('upper_deck',460))):
        assert not inspect_disguise(alternative,t,1_000_000).accepted


def test_lamp_three_stages_rejections_and_full_restart(tmp_path):
    path=tmp_path/'lamp.sqlite3'
    state=free(position=Position('hold',834))
    with connect_db(path) as c:
        assert restore_game(c,state,'p')
        before=c.total_changes
        assert not apply_action(c,'take_lamp',state.position,0,'p').accepted
        assert c.total_changes == before
        revealed=apply_action(c,'search_crate',state.position,0,'p').state
        assert revealed.lamp_revealed and not revealed.has_lamp
        assert revealed.held_item == 'none'
    with connect_db(path) as c:
        assert load_game(c,'p') == revealed
        before=c.total_changes
        assert not apply_action(c,'take_lamp',Position('hold',780),0,'p').accepted
        assert c.total_changes == before
        taken=apply_action(c,'take_lamp',state.position,0,'p').state
        assert taken.lamp_revealed and taken.has_lamp and taken.held_item=='lamp'
        before=c.total_changes
        assert not apply_action(c,'take_lamp',state.position,0,'p').accepted
        assert c.total_changes == before
    with connect_db(path) as c:
        assert load_game(c,'p') == taken
        assert state_from_backup(asdict(taken)) == taken
        new_game(c,'p')
        assert load_game(c,'p') == initial_state()


def test_existing_lamp_owner_migrates_in_sqlite_and_browser(tmp_path):
    path=tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE progress (player_id TEXT PRIMARY KEY,zone TEXT,position_value REAL,has_key INTEGER,door_open INTEGER,reached_kitchen INTEGER,has_lamp INTEGER,lamp_lit INTEGER,held_item TEXT CHECK(held_item IN ('none','lamp')))")
        c.execute("INSERT INTO progress VALUES ('p','hold',834,1,1,0,1,1,'lamp')")
    with connect_db(path) as c:
        old=load_game(c,'p')
        assert old.has_lamp and old.lamp_revealed and old.lamp_lit
        assert old.position==Position('hold',834) and old.held_item=='lamp'
    payload=asdict(free(position=Position('hold',834),has_lamp=True,held_item='lamp'))
    payload.pop('lamp_revealed')
    migrated=state_from_backup(payload)
    assert migrated.has_lamp and migrated.lamp_revealed
    assert all(getattr(migrated,f'{kind}_alive') for kind in GUARD_ROUTES)


def test_double_length_connected_rooms_and_every_stair_both_directions():
    assert max(f[1] for f in FLOORS.values()) == 2580
    assert set(f[2] for f in FLOORS.values()) == {245,365,500}
    assert FLOORS['cabin'] == (160,520,365) and FLOORS['kitchen'] == (1040,1370,245)
    assert len(FLOORS)>=16
    for zone,(lo,hi,y) in FLOORS.items():
        path=route_points(Position('cell',230),Position(zone,(lo+hi)/2))
        assert path[-1]==((lo+hi)/2,y)
        for a,b in zip(path,path[1:]):
            if a[1]!=b[1]:
                assert any((a==s[:2] and b==s[2:]) or (b==s[:2] and a==s[2:]) for s in STAIRS.values())
    for zone,s in STAIRS.items():
        for initial,direction,endpoint in ((.1,-1,s[:2]),(.9,1,s[2:])):
            p=Position(zone,initial)
            for _ in range(30):
                p=advance_player(p,True,0,direction,.1)
                if p.zone not in STAIRS: break
            assert position_xy(p)==pytest.approx(endpoint)
    for y in (245,365,500):
        zone=next(z for z,f in FLOORS.items() if f[0]==160 and f[2]==y)
        p=Position(zone,160)
        visited={p.zone}
        for _ in range(150):
            p=advance_player(p,True,1,0,.1);visited.add(p.zone)
        assert p.value==2580
        assert visited=={z for z,f in FLOORS.items() if f[2]==y}


def test_ten_guards_routes_sight_capture_and_death_storage(tmp_path):
    assert len(GUARD_ROUTES)==9  # plus the sleeping guard
    assert len({v['color'] for v in GUARD_STYLES.values()})==9
    for kind,route in GUARD_ROUTES.items():
        for a,b in zip(route,(*route[1:],route[0])):
            assert (a.x2,a.y2)==(b.x1,b.y1)
        segment=next(s for s in route if s.y1==s.y2 and s.x2>s.x1)
        t=sum(s.duration for s in route[:route.index(segment)])+segment.duration*.5
        pose=guard_pose_at(initial_state(),kind,t,1_000_000)
        x=pose.x+60
        zone=next(z for z,f in FLOORS.items() if f[0]<=x<=f[1] and f[2]==pose.y)
        state=free(position=Position(zone,x))
        assert can_guard_see(state,t,kind)
        assert start_capture(state,t,kind).state.capture_guard==kind
        dead=replace(state,**{f'{kind}_alive':False,f'{kind}_corpse_x':pose.x,f'{kind}_corpse_y':pose.y})
        assert not can_guard_see(dead,t,kind)
        with connect_db(tmp_path/f'{kind}.sqlite3') as c: assert restore_game(c,dead,'p')
        with connect_db(tmp_path/f'{kind}.sqlite3') as c: assert load_game(c,'p')==dead
        assert state_from_backup(asdict(dead))==dead


def test_barrels_crates_and_pistol_free_exploration():
    assert len(BARRELS)>=20
    assert all(any(zone==z for _,z,_ in BARRELS) for zone,f in FLOORS.items() if f[0]>=1370)
    dressed=free(disguised=True,wardrobe_contents='player_clothes')
    for name,zone,x in BARRELS:
        hidden=toggle_barrel(replace(dressed,position=Position(zone,x))).state
        assert hidden.hidden_barrel==name
        assert state_from_backup(asdict(hidden))==hidden
        assert all(not can_guard_see(hidden,20,kind) for kind in GUARD_ROUTES)
    for name,zone,x in CRATES:
        state=replace(dressed,position=Position(zone,x))
        result=search_crate(state)
        assert result.accepted and not result.state.has_lamp
        assert toggle_barrel(state).accepted  # crates now provide cover too
    for zone,(lo,hi,y) in FLOORS.items():
        state=replace(dressed,position=Position(zone,(lo+hi)/2))
        for t in range(0,150,5):
            assert all(not can_guard_see(state,t,kind) for kind in GUARD_ROUTES)
        assert not state.has_pistol
