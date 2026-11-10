"""Both endings reached from initial_state through movement and accepted rules."""
from dataclasses import asdict
from math import isclose

from content import STORY_POINTS
from logic import (Position, advance_player, change_outfit, guard_time, initial_state,
    open_door, opponents_remaining, position_xy, route_points, select_item,
    shoot_guard, steal_blue_key, steal_key, story_action, story_progress,
    toggle_wardrobe, unlock_chest, take_pistol, with_position)


def accepted(result):
    assert result.accepted, result.message
    return result.state


def walk(state, target):
    """Walk each continuous floor/stair segment, never assign an invented position."""
    for gx,gy in route_points(state.position,target)[1:]:
        for _ in range(2000):
            x,y=position_xy(state.position)
            if isclose(x,gx,abs_tol=.001) and isclose(y,gy,abs_tol=.001):
                break
            if isclose(y,gy,abs_tol=.001):
                h=1 if gx>x else -1
                next_pos=advance_player(state.position,state.door_open,h,0,min(.04,abs(gx-x)/180))
            else:
                next_pos=advance_player(state.position,state.door_open,0,1 if gy<y else -1,.04)
            assert next_pos!=state.position, (state.position,(gx,gy))
            updated=with_position(state,next_pos)
            assert updated is not None
            state=updated
        else:
            raise AssertionError('Route did not finish')
    assert state.position.zone==target.zone
    return state


def start_free():
    state=walk(initial_state(),Position('cell',374))
    state=accepted(steal_key(state,guard_time('cell_pass',.5)))
    return accepted(open_door(state))


def take_story(state,point_id):
    p=STORY_POINTS[point_id]
    state=walk(state,Position(p['zone'],p['x']))
    state=accepted(story_action(state,'inspect',point_id,1000))
    if state.reading: state=accepted(story_action(state,'close_reading','',2000))
    return accepted(story_action(state,'take',point_id,3000))


def crate_path():
    state=start_free()
    # Forkledning is an established valid way through the patrols.
    state=walk(state,Position('cabin',460))
    state=accepted(toggle_wardrobe(state))
    state=accepted(change_outfit(state))
    state=accepted(toggle_wardrobe(state))
    for point in ('tools_chest','manifest_desk','seal_chest'):
        state=take_story(state,point)
    state=walk(state,Position('mid',735))
    for _ in range(2):
        state=accepted(story_action(state,'inspect','return_crate',5000))
        if state.reading: state=accepted(story_action(state,'close_reading','',6000))
    assert story_progress(state)['crate_open']
    return state


def takeover_path():
    state=start_free()
    state=walk(state,Position('cabin',300))
    state=accepted(steal_blue_key(state))
    state=walk(state,Position('cabin',460))
    state=accepted(toggle_wardrobe(state))
    state=accepted(change_outfit(state))
    state=accepted(toggle_wardrobe(state))
    state=walk(state,Position('chest_room',1120))
    state=accepted(unlock_chest(state))
    state=accepted(take_pistol(state))
    # At route time zero all patrols occupy a floor. Take every shot through
    # the actual directional/wall/nearest-target shooting rule.
    for zone in ('cell','cabin','upper_deck'):
        state=walk(state,Position(zone,160))
        # Approach from the left so a real movement action sets right facing.
        state=walk(state,Position(zone,175))
        for _ in range(12):
            before=opponents_remaining(state)
            shot=shoot_guard(state,0,0)
            assert shot.accepted
            if opponents_remaining(shot.state)==before:
                break
            state=shot.state
    assert opponents_remaining(state)==0
    return walk(state,Position('aft_deck',1980))


def test_both_endings_have_a_complete_valid_path_from_new_game():
    from logic import state_from_backup
    for prepare,point,ending in ((crate_path,'return_crate','crate'),(takeover_path,'helm','takeover')):
        ready=prepare()
        confirmed=accepted(story_action(ready,'inspect',point,10_000))
        won=confirmed if confirmed.ending else accepted(story_action(confirmed,'finish',point,11_000))
        assert won.ending==ending
        assert state_from_backup(asdict(won))==won
