"""A decorative painting can be inspected without changing escape progress."""
from dataclasses import replace

from content import DOCUMENTS, STORY_POINTS
from logic import BARRELS, BARREL_RANGE, CRATES, CRATE_RANGE, Position, initial_state, story_action, story_progress


def test_painting_is_local_readable_and_has_no_item_or_ending():
    point = STORY_POINTS['crew_painting']
    state = replace(initial_state(), has_key=True, door_open=True,
                    position=Position(point['zone'], point['x']))
    far = replace(state, position=Position(point['zone'], point['x'] + point['reach'] + 1))
    assert not story_action(far, 'inspect', 'crew_painting', 1000).accepted
    result = story_action(state, 'inspect', 'crew_painting', 1000)
    assert result.accepted and result.state.reading == 'crew_painting'
    assert DOCUMENTS['crew_painting']['body']
    assert story_progress(result.state)['items'] == story_progress(state)['items']
    assert result.state.ending == state.ending
    closed = story_action(result.state, 'close_reading', '', 2000)
    assert closed.accepted and not closed.state.reading
    assert story_action(closed.state, 'inspect', 'crew_painting', 3000).accepted


def test_painting_is_near_provisions_without_overriding_nearby_props():
    point = STORY_POINTS['crew_painting']
    assert point['zone'] == 'armory' and 2100 < point['x'] < 2220
    for _, zone, x in BARRELS:
        if zone == point['zone']:
            assert abs(point['x'] - x) > point['reach'] + BARREL_RANGE
    for _, zone, x in CRATES:
        if zone == point['zone']:
            assert abs(point['x'] - x) > point['reach'] + CRATE_RANGE
