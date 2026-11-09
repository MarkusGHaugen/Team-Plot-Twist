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
