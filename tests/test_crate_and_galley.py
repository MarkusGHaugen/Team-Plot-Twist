"""Return crate 07 waits on the middle deck; the galley is a real kitchen."""
from dataclasses import asdict, replace

import pytest

from content import STORY_POINTS
from escort import plan
from logic import BARREL_RANGE, BARRELS, FLOORS, Position, initial_state, state_from_backup
from voyage import progress, save
from test_canvas_rules import canvas, NODE


def test_crate_07_stands_between_the_two_middle_deck_barrels():
    crate = STORY_POINTS['return_crate']
    left, right = sorted(x for _, zone, x in BARRELS if zone == 'mid')
    assert crate['zone'] == 'mid' and left < crate['x'] < right
    # Each spot keeps its own F: the crate's reach never overlaps a barrel's.
    assert left + BARREL_RANGE < crate['x'] - crate['reach']
    assert crate['x'] + crate['reach'] < right - BARREL_RANGE


def test_a_save_with_a_cook_escort_to_the_old_galley_crate_still_loads():
    s = replace(initial_state(), has_key=True, door_open=True, position=Position('dining', 1100))
    v = progress(s)
    v.update(coins=0, claimed=['coins_hold', 'coins_chart'], paid=['cook'])
    v['escort'] = plan(s, Position('kitchen', 1260), Position('dining', 1100), 'cook', 2000)
    old = save(s, v)
    assert state_from_backup(asdict(old)) == old


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas drawing code')
def test_the_galley_draws_its_stove_pot_and_table_without_errors():
    calls = canvas(r'''(()=>{const log=[];const ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:(typeof k==='string'&&/^create/.test(k)?()=>({addColorStop(){}}):(...a)=>{log.push(k);}),set:(t,k,v)=>{t[k]=v;return true;}});
      drawGalleyWall(ctx);
      for(const drugged of [false,true])drawGalley(ctx,{story:{voyage:{stew_drugged:drugged}}},12345);
      return log.length;})()''', {})
    assert calls > 100
