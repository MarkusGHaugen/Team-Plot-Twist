"""Cannon finale: after an ending the guards return and the player dodges 10 cannonballs."""
import json
import sqlite3
from dataclasses import asdict, replace
import pytest
import finale
import logic as L
from content import ENDINGS, FINALE_RESCUE_EPILOGUE
from db import connect_db, restore_game, load_game, apply_action, new_game
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
    with connect_db(':memory:') as c:
        restore_game(c,s,'p')
        db_result=apply_action(c,'finale_start',s.position,0.,'p',now_ms=T0)
        assert not db_result.accepted and db_result.state==s and load_game(c,'p')==s


@pytest.mark.parametrize('ending', ['takeover', 'crate', 'dinghy', 'command', 'lullaby', 'castaway'])
def test_every_one_of_the_six_endings_can_start_the_finale(ending):
    s = replace(ended('castaway'), ending=ending)
    f = fin(accepted(finale.start(s, T0)))
    assert f['status'] == 'active' and f['attempt'] == 1 and f['started'] == T0


def test_finale_starts_only_once():
    s = started()
    again = finale.start(s, T0 + 5000)
    assert not again.accepted and again.state == s


def test_retry_is_only_accepted_after_a_caught_result():
    s=started()
    assert not finale.retry(s,T0+1).accepted
    won=accepted(finale.report(s,perfect(fin(s)['seed']),after_volley(s)))
    assert not finale.retry(won,T0+finale.END_MS+1000).accepted


def test_escape_demo_starts_before_the_cannon_plot_twist():
    s = finale.demo_escape_state()
    assert s.ending == 'castaway'
    assert fin(s) is None
    assert state_from_backup(asdict(s)) == s


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

def test_two_hits_and_eight_dodges_win_without_changing_the_reached_ending():
    s = started()
    seed = fin(s)['seed']
    won = accepted(finale.report(s, perfect(seed, skip=(2, 5)), after_volley(s)))
    assert won.ending == s.ending == 'castaway'
    assert replace(won,story_state=s.story_state)==s
    f = fin(won)
    assert f['status'] == 'won' and (f['dodged'], f['hits']) == (8, 2)
    assert state_from_backup(asdict(won)) is not None


def test_three_hits_means_caught_and_the_earlier_ending_is_kept():
    s = started()
    seed = fin(s)['seed']
    lost = accepted(finale.report(s, perfect(seed, skip=(0, 4, 9)), after_volley(s)))
    assert lost.ending == 'castaway'
    assert replace(lost,story_state=s.story_state)==s
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


# ---- capture and restart ---------------------------------------------------

def test_caught_player_can_retry_without_resetting_the_game():
    s = started()
    lost = accepted(finale.report(s, [], after_volley(s)))
    assert 'finale_retry' in finale.KINDS
    with connect_db(':memory:') as c:
        restore_game(c, lost, 'p')
        pos = Position('kitchen', 1200.)
        retry = apply_action(c, 'finale_retry', pos, 0., 'p', None, None, T0 + finale.END_MS + 1000)
        assert retry.accepted
        saved = load_game(c, 'p')
        assert saved.ending == lost.ending == 'castaway'
        assert saved.position == lost.position and saved.story_state != initial_state().story_state
        assert saved.has_key == lost.has_key and saved.door_open == lost.door_open
        assert story_progress(saved)['items']==story_progress(lost)['items']
        assert fin(saved)['status'] == 'active' and fin(saved)['attempt'] == 2
        assert state_from_backup(asdict(saved)) == saved


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


def test_legacy_free_backup_migrates_to_its_reached_route():
    legacy={**GOOD,'origin':'castaway','status':'won','dodged':10,'hits':0}
    restored=state_from_backup(asdict(ended('free',finale_state=legacy)))
    assert restored is not None and restored.ending=='castaway'
    assert fin(restored)=={k:v for k,v in legacy.items() if k!='origin'}


def test_legacy_free_database_save_migrates_before_schema_rebuild(tmp_path):
    import db
    path=tmp_path/'legacy.sqlite3'
    old_sql=db._CREATE.replace(db._ENDING_CHECK,
        "CHECK (ending IN ('','takeover','crate','dinghy','command','lullaby','castaway','free'))")
    legacy={**GOOD,'origin':'castaway','status':'won','dodged':10,'hits':0}
    state=ended('free',finale_state=legacy)
    with sqlite3.connect(path) as conn:
        columns=('player_id',*db._KEYS)
        conn.execute(old_sql)
        conn.execute(f"INSERT INTO progress ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                     ('p',*db._values(state)))
    with db.connect_db(path) as conn:
        restored=load_game(conn,'p')
        assert restored.ending=='castaway' and fin(restored)=={k:v for k,v in legacy.items() if k!='origin'}
        assert state_from_backup(asdict(restored))==restored


def tampered(finale_state, ending='castaway'):
    return state_from_backup(asdict(ended(ending, finale_state=finale_state)))


GOOD = {'status': 'active', 'seed': 5, 'started': T0, 'attempt': 1}


def test_valid_finale_saves_round_trip():
    for record in (GOOD,{**GOOD, 'status': 'lost', 'dodged': 6, 'hits': 4},
                   {**GOOD, 'status': 'won', 'dodged': 9, 'hits': 1}):
        state=ended(finale_state=record)
        assert state_from_backup(asdict(state))==state
        with connect_db(':memory:') as c:
            assert restore_game(c,state,'p')
            assert load_game(c,'p')==state


@pytest.mark.parametrize('bad', [
    {**GOOD, 'status': 'done'}, {**GOOD, 'origin': 'castaway'},
    {**GOOD, 'seed': -1}, {**GOOD, 'seed': 1.5}, {**GOOD, 'started': -5}, {**GOOD, 'attempt': 0},
    {**GOOD, 'extra': 1}, {'status': 'active'},
    {**GOOD, 'status': 'lost', 'dodged': 7, 'hits': 2}, {**GOOD, 'status': 'lost', 'dodged': 10, 'hits': 0},
    {**GOOD, 'status': 'lost', 'dodged': 3, 'hits': 3, 'extra': 0},
    {**GOOD, 'dodged': 5, 'hits': 5}, 'active', [],
])
def test_tampered_finale_saves_are_rejected(bad):
    assert tampered(bad) is None


def test_finale_result_requires_an_ending_but_does_not_replace_it():
    won = {**GOOD, 'status': 'won', 'dodged': 10, 'hits': 0}
    assert tampered(won, ending='castaway') is not None
    assert tampered(GOOD, ending='') is None
    assert tampered(None, ending='') is not None


def test_a_finale_save_needs_an_ending():
    s = replace(ended(finale_state=GOOD), ending='')
    assert state_from_backup(asdict(s)) is None


def test_six_routes_and_rescue_epilogue_are_separate():
    assert 'free' not in ENDINGS
    assert FINALE_RESCUE_EPILOGUE['title'] and FINALE_RESCUE_EPILOGUE['body']
    assert len(ENDINGS) == 6
    assert all(e['subtitle'].startswith('Ending ') and 'of 6' in e['subtitle'] for e in ENDINGS.values())


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
        assert done.accepted and load_game(c, 'p').ending == 'castaway'
        assert fin(load_game(c, 'p'))['status'] == 'won'
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


def test_restart_action_cannot_bypass_new_game_confirmation_and_new_game_resets_both(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        s = started()
        won = accepted(finale.report(s, perfect(fin(s)['seed']), after_volley(s)))
        restore_game(c, won, 'p')
        pos=Position('kitchen', 1200.)
        for item in (None,'confirmed'):
            denied=apply_action(c, 'restart_game', pos, 0., 'p', None, item, T0 + 10 ** 6)
            assert not denied.accepted and load_game(c, 'p')==won
        fresh=new_game(c, 'p')
        assert fresh==initial_state() and story_progress(load_game(c, 'p')).get('voyage',{}).get('finale') is None
        restore_game(c, s, 'q')
        fresh=new_game(c, 'q')
        assert fresh==initial_state() and story_progress(load_game(c, 'q')).get('voyage',{}).get('finale') is None


def test_ordinary_actions_after_an_ending_are_rejected_without_changes(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        s=started()
        restore_game(c,s,'p')
        for kind,item in (('journal',None),('story_inspect','captains_log'),('move',None),('restart_prompt',None)):
            result=apply_action(c,kind,s.position,0.,'p',None,item,T0+100)
            assert not result.accepted and result.state==s and load_game(c,'p')==s


def test_other_actions_stay_blocked_during_the_finale(tmp_path):
    with connect_db(tmp_path / 'f.sqlite3') as c:
        restore_game(c, started(), 'p')
        assert not apply_action(c, 'journal', Position('kitchen', 1200.), 0., 'p', None, None, T0).accepted


def test_demo_state_is_a_valid_save_already_in_the_finale():
    s = finale.demo_state(T0)
    assert state_from_backup(asdict(s)) is not None
    assert fin(s)['status'] == 'active' and len(finale.public(s)['balls']) == 10


# ---- multiplayer: one shared ship, so one shared finale -------------------------

def test_finale_is_shared_in_a_room_and_every_save_stays_valid():
    import shared_ship
    a, b = ended(), ended()
    a2 = accepted(finale.start(a, T0))
    b2 = shared_ship.apply_world(b, shared_ship.world_changes(a, a2))
    assert fin(b2) == fin(a2) and state_from_backup(asdict(b2)) is not None
    won = accepted(finale.report(a2, perfect(fin(a2)['seed']), after_volley(a2)))
    b3 = shared_ship.apply_world(b2, shared_ship.world_changes(a2, won))
    assert b3.ending == 'castaway' and fin(b3)['status'] == 'won' and state_from_backup(asdict(b3)) is not None
    lost = accepted(finale.report(a2, [], after_volley(a2)))
    b4 = shared_ship.apply_world(b2, shared_ship.world_changes(a2, lost))
    assert b4.ending == 'castaway' and fin(b4)['status'] == 'lost' and state_from_backup(asdict(b4)) is not None


# ---- the page and the server agree ---------------------------------------------

@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_canvas_finale_constants_match_the_server():
    js = canvas('FINALE', {})
    assert js == {'balls': finale.BALLS, 'lives': finale.LIVES, 'endMs': finale.END_MS,
                  'windowBefore': finale.WINDOW_BEFORE_MS, 'windowAfter': finale.WINDOW_AFTER_MS}


def test_cannonballs_are_spaced_about_one_second_apart():
    assert finale.GAP_MS == 1000
    assert finale.END_MS == 20_500


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_beach_music_switches_from_celebration_to_the_guard_theme():
    data = {'ending': 'castaway', 'finale': {'status': 'active'}}
    assert canvas('finaleCelebrationNow(input.data,{t:1000})', {'data': data})
    assert not canvas('finaleDarkNow(input.data,{t:6699})', {'data': data})
    assert canvas('finaleDarkNow(input.data,{t:6700})', {'data': data})
    assert canvas('finaleCelebrationNow(input.data,{t:6699})', {'data': data})
    assert not canvas('finaleCelebrationNow(input.data,{t:6700})', {'data': data})


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_rescue_restores_cheerful_music_and_names_the_plot_twist():
    data = {'ending': 'castaway', 'finale': {'status': 'won'}}
    assert canvas('finaleRescueNow(input.data)', {'data': data})
    assert not canvas('finaleRescueNow(input.data)', {'data': {'ending':'castaway','finale':{'status':'active'}}})
    source = __import__('pathlib').Path('game_component/game.js').read_text()
    assert 'PLOT TWIST: THE GUARDS ARE BACK!' in source
    assert 'You thought you were free…' in source
    from content import DOCUMENTS
    assert 'after you jumped in to save your dog' in DOCUMENTS['opening_letter']['body']
    assert 'falsifying the cargo manifests' in DOCUMENTS['opening_letter']['body']


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_caught_screen_waits_until_the_capture_scene_finishes():
    data={'ending':'castaway','finale':{'status':'lost'}}
    assert not canvas('finaleCaughtReady(input.data,input.fin)', {'data':data,'fin':{'captureT':6499}})
    assert canvas('finaleCaughtReady(input.data,input.fin)', {'data':data,'fin':{'captureT':6500}})


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_cannonball_inputs_wait_until_the_beach_scene_ends():
    data = {'ending': 'castaway', 'finale': {'status': 'active'}}
    client = {'data': data, 'fin': {'t': 1000, 'over': False, 'moves': []}}
    result = canvas('(()=>{const consumed=finaleKey(input.client," ",false);return [consumed,input.client.fin.moves];})()',
                    {'client': client})
    assert result == [True, []]


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_beach_twist_and_captured_return_scenes_render_without_errors():
    expression = r'''(() => {
      const ctx=new Proxy({}, {get:(_,key)=>key==='createLinearGradient'||key==='createRadialGradient'
        ?()=>({addColorStop:()=>{}}):()=>{}, set:()=>true});
      drawBeachTwist(ctx,900,500,input.t);
      drawCapturedReturn(ctx,900,500,6500);
      return true;
    })()'''
    assert canvas(expression, {'t': 7000})


@pytest.mark.skipif(NODE is None, reason='Node is needed to execute the actual Canvas rules')
def test_canvas_judges_a_volley_like_the_server():
    seed = 11
    volley = finale.volley(seed)
    for moves in (perfect(seed), [], perfect(seed, skip=(1, 3, 8)),
                  [[b['at'] - 400, 'duck'] for b in volley], [[b['at'] + 200, 'jump'] for b in volley]):
        got = canvas('finaleJudge(input.balls,input.moves)', {'balls': volley, 'moves': moves})
        assert tuple(got) == finale.judge(seed, moves)
