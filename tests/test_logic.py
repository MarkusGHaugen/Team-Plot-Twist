from dataclasses import replace

import pytest

from logic import (
    Position,
    advance_player,
    guard_pose,
    guard_time,
    initial_state,
    key_prompt,
    open_door,
    position_xy,
    steal_key,
    with_position,
)


def near_door():
    return Position("cell", 374.0)


def test_locked_cell_wall_and_door_stop_player():
    state = initial_state()
    assert advance_player(Position("cell", 165), False, -1, 0, 1).value == 160
    stopped = advance_player(near_door(), False, 1, 0, 1)
    assert stopped == Position("cell", 380)
    assert with_position(state, Position("hold", 400)) is None


def test_guard_walks_continuously_and_returns_to_kitchen():
    before = guard_pose(guard_time("lower_up", 0.3) - 0.01)
    after = guard_pose(guard_time("lower_up", 0.3) + 0.01)
    assert abs(after.x - before.x) < 3
    assert abs(after.y - before.y) < 3
    descending = guard_pose(guard_time("lower_down", 0.5))
    ascending = guard_pose(guard_time("lower_up", 0.5))
    assert descending.segment == "lower_down"
    assert ascending.segment == "lower_up"
    assert descending.y == pytest.approx(ascending.y)
    assert guard_pose(guard_time("cycle_end", 0)).x == pytest.approx(guard_pose(0).x)


def test_steal_requires_door_position_and_guard_at_stair_foot():
    state = replace(initial_state(), position=near_door())
    too_early = steal_key(state, guard_time("lower_down", 0.3))
    assert not too_early.accepted
    assert too_early.state == state
    assert not key_prompt(state, guard_time("lower_down", 0.3))

    far = replace(state, position=Position("cell", 220))
    assert not steal_key(far, guard_time("hold_out", 0.05)).accepted
    assert key_prompt(state, guard_time("hold_out", 0.05))
    success = steal_key(state, guard_time("hold_out", 0.05))
    assert success.accepted
    assert success.state.has_key

    duplicate = steal_key(success.state, guard_time("hold_out", 0.05))
    assert not duplicate.accepted
    assert duplicate.state == success.state
    assert not key_prompt(success.state, guard_time("hold_out", 0.05))
    assert not steal_key(state, guard_time("hold_out", 0.8)).accepted


def test_door_needs_key_and_proximity_and_keeps_key():
    state = replace(initial_state(), position=near_door())
    no_key = open_door(state)
    assert not no_key.accepted
    assert no_key.state == state
    keyed = replace(state, has_key=True)
    too_far = open_door(replace(keyed, position=Position("cell", 200)))
    assert not too_far.accepted
    assert too_far.state == replace(keyed, position=Position("cell", 200))
    opened = open_door(keyed)
    assert opened.accepted
    assert opened.state.door_open
    assert opened.state.has_key
    closed = open_door(opened.state)
    assert closed.accepted and not closed.state.door_open


def test_open_route_reaches_kitchen_on_continuous_stairs():
    position = advance_player(Position("cell", 380), True, 1, 0, 0.15)
    assert position.zone == "hold"
    position = Position("hold", 440)
    for _ in range(25):
        position = advance_player(position, True, 0, 1, 0.1)
    assert position.zone == "mid"
    assert position_xy(position)[1] == pytest.approx(365)
    position = advance_player(position, True, 1, 0, 3)
    assert position == Position("dining", 1080)
    position = Position("dining", 920)
    for _ in range(25):
        position = advance_player(position, True, 0, 1, 0.1)
    assert position.zone == "kitchen"
    assert position_xy(position)[1] == pytest.approx(245)
    state = with_position(replace(initial_state(), has_key=True, door_open=True,
                                  position=Position("upper_stair", .9)), position)
    assert state is not None
    assert state.reached_kitchen
    for _ in range(25):
        position = advance_player(position, True, 0, -1, 0.1)
    assert position.zone == "dining"
