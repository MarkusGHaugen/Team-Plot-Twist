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
