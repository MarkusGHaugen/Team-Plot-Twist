"""Cannon finale: after an ending the guards return and the player dodges 10 cannonballs."""
import json
from dataclasses import asdict, replace
import pytest
import finale
import logic as L
from content import ENDINGS
from db import connect_db, restore_game, load_game, apply_action
from logic import Position, initial_state, state_from_backup, story_progress
from test_canvas_rules import canvas, NODE

T0 = 1_000_000


def ended(ending='castaway', finale_state=None, **changes):
    """A valid save that has just reached one of the six endings."""
    voyage = {'watch_start': 0}
    if finale_state is not None:
        voyage['finale'] = finale_state
    return replace(initial_state(), has_key=True, door_open=True, reached_kitchen=True,
                   position=Position('kitchen', 1200.), ending=ending,
                   story_state=json.dumps({'items': ['sleeping_pills'], 'voyage': voyage}), **changes)


def accepted(result):
    assert result.accepted, result.message
    return result.state


def fin(state):
    return story_progress(state)['voyage'].get('finale')


def perfect(seed, skip=()):
    """The right move for every ball, made exactly when the ball arrives."""
    return [[b['at'], 'jump' if b['lane'] == 'low' else 'duck']
            for i, b in enumerate(finale.volley(seed)) if i not in skip]


def after_volley(state):
    return fin(state)['started'] + finale.END_MS + 500


def started(**kw):
    return accepted(finale.start(ended(**kw), T0))


# ---- starting -------------------------------------------------------------

def test_finale_cannot_start_before_an_ending_and_nothing_changes():
    s = replace(ended(), ending='')
    result = finale.start(s, T0)
    assert not result.accepted and result.state == s


@pytest.mark.parametrize('ending', ['takeover', 'crate', 'dinghy', 'command', 'lullaby', 'castaway'])
def test_every_one_of_the_six_endings_can_start_the_finale(ending):
    s = replace(ended('castaway'), ending=ending)
    f = fin(accepted(finale.start(s, T0)))
    assert f['status'] == 'active' and f['origin'] == ending and f['attempt'] == 1 and f['started'] == T0


def test_finale_starts_only_once():
    s = started()
    again = finale.start(s, T0 + 5000)
    assert not again.accepted and again.state == s


def test_finale_cannot_start_after_it_was_won():
    won = accepted(finale.report(started(), perfect(fin(started())['seed']), T0 + finale.END_MS + 500))
    assert not finale.start(won, T0 + 99_999).accepted


# ---- the volley -----------------------------------------------------------

def test_volley_has_exactly_ten_balls_in_order_and_is_repeatable():
    v = finale.volley(1234)
    assert len(v) == finale.BALLS == 10
    assert v == finale.volley(1234)
    assert all(b['lane'] in ('low', 'high') for b in v)
    assert [b['at'] for b in v] == sorted({b['at'] for b in v})
    assert v[0]['at'] > 0 and v[-1]['at'] < finale.END_MS


def test_different_seeds_give_different_volleys():
    assert len({tuple(b['lane'] for b in finale.volley(s)) for s in range(40)}) > 1


# ---- dodging --------------------------------------------------------------

def test_low_balls_are_jumped_and_high_balls_are_ducked():
    seed = 7
    v = finale.volley(seed)
    assert finale.judge(seed, perfect(seed)) == (10, 0)
    wrong = [[b['at'], 'duck' if b['lane'] == 'low' else 'jump'] for b in v]
    assert finale.judge(seed, wrong) == (0, 10)


def test_no_moves_means_every_ball_hits():
    assert finale.judge(7, []) == (0, 10)


def test_a_move_outside_the_window_does_not_dodge():
    seed = 7
    b = finale.volley(seed)[0]
    right = 'jump' if b['lane'] == 'low' else 'duck'
    early = [[b['at'] - finale.WINDOW_BEFORE_MS - 1, right]]
    late = [[b['at'] + finale.WINDOW_AFTER_MS + 1, right]]
    edge = [[b['at'] - finale.WINDOW_BEFORE_MS, right]]
    assert finale.judge(seed, early)[0] == 0 and finale.judge(seed, late)[0] == 0
    assert finale.judge(seed, edge)[0] == 1


def test_one_move_cannot_dodge_two_balls():
    seed = 7
    v = finale.volley(seed)
    assert min(b2['at'] - b1['at'] for b1, b2 in zip(v, v[1:])) > finale.WINDOW_BEFORE_MS + finale.WINDOW_AFTER_MS


# ---- reporting the result -------------------------------------------------

def test_two_hits_and_eight_dodges_still_wins_and_records_the_ending():
    s = started()
    seed = fin(s)['seed']
    won = accepted(finale.report(s, perfect(seed, skip=(2, 5)), after_volley(s)))
    assert won.ending == 'free'
    f = fin(won)
    assert f['status'] == 'won' and f['origin'] == 'castaway' and (f['dodged'], f['hits']) == (8, 2)
    assert state_from_backup(asdict(won)) is not None


def test_three_hits_means_caught_and_the_earlier_ending_is_kept():
    s = started()
    seed = fin(s)['seed']
    lost = accepted(finale.report(s, perfect(seed, skip=(0, 4, 9)), after_volley(s)))
    assert lost.ending == 'castaway'
    f = fin(lost)
    assert f['status'] == 'lost' and (f['dodged'], f['hits']) == (7, 3)
    assert story_progress(lost)['items'] == ['sleeping_pills']
    assert state_from_backup(asdict(lost)) is not None


def test_a_perfect_run_wins():
    s = started()
    won = accepted(finale.report(s, perfect(fin(s)['seed']), after_volley(s)))
    assert (fin(won)['dodged'], fin(won)['hits']) == (10, 0)


def test_reporting_victory_too_early_is_rejected_and_nothing_changes():
    s = started()
    early = finale.report(s, perfect(fin(s)['seed']), T0 + finale.END_MS - finale.EARLY_SLACK_MS - 1)
    assert not early.accepted and early.state == s


@pytest.mark.parametrize('moves', [
    'jump', [[100]], [[100, 'fly']], [['x', 'jump']], [[-1, 'jump']], [[True, 'jump']],
    [[100.5, 'jump']], [[10 ** 9, 'jump']], [[100, 'jump']] * 500, None,
])
def test_malformed_move_reports_are_rejected(moves):
    s = started()
    result = finale.report(s, moves, after_volley(s))
    assert not result.accepted and result.state == s


def test_report_without_an_active_finale_is_rejected():
    s = ended()
    assert not finale.report(s, [], T0 + 99_999).accepted
    won = accepted(finale.report(started(), perfect(fin(started())['seed']), T0 + finale.END_MS + 500))
    assert not finale.report(won, [], T0 + 999_999).accepted


# ---- retry ----------------------------------------------------------------

def test_retry_after_a_loss_starts_a_fresh_attempt_and_keeps_everything_earned():
    s = started()
    lost = accepted(finale.report(s, [], after_volley(s)))
    again = accepted(finale.retry(lost, T0 + 90_000))
    f = fin(again)
    assert f['status'] == 'active' and f['attempt'] == 2 and f['origin'] == 'castaway'
    assert 'hits' not in f and again.ending == 'castaway'
    assert story_progress(again)['items'] == ['sleeping_pills']
    assert len(finale.volley(f['seed'])) == 10


def test_retry_is_rejected_unless_the_player_was_caught():
    s = started()
    assert not finale.retry(s, T0 + 1).accepted
    assert not finale.retry(ended(), T0 + 1).accepted
    won = accepted(finale.report(s, perfect(fin(s)['seed']), after_volley(s)))
    assert not finale.retry(won, T0 + 99_999).accepted


# ---- what the page is told --------------------------------------------------

def test_public_view_has_the_counter_lives_and_volley():
    assert finale.public(ended()) is None
    p = finale.public(started())
    assert p['status'] == 'active' and p['balls'] == finale.volley(fin(started())['seed'])
    assert p['total'] == 10 and p['lives'] == finale.LIVES == 3 and p['end_ms'] == finale.END_MS
    lost = accepted(finale.report(started(), [], after_volley(started())))
    q = finale.public(lost)
    assert q['status'] == 'lost' and q['hits'] == 10 and q['left'] == 0 and q['lives_left'] == 0


# ---- saves ----------------------------------------------------------------

def test_old_ended_saves_without_a_finale_still_load():
    s = ended()
    assert fin(s) is None and state_from_backup(asdict(s)) is not None


def tampered(finale_state, ending='castaway'):
    return state_from_backup(asdict(ended(ending, finale_state=finale_state)))


GOOD = {'status': 'active', 'origin': 'castaway', 'seed': 5, 'started': T0, 'attempt': 1}


def test_valid_finale_saves_round_trip():
    assert tampered(GOOD) is not None
    assert tampered({**GOOD, 'status': 'lost', 'dodged': 6, 'hits': 4}) is not None
    assert tampered({**GOOD, 'status': 'won', 'dodged': 9, 'hits': 1}, ending='free') is not None


@pytest.mark.parametrize('bad', [
    {**GOOD, 'status': 'done'}, {**GOOD, 'origin': 'free'}, {**GOOD, 'origin': 'nope'},
    {**GOOD, 'seed': -1}, {**GOOD, 'seed': 1.5}, {**GOOD, 'started': -5}, {**GOOD, 'attempt': 0},
    {**GOOD, 'extra': 1}, {'status': 'active'},
    {**GOOD, 'status': 'lost', 'dodged': 7, 'hits': 2}, {**GOOD, 'status': 'lost', 'dodged': 10, 'hits': 0},
    {**GOOD, 'status': 'lost', 'dodged': 3, 'hits': 3, 'extra': 0},
    {**GOOD, 'dodged': 5, 'hits': 5}, 'active', [],
])
def test_tampered_finale_saves_are_rejected(bad):
    assert tampered(bad) is None


def test_a_won_finale_needs_the_free_ending_and_the_free_ending_needs_a_win():
    won = {**GOOD, 'status': 'won', 'dodged': 10, 'hits': 0}
    assert tampered(won, ending='castaway') is None
    assert tampered(GOOD, ending='free') is None
    assert tampered(None, ending='free') is None


def test_a_finale_save_needs_an_ending():
    s = replace(ended(finale_state=GOOD), ending='')
    assert state_from_backup(asdict(s)) is None


def test_free_ending_is_the_seventh_and_has_text():
    assert ENDINGS['free']['title'] and ENDINGS['free']['body']
    assert all(e['subtitle'].startswith('Ending ') and 'of 7' in e['subtitle'] for e in ENDINGS.values())


# ---- through the database and the action pipeline ---------------------------

def test_actions_work_through_the_database_and_survive_a_reload(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        restore_game(c, ended(), 'p')
        pos = Position('kitchen', 1200.)
        r = apply_action(c, 'finale_start', pos, 0., 'p', None, None, T0)
        assert r.accepted
        seed = fin(load_game(c, 'p'))['seed']
        assert fin(load_game(c, 'p'))['status'] == 'active'
        early = apply_action(c, 'finale_report', pos, 0., 'p', None, json.dumps(perfect(seed)), T0 + 1000)
        assert not early.accepted and fin(load_game(c, 'p'))['status'] == 'active'
        done = apply_action(c, 'finale_report', pos, 0., 'p', None, json.dumps(perfect(seed)), T0 + finale.END_MS + 500)
        assert done.accepted and load_game(c, 'p').ending == 'free'
        assert fin(load_game(c, 'p'))['hits'] == 0


def test_rejected_finale_actions_do_not_write_to_the_save(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        restore_game(c, replace(ended(), ending=''), 'p')
        before = c.total_changes
        pos = Position('kitchen', 1200.)
        for kind in ('finale_start', 'finale_report', 'finale_retry'):
            assert not apply_action(c, kind, pos, 0., 'p', None, '[]', T0).accepted
        assert c.total_changes == before


def test_a_bad_item_string_is_rejected_not_crashed(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        restore_game(c, started(), 'p')
        pos = Position('kitchen', 1200.)
        for item in (None, '', 'not json', '{"a":1}', '[' * 5000):
            assert not apply_action(c, 'finale_report', pos, 0., 'p', None, item, T0 + finale.END_MS + 500).accepted
        assert fin(load_game(c, 'p'))['status'] == 'active'


def test_restart_still_works_after_the_free_ending(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        s = started()
        won = accepted(finale.report(s, perfect(fin(s)['seed']), after_volley(s)))
        restore_game(c, won, 'p')
        r = apply_action(c, 'restart_game', Position('kitchen', 1200.), 0., 'p', None, None, T0 + 10 ** 6)
        assert r.accepted and load_game(c, 'p').ending == ''


def test_other_actions_stay_blocked_during_the_finale(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        restore_game(c, started(), 'p')
        assert not apply_action(c, 'journal', Position('kitchen', 1200.), 0., 'p', None, None, T0).accepted


# ---- the page and the server agree ---------------------------------------------

@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_canvas_finale_constants_match_the_server():
    js = canvas('FINALE', {})
    assert js == {'balls': finale.BALLS, 'lives': finale.LIVES, 'endMs': finale.END_MS,
                  'windowBefore': finale.WINDOW_BEFORE_MS, 'windowAfter': finale.WINDOW_AFTER_MS}


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_canvas_judges_a_volley_like_the_server():
    seed = 11
    volley = finale.volley(seed)
    for moves in (perfect(seed), [], perfect(seed, skip=(1, 3, 8)),
                  [[b['at'] - 400, 'duck'] for b in volley], [[b['at'] + 200, 'jump'] for b in volley]):
        got = canvas('finaleJudge(input.balls,input.moves)', {'balls': volley, 'moves': moves})
        assert tuple(got) == finale.judge(seed, moves)
