from dataclasses import replace
from logic import STAIRS, Position, advance_player, initial_state, story_action, story_progress, state_from_backup
from content import STORY_POINTS
from dataclasses import asdict

def test_each_stair_landing_accepts_horizontal_exit():
    for name in STAIRS:
        for p in (.08, .92):
            for direction in (-1, 1):
                result=advance_player(Position(name,p),True,direction,0,.1)
                assert result.zone not in STAIRS
        assert advance_player(Position(name,.5),True,1,0,.1)==Position(name,.5)

def test_open_chests_do_not_pause_and_pickups_survive_restore():
    for name,point in STORY_POINTS.items():
        if point['kind']!='chest': continue
        state=replace(initial_state(),has_key=True,door_open=True,position=Position(point['zone'],point['x']))
        assert not story_action(state,'take',name,1000).accepted
        opened=story_action(state,'inspect',name,1000)
        assert opened.accepted and not opened.state.reading and not opened.state.paused_at_ms
        taken=story_action(opened.state,'take',name,1100)
        assert taken.accepted
        assert not story_action(taken.state,'take',name,1200).accepted
        restored=state_from_backup(asdict(taken.state))
        assert restored and point['item'] in story_progress(restored)['items']


def test_stairs_catch_up_from_the_visible_foot_area():
    from logic import _floor_zone
    for name,(x1,y1,x2,y2) in STAIRS.items():
        for x in (x1-40,x1+50,x2):
            p=advance_player(Position(_floor_zone(y1,x),x),True,1,1,.1)
            assert p.zone==name
        for x in (x1,x2-50,x2+40):
            p=advance_player(Position(_floor_zone(y2,x),x),True,-1,-1,.1)
            assert p.zone==name
    assert advance_player(Position('cell',380),False,0,1,.1)==Position('cell',380)


def test_expanded_stair_entry_matches_canvas():
    from test_canvas_rules import canvas
    from logic import MAP_CONFIG, _floor_zone
    import pytest
    cases=[]
    for name,(x1,y1,x2,y2) in STAIRS.items():
        for x in (x1-40,x1+50,x2): cases.append((Position(_floor_zone(y1,x),x),1))
        for x in (x1,x2-50,x2+40): cases.append((Position(_floor_zone(y2,x),x),-1))
    got=canvas('input.cases.map(([p,v])=>move(p,true,0,v,.1,input.rules))',{'cases':[(asdict(p),v) for p,v in cases],'rules':MAP_CONFIG})
    for js,(p,v) in zip(got,cases):
        py=advance_player(p,True,0,v,.1)
        assert js['zone']==py.zone and js['value']==pytest.approx(py.value)
