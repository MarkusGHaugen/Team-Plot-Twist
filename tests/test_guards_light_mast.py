"""New ship rules, specified before the implementation."""
from dataclasses import asdict, replace
import sqlite3

import pytest

from db import apply_action, connect_db, load_game, new_game, restore_game
from logic import (
    ALERT_DURATION_MS, BARRELS, GUARD_ROUTES, KEY_REACH, MAST_X, Position,
    advance_player, can_guard_see, change_outfit, guard_pose_for, guard_time,
    initial_state, key_prompt, position_xy, raise_alert, search_crate,
    state_from_backup, toggle_lamp, toggle_wardrobe, with_position,
    suspicion_step,
    guard_pose_at, STAIRS, take_lamp, notice_wardrobe,
)


def free(**changes):
    return replace(initial_state(), has_key=True, door_open=True, **changes)


def test_three_new_guard_routes_have_waits_and_join_without_jumps():
    assert {'patrol', 'dining', 'cargo', 'lookout'} <= set(GUARD_ROUTES)
    for kind, route in GUARD_ROUTES.items():
        assert route
        for a, b in zip(route, route[1:]):
            assert (a.x2, a.y2) == pytest.approx((b.x1, b.y1))
        assert (route[-1].x2, route[-1].y2) == pytest.approx((route[0].x1, route[0].y1))
        for segment in route:
            if segment.x1 != segment.x2 and segment.y1 != segment.y2:
                assert (segment.x1,segment.y1,segment.x2,segment.y2) in tuple(STAIRS.values()) + tuple((v[2],v[3],v[0],v[1]) for v in STAIRS.values())
    dining = GUARD_ROUTES['dining']
    assert next(s for s in dining if s.name == 'eating').duration == 28
    assert next(s for s in dining if s.name == 'lookout_pause').duration == 10.5
    assert guard_pose_for('dining', 0).segment == 'eating'
    assert guard_pose_for('dining', 27.9).segment == 'eating'
    assert guard_pose_for('dining', 28.01).segment != 'eating'
    assert guard_pose_for('dining', sum(s.duration for s in dining)).segment == 'eating'
    assert any(s.x1 == s.x2 and s.y1 == s.y2 and s.duration >= 2 for s in GUARD_ROUTES['cargo'])
    cargo_walk=next(s for s in GUARD_ROUTES['cargo'] if s.name=='cargo_out')
    assert (cargo_walk.x2-cargo_walk.x1)/cargo_walk.duration < 60
    assert any(s.x1 == MAST_X and s.x2 == MAST_X and s.duration >= 2 for s in GUARD_ROUTES['lookout'])
    patrol_names = [s.name for s in GUARD_ROUTES['patrol']]
    assert patrol_names.count('cabin_visit') == 1
    assert patrol_names.index('cabin_visit') > patrol_names.index('hold_return')
    assert all(s.y1 >= 365 and s.y2 >= 365 for s in GUARD_ROUTES['patrol'])


def test_key_reach_is_continuous_at_stair_cell_and_both_directions():
    state = replace(initial_state(), position=Position('cell', 374))
    for name in ('lower_down', 'cell_pass', 'cell_return', 'hold_out',
                 'hold_return', 'lower_down_again', 'cell_pass_again'):
        segment = next(s for s in GUARD_ROUTES['patrol'] if s.name == name)
        samples = [guard_time(name, i/100) for i in range(101)]
        near = [key_prompt(state,t) for t in samples]
        assert all(near[i] for i in range(next((j for j,v in enumerate(near) if v),101),
                                    101-next((j for j,v in enumerate(reversed(near)) if v),101)))
        if name in ('cell_pass','cell_return'):
            assert all(near)
    assert key_prompt(state, guard_time('lower_down', .92))
    assert key_prompt(state, guard_time('hold_out', .04))
    assert key_prompt(state, guard_time('hold_return', .96))
    assert not key_prompt(state, guard_time('hold_out', .2))
    assert KEY_REACH >= 100
    assert not key_prompt(replace(state, position=Position('cell', 220)),guard_time('cell_pass',.5))


def test_lamp_is_unique_switchable_and_other_crates_remain_empty(tmp_path):
    state = free(position=Position('hold', 834))
    revealed = search_crate(state)
    assert revealed.accepted and revealed.state.lamp_revealed and not revealed.state.has_lamp
    found = take_lamp(revealed.state)
    assert found.accepted and found.state.has_lamp and found.state.held_item == 'lamp'
    assert not search_crate(found.state).accepted
    on = toggle_lamp(found.state)
    assert on.accepted and on.state.lamp_lit
    off = toggle_lamp(on.state)
    assert off.accepted and not off.state.lamp_lit
    assert not toggle_lamp(state).accepted
    empty = search_crate(replace(state, position=Position('hold', 613)))
    assert empty.accepted and empty.state == replace(state, position=Position('hold', 613))
    with connect_db(tmp_path/'lamp.sqlite3') as conn:
        assert restore_game(conn,on.state,'browser')
    with connect_db(tmp_path/'lamp.sqlite3') as conn:
        assert load_game(conn,'browser') == on.state


def test_mast_is_secret_climbable_continuous_and_saved(tmp_path):
    p = Position('upper_deck', MAST_X)
    p = advance_player(p, True, 0, 1, .1)
    assert p.zone == 'mast' and 0 < p.value < 1
    last_y = 245
    for _ in range(40):
        xy = position_xy(p)
        assert xy[1] <= last_y
        last_y = xy[1]
        p = advance_player(p, True, 0, 1, .1)
    assert p.zone == 'mast_top'
    assert position_xy(p)[1] < 100
    state = free(position=p)
    assert state_from_backup(asdict(state)) == state
    with connect_db(tmp_path/'mast.sqlite3') as conn:
        assert restore_game(conn,state,'browser')
    with connect_db(tmp_path/'mast.sqlite3') as conn:
        assert load_game(conn,'browser') == state
    p = advance_player(p, True, 0, -1, .1)
    for _ in range(40): p = advance_player(p, True, 0, -1, .1)
    assert p.zone == 'upper_deck'
    assert advance_player(Position('upper_deck',MAST_X+50),True,0,1,.1).zone == 'upper_deck'


def test_upper_barrels_hide_from_lookout_and_all_guards():
    upper = [b for b in BARRELS if b[1] == 'upper_deck']
    assert len(upper) >= 2
    from logic import toggle_barrel
    for name,zone,x in upper:
        hidden = toggle_barrel(free(position=Position(zone,x)))
        assert hidden.accepted and hidden.state.hidden_barrel == name
        assert not can_guard_see(hidden.state,0,'lookout')


def test_wardrobe_contents_and_two_second_suspicion_window():
    state = free(position=Position('cabin',460))
    state = toggle_wardrobe(state).state
    assert state.wardrobe_contents == 'uniform'
    state = change_outfit(state).state
    assert state.disguised and state.wardrobe_contents == 'player_clothes'
    t = 1_000_000
    unseen = state
    state = notice_wardrobe(state, guard_time('cabin_visit', .25), t).state
    started = suspicion_step(state, True, t)
    assert started.suspect_started_ms == t
    assert suspicion_step(started, True, t+1999).capture_phase == 'none'
    escaped = suspicion_step(started, False, t+1900)
    assert escaped.suspect_started_ms == 0
    assert suspicion_step(escaped, True, t+3000).capture_phase == 'none'
    caught = suspicion_step(started, True, t+2001)
    assert caught.capture_phase == 'active'
    assert suspicion_step(replace(unseen,wardrobe_open=False),True,t).suspect_started_ms == 0
    assert change_outfit(state).state.wardrobe_contents == 'uniform'


def test_door_and_shot_alert_window_and_old_save_migration(tmp_path):
    from logic import shoot_guard
    state = free(position=Position('hold',700),has_blue_key=True,chest_open=True,
                 has_pistol=True,held_item='pistol')
    shot = shoot_guard(state,guard_time('hold_out',.4),now_ms=1_000_000)
    assert shot.state.alert_until_ms == 1_000_000 + ALERT_DURATION_MS
    assert not shot.state.door_alerted
    from logic import guard_notices_door
    moment = guard_time('cell_return',.5)
    assert guard_notices_door(state,moment)
    alarm = raise_alert(state,moment,2_000_000)
    assert alarm.state.alert_until_ms == 2_000_000 + ALERT_DURATION_MS
    assert not guard_notices_door(alarm.state,moment)
    path=tmp_path/'old.sqlite3'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE progress (player_id TEXT PRIMARY KEY,zone TEXT,position_value REAL,has_key INTEGER,door_open INTEGER,reached_kitchen INTEGER,has_blue_key INTEGER,chest_open INTEGER,has_pistol INTEGER,disguised INTEGER)')
        conn.execute("INSERT INTO progress VALUES ('old','cabin',460,1,1,0,1,1,1,1)")
    with connect_db(path) as conn:
        old=load_game(conn,'old')
        assert old.has_blue_key and old.has_pistol and old.disguised
        assert not old.has_lamp and old.dining_alive and old.cargo_alive and old.lookout_alive
        assert old.wardrobe_contents == 'player_clothes'
        before=conn.total_changes
        assert not apply_action(conn,'toggle_lamp',old.position,0,'old').accepted
        assert conn.total_changes==before
        new_game(conn,'new')
        assert load_game(conn,'old')==old
    assert not state_from_backup({'position':{'zone':'mast','value':2},'has_key':True,'door_open':True,'reached_kitchen':False})


def test_search_starts_at_each_actual_guard_and_returns_without_jump():
    from logic import guard_pose_for
    state=free(position=Position('hold',700))
    moment=guard_time('cell_return',.5)
    now=5_000_000
    alarm=raise_alert(state,moment,now).state
    for kind in GUARD_ROUTES:
        start=guard_pose_for(kind,moment)
        immediate=guard_pose_at(alarm,kind,moment,now)
        assert (immediate.x,immediate.y)==pytest.approx((start.x,start.y))
        after=guard_pose_at(alarm,kind,moment+.1,now+100)
        assert ((after.x-start.x)**2+(after.y-start.y)**2)**.5 <= 30
        end=guard_pose_at(alarm,kind,moment+20,now+ALERT_DURATION_MS-1)
        resume=guard_pose_at(alarm,kind,moment+20,now+ALERT_DURATION_MS)
        assert ((end.x-resume.x)**2+(end.y-resume.y)**2)**.5 < 3
    from logic import alert_waypoints
    assert {'hold','chest_room','cabin'} <= {p.zone for p in alert_waypoints('patrol')}
    assert {'dining','kitchen','upper_deck'} <= {p.zone for p in alert_waypoints('dining')}


def test_old_inventory_check_constraint_is_migrated_for_lamp(tmp_path):
    path=tmp_path/'prior-version.sqlite3'
    with sqlite3.connect(path) as conn:
        conn.execute("""CREATE TABLE progress (player_id TEXT PRIMARY KEY,zone TEXT NOT NULL,
          position_value REAL NOT NULL,has_key INTEGER NOT NULL,door_open INTEGER NOT NULL,
          reached_kitchen INTEGER NOT NULL,held_item TEXT NOT NULL DEFAULT 'none'
          CHECK(held_item IN ('none','cell_key','blue_key','pistol')),
          has_blue_key INTEGER NOT NULL DEFAULT 0,chest_open INTEGER NOT NULL DEFAULT 0,
          has_pistol INTEGER NOT NULL DEFAULT 0,disguised INTEGER NOT NULL DEFAULT 0)""")
        conn.execute("INSERT INTO progress VALUES ('old','hold',834,1,1,0,'pistol',1,1,1,1)")
    with connect_db(path) as conn:
        old=load_game(conn,'old')
        assert old.has_pistol and old.has_blue_key and old.disguised
        assert old.wardrobe_contents=='player_clothes'
        result=apply_action(conn,'search_crate',Position('hold',834),0,'old')
        assert result.accepted and result.state.lamp_revealed and not result.state.has_lamp
        result=apply_action(conn,'take_lamp',Position('hold',834),0,'old')
        assert result.accepted and result.state.has_lamp and result.state.held_item=='lamp'
    with connect_db(path) as conn:
        assert load_game(conn,'old').held_item=='lamp'


def test_each_new_guard_can_detect_capture_or_remain_inert_when_dead():
    from logic import start_capture, capture_paths
    for kind in GUARD_ROUTES:
        route=GUARD_ROUTES[kind]
        sample=next((s for s in route if s.x2>s.x1 and s.y1==s.y2),None)
        assert sample is not None
        elapsed=sum(s.duration for s in route[:route.index(sample)])+sample.duration*.45
        guard=guard_pose_for(kind,elapsed)
        from logic import FLOORS
        zone=next(z for z,(lo,hi,y) in FLOORS.items() if lo<=guard.x+70<=hi and y==guard.y)
        state=free(position=Position(zone,guard.x+70))
        assert can_guard_see(state,elapsed,kind)
        started=start_capture(state,elapsed,kind)
        assert started.accepted and started.state.capture_guard==kind
        approach,escort=capture_paths(started.state)
        assert approach[0]==pytest.approx((guard.x,guard.y))
        assert escort[-1]==(230.,500.)
        assert not can_guard_see(replace(state,**{f'{kind}_alive':False}),elapsed,kind)


def test_pistol_free_route_with_closed_wardrobe_remains_safe():
    from logic import change_outfit, toggle_wardrobe, toggle_barrel
    dressed=change_outfit(toggle_wardrobe(free(position=Position('cabin',460))).state)
    assert dressed.accepted and dressed.state.disguised
    closed=toggle_wardrobe(dressed.state).state
    assert not closed.wardrobe_open and closed.wardrobe_contents=='player_clothes'
    for kind in GUARD_ROUTES:
        for t in (0,10,40,80):
            nearby=replace(closed,position=Position('upper_deck',760))
            assert not can_guard_see(nearby,t,kind)
    hidden=toggle_barrel(replace(closed,position=Position('upper_deck',885))).state
    assert hidden.hidden_barrel=='barrel_deck_b'
    assert not hidden.has_pistol


def test_new_guards_fall_remain_dead_and_do_not_search_after_shot(tmp_path):
    from logic import shoot_guard
    for kind in GUARD_ROUTES:
        route=GUARD_ROUTES[kind]
        moving=next(s for s in route if s.x2>s.x1 and s.y1==s.y2)
        t=sum(s.duration for s in route[:route.index(moving)])+moving.duration*.5
        pose=guard_pose_for(kind,t)
        player_x=pose.x-80
        from logic import FLOORS
        zone=next(z for z,(lo,hi,y) in FLOORS.items() if lo<=player_x<=hi and y==pose.y)
        all_dead={f'{name}_alive':False for name in GUARD_ROUTES}
        all_dead.update({f'{name}_corpse_x':160. for name in GUARD_ROUTES})
        all_dead.update({f'{name}_corpse_y':500. for name in GUARD_ROUTES})
        all_dead.update({f'{kind}_alive':True,f'{kind}_corpse_x':None,f'{kind}_corpse_y':None})
        state=free(position=Position(zone,player_x),reached_kitchen=True,has_blue_key=True,chest_open=True,
                   has_pistol=True,held_item='pistol',facing='right',**all_dead)
        hit=shoot_guard(state,t,now_ms=7_000_000)
        assert hit.accepted and not getattr(hit.state,f'{kind}_alive')
        assert getattr(hit.state,f'{kind}_corpse_x')==pytest.approx(pose.x)
        assert hit.state.alert_until_ms==7_000_000+ALERT_DURATION_MS
        assert not can_guard_see(hit.state,t,kind)
        assert state_from_backup(asdict(hit.state))==hit.state
        with connect_db(tmp_path/f'{kind}.sqlite3') as conn:
            assert restore_game(conn,hit.state,'browser')
        with connect_db(tmp_path/f'{kind}.sqlite3') as conn:
            assert not getattr(load_game(conn,'browser'),f'{kind}_alive')
