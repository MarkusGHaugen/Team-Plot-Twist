"""Keep online play responsive: fewer server round trips, without changing the rules."""
from dataclasses import asdict, replace
import json

import pytest

import logic as L
from logic import FLOORS, Position, initial_state, story_progress
from voyage import crew_tick
from test_canvas_rules import canvas, NODE

NOW0 = 50_000


def watching_state():
    """A fresh game after the first crew tick has started the watch rota."""
    s = initial_state()
    first = crew_tick(replace(s, position=Position('cell', 300)), NOW0)
    assert first.accepted and 'watch_start' in story_progress(first.state)['voyage']
    return first.state


def client_data(s):
    return {**asdict(s), 'story': story_progress(s),
            'rules': {**L.MAP_CONFIG, 'watch_path': L.route_points(Position('cabin', 300), Position('chest_room', 1320))},
            'guard_routes': {k: [asdict(x) for x in r] for k, r in L.GUARD_ROUTES.items()}}


def tick_needed(cases):
    return canvas(r'''input.cases.map(([d,p,t])=>crewTickNeeded({...d,paused_at_ms:t,paused_total_ms:0},p))''',
                  {'cases': cases})


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas rules')
def test_client_ticks_whenever_the_server_could_spot_the_player():
    s = watching_state()
    d = client_data(s)
    positions = [Position(z, float(x)) for z, (a, b, _) in FLOORS.items() if z != 'cell'
                 for x in range(int(a), int(b) + 1, 30)]
    spotted, far = [], []
    for t in range(NOW0 + 1000, NOW0 + 105_000, 1500):
        for p in positions:
            r = crew_tick(replace(s, position=p), t)
            (spotted if r.state.capture_phase == 'active' else far).append([d, asdict(p), t])
    assert len(spotted) > 20, 'the sweep must include real sightings'
    assert all(tick_needed(spotted)), 'a skipped tick would let the sleeper miss the player'
    # The point of the change: most of the ship needs no tick at all.
    sample = far[::7]
    assert sum(tick_needed(sample)) < len(sample) * .4


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas rules')
def test_fights_escorts_and_the_first_tick_always_reach_the_server():
    s = watching_state()
    far = asdict(Position('kitchen', 1200))
    fresh = client_data(initial_state())
    v = story_progress(s)['voyage']
    armed = client_data(replace(s, story_state=json.dumps({**story_progress(s), 'voyage': {**v, 'armed': True}})))
    escort = client_data(replace(s, story_state=json.dumps({**story_progress(s), 'voyage': {**v, 'escort': {'kind': 'officer'}}})))
    hidden = client_data(replace(s, hidden_barrel='barrel_hold'))
    near_sleeper = asdict(Position('cabin', 330))
    t = NOW0 + 60_000
    assert tick_needed([[fresh, far, t], [armed, far, t], [escort, far, t], [hidden, near_sleeper, t]]) == [True, True, True, False]


class FakeSessionState(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


def test_actions_are_applied_before_the_page_runs(tmp_path, monkeypatch):
    """One script run per key press: the callback saves the action first."""
    import app
    from db import connect_db, load_game, restore_game
    path = tmp_path / 'callback.sqlite3'
    monkeypatch.setattr(app, 'DB_PATH', path)
    s = replace(initial_state(), has_key=True, door_open=True, position=Position('mid', 540))
    with connect_db(path) as c:
        assert restore_game(c, s, 'one')
    action = {'request_id': 'r1', 'run_id': 'run', 'kind': 'wardrobe', 'position': {'zone': 'mid', 'value': 540},
              'guard_elapsed': 0, 'facing': 'right', 'item': None}
    session = FakeSessionState(run_id='run', feedback_seq=3, feedback_request_id='', feedback_text='',
                               feedback_accepted=False, game_canvas_one={'action': action})
    monkeypatch.setattr(app.st, 'session_state', session)
    app.apply_game_action('one')
    with connect_db(path) as c:
        assert load_game(c, 'one').wardrobe_open
    assert session.feedback_seq == 4 and session.feedback_request_id == 'r1' and session.feedback_accepted
    assert session.action_applied
    # The page's position snapshot is skipped in that run; nothing else changes.
    session.game_canvas_one = {'position': {'zone': 'mid', 'value': 540}}
    session.feedback_seq = 9
    app.apply_game_action('one')
    assert session.feedback_seq == 9


def test_the_page_no_longer_reruns_after_every_action():
    from pathlib import Path
    source = Path('app.py').read_text()
    body = source[source.index('on_action_change='):]
    assert 'on_action_change=partial(apply_game_action' in source
    assert 'handle_action(' not in body and 'st.rerun()' not in body
