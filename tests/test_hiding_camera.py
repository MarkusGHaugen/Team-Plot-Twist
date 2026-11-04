"""Regression checks for sleeping safety, foreground guards and the opening view."""
from dataclasses import asdict, replace

import pytest

from db import apply_action, connect_db, load_game, restore_game
from logic import (GUARD_ROUTES, MAP_CONFIG, Position, can_guard_see, guard_time,
                   initial_state, inspect_disguise, start_capture, toggle_hammock)
from test_canvas_rules import canvas, NODE


def sleeper(**changes):
    return replace(initial_state(),has_key=True,door_open=True,
                   position=Position('hammock',300),in_hammock=True,**changes)


def test_sleeping_is_safe_from_every_guard_and_standing_is_visible_again():
    state=sleeper()
    for kind in GUARD_ROUTES:
        for t in range(0,150,3):
            assert not can_guard_see(state,t,kind)
            assert not start_capture(state,t,kind).accepted
    awake=toggle_hammock(state)
    assert awake.accepted and not awake.state.in_hammock
    moment=guard_time('cabin_visit',.5)
    assert can_guard_see(awake.state,moment,'patrol')
    assert start_capture(awake.state,moment,'patrol').accepted


def test_sleeping_cancels_existing_disguise_inspection():
    state=sleeper(disguised=True,wardrobe_contents='player_clothes',wardrobe_suspected=True,
                  suspect_started_ms=1_000_000,suspect_guard_zone='cabin',suspect_guard_value=360.)
    result=inspect_disguise(state,guard_time('cabin_visit',.5),1_003_000)
    assert result.state.capture_phase=='none'
    assert result.state.suspect_started_ms==0
    assert result.state.in_hammock


def test_saved_sleeping_player_rejects_capture_without_database_changes(tmp_path):
    path=tmp_path/'sleep.sqlite3'
    state=sleeper()
    with connect_db(path) as conn:
        assert restore_game(conn,state,'sleep-test')
    with connect_db(path) as conn:
        assert load_game(conn,'sleep-test')==state
        before=conn.total_changes
        result=apply_action(conn,'capture',state.position,guard_time('cabin_visit',.5),
                            'sleep-test',item='patrol',now_ms=1_000_000)
        assert not result.accepted
        assert conn.total_changes==before
        assert load_game(conn,'sleep-test')==state


@pytest.mark.skipif(NODE is None,reason='Execute the real Canvas rules in Node')
def test_canvas_also_ignores_a_sleeping_player_for_sight_and_inspection():
    state=asdict(sleeper())
    result=canvas('''(() => {
      const client={data:{...input.state,rules:input.rules},position:input.state.position};
      const pose={x:390,y:365,facing:-1};
      const seen=guardCanSee(client,pose,'patrol');
      client.data.disguised=true;client.data.wardrobe_suspected=true;
      return {seen,investigated:investigating(client,pose)};
    })()''',{'state':state,'rules':MAP_CONFIG})
    assert result=={'seen':False,'investigated':False}


@pytest.mark.skipif(NODE is None,reason='Execute the actual camera transform')
def test_cell_camera_shows_letter_and_half_stair_then_returns_to_normal_outside():
    result=canvas('''(() => {
      const views=[230,374].map(x=>cameraFor({x,y:500},1000,500,'cell'));
      return {views,outside:cameraFor({x:420,y:500},1000,500,'hold')};
    })()''',{})
    for view in result['views']:
        assert view['zoom']>2.4
        assert view['x']+1000/view['zoom']==pytest.approx(495)
        for x in (205,390,490):
            assert 0<(x-view['x'])*view['zoom']<1000
        assert (540-view['x'])*view['zoom']>1000
        assert 0<(432.5-view['y'])*view['zoom']<500
    assert result['views'][0]==result['views'][1]
    assert result['outside']['zoom']==pytest.approx(1.22)


@pytest.mark.skipif(NODE is None,reason='Record paint order from the actual draw function')
def test_guard_is_painted_in_front_of_visible_barrel_hat():
    state=asdict(replace(initial_state(),has_key=True,door_open=True,
                        position=Position('hold',710),hidden_barrel='barrel_hold_a'))
    result=canvas('''(() => {
      const order=[];
      globalThis.window={devicePixelRatio:1};globalThis.performance={now:()=>1000};
      background=()=>{};ship=()=>{};storyDecor=()=>{};cellBars=()=>{};
      lyingPerson=()=>{};fallen=()=>{};
      person=(ctx,x,y,guard)=>order.push(guard?'guard':'standing-player');
      const gradient={addColorStop:()=>{}};
      const ctx=new Proxy({fillStyle:'',fill(){if(this.fillStyle==='#273a40')order.push('hat');}},
        {get:(obj,key)=>key in obj?obj[key]:key.startsWith('create')?()=>gradient:()=>{}});
      const data={...input.state,rules:input.rules,guard_routes:{patrol:[]}};
      draw({data,position:data.position,bullets:[],facing:'right'},
        {width:1000,height:500,getContext:()=>ctx},{clientWidth:1000,clientHeight:500},
        {patrol:{x:710,y:500,facing:1,name:'hold_out'}});
      return order;
    })()''',{'state':state,'rules':MAP_CONFIG})
    assert result.count('hat')==1
    assert result.index('hat')<result.index('guard')
    assert 'standing-player' not in result
