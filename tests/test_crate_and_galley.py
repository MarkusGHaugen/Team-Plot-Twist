"""Return crate 07 waits on the middle deck between the two barrels."""
from dataclasses import asdict, replace

from content import STORY_POINTS
from escort import plan
from logic import BARREL_RANGE, BARRELS, FLOORS, Position, initial_state, state_from_backup
from voyage import progress, save


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

