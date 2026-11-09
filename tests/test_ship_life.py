"""Ambient ship life: rats, telescope and cannon."""
import pytest
from test_canvas_rules import canvas, NODE

pytestmark=pytest.mark.skipif(NODE is None,reason='Node runs the Canvas rules')


def test_rats_bolt_away_from_nearby_people_and_stay_in_the_hold():
    result=canvas(r'''(()=>{
    const rats=initRats();rats.forEach(r=>{r.until=1e9;});
    const before=rats.map(r=>r.x);
    // Someone walks right up to the second rat from its left.
    stepRats(rats,.016,[{x:before[1]-40,y:500}],0);
    const fleeing={mode:rats[1].mode,dir:rats[1].dir,squeak:rats[1].squeak>0};
    for(let i=0;i<200;i++)stepRats(rats,.05,[{x:430,y:500},{x:1340,y:500}],i*50);
    // A threat on another deck does not scare them.
    const calm=initRats();calm.forEach(r=>{r.until=1e9;});stepRats(calm,.1,[{x:calm[0].x,y:365}],0);
    return {fleeing,xs:rats.map(r=>r.x),calm:calm[0].mode};
    })()''',{})
    assert result['fleeing']=={'mode':'flee','dir':1,'squeak':True}
    assert all(420<=x<=1350 for x in result['xs'])
    assert result['calm']=='sniff'


def test_telescope_sits_in_the_crows_nest_and_names_what_you_see():
    from content import STORY_POINTS
    from logic import MAST_X, Position, with_position, initial_state
    from dataclasses import replace
    p=STORY_POINTS['telescope']
    assert p['zone']=='mast_top' and abs(p['x']-MAST_X)<=40  # reachable on the platform
    result=canvas(r'''[850,1650,2450,300,1250,850+3000,-2700].map(scopeCaption)''',{})
    assert 'island' in result[0] and 'Nobody lives there' in result[0]
    assert 'harbour town' in result[1] and 'frigate' in result[2] and 'whale' in result[3]
    assert result[4]=='Open sea in every direction.'
    assert result[5]==result[0]  # the view wraps all the way round
    assert result[6]==result[3]


def _on_deck(x=300., **changes):
    from dataclasses import replace
    from logic import initial_state, Position
    return replace(initial_state(), has_key=True, door_open=True, position=Position('upper_deck', x), **changes)


def test_cannon_needs_a_lit_lamp_fires_once_and_brings_the_crew_running():
    import json
    from dataclasses import asdict
    from logic import story_progress, state_from_backup, guard_pose_at, GUARD_ROUTES
    from shiplife import fire_cannon, FUSE_MS
    assert not fire_cannon(_on_deck(600.), 0, 1000).accepted          # too far away
    unlit = fire_cannon(_on_deck(has_lamp=True, held_item='lamp'), 0, 1000)
    assert not unlit.accepted and 'lit lamp' in unlit.message
    fired = fire_cannon(_on_deck(has_lamp=True, lamp_revealed=True, lamp_lit=True, held_item='lamp'), 0, 1000)
    assert fired.accepted
    s = fired.state
    assert story_progress(s)['voyage']['cannon_fired'] == 1000 + FUSE_MS
    assert s.alert_started_ms == 1000 + FUSE_MS
    # Every living crew member's search starts by heading for the cannon.
    paths = json.loads(s.alert_paths)
    for kind, path in paths.items():
        assert [300., 245.] in path[1:], kind
        assert path.index([300., 245.]) <= min(i for i, p in enumerate(path) if i and p != path[0]) + 4
    assert not fire_cannon(s, 0, 30_000).accepted                     # only one shot
    assert state_from_backup(asdict(s)) is not None


def test_cannon_motion_kicks_back_and_settles():
    result = canvas(r'''[-300,0,60,120,900,1700,7000].map(cannonMotion)''', {})
    fuse, start, flash, kick, rolling, back, later = result
    assert fuse['fuse'] and fuse['ball'] is None and not fuse['boom']
    assert start['flash'] and start['shake'] > 0 and start['ball'] is not None
    assert kick['recoil'] == 22 and rolling['recoil'] < kick['recoil'] and back['recoil'] == 0
    assert rolling['ball']['dx'] < start['ball']['dx']            # the ball flies out over the bow
    assert later['smoke'] == [] and later['shake'] == 0 and not later['boom']
