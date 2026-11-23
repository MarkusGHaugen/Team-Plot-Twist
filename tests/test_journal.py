"""Player knowledge, route guidance and read-only journal acceptance cases."""
import json
import shutil
from dataclasses import asdict, replace

import pytest

from logic import Position, initial_state
from journal import journal_hints


def state(items=(), inspected=(), voyage=None, **changes):
    story = {'items': list(items), 'inspected': list(inspected)}
    if voyage is not None:
        story['voyage'] = voyage
    return replace(initial_state(),
                   **{'door_open': True, 'story_state': json.dumps(story), **changes})


def hints(s, now=10000):
    return {h['id']: h for h in journal_hints(s, now)}


def test_new_game_only_points_to_the_visible_letter():
    result = journal_hints(initial_state(), 10000)
    assert [h['id'] for h in result] == ['cell']
    assert 'letter' in result[0]['text'].lower()
    assert not any(word in str(result).lower() for word in ('pills', 'captain', 'dinghy', 'stew'))


def test_key_and_recapture_replace_theft_advice():
    h = hints(state(has_key=True, door_open=False, position=Position('cell', 374)))['cell']
    assert 'unlock' in h['clearer'].lower()
    assert 'steal' not in h['clearer'].lower()


@pytest.mark.parametrize('items,paid,status', [
    (['sail'], [], 'Missing equipment'),
    (['rope'], [], 'Missing equipment'),
    (['sail', 'rope'], [], 'Next action'),
    (['sail'], ['boatswain'], 'Next action'),
])
def test_dinghy_alternatives(items, paid, status):
    assert hints(state(items, voyage={'paid': paid}))['dinghy']['status'] == status


def test_open_crate_no_longer_requests_tools_and_dead_cook_blocks_it():
    s = state(inspected=['return_crate'], story_state=json.dumps({
        'items': ['crowbar'], 'inspected': ['return_crate'], 'crate_open': True}))
    assert hints(s)['crate']['status'] == 'Next action'
    assert 'crowbar' not in hints(s)['crate']['clearer'].lower()
    assert hints(replace(s, dining_alive=False))['crate']['status'] == 'Unavailable'


def test_unknown_routes_stay_hidden_even_if_the_server_knows_crew_status():
    assert set(hints(state(officer_alive=False, dining_alive=False))) == {'explore'}
    assert 'stew' not in hints(state(['sleeping_pills']))
    assert 'command' not in hints(state())


def test_personal_disguise_and_alarm_affect_command_advice():
    s = state(['captain_uniform'], ['captains_log'],
              {'captain_worn': True, 'concealed': {'officer': 'barrel_hold_a'}},
              officer_alive=False, disguised=True)
    assert hints(s)['command']['status'] == 'Next action'
    assert hints(replace(s, alert_until_ms=20000))['command']['status'] == 'Wait'
    assert hints(replace(s, disguised=False))['command']['status'] == 'Missing requirement'


def test_stew_requires_discovered_connection_and_living_cook():
    s = state(['sleeping_pills'], ['stew_pot'])
    assert hints(s)['stew']['status'] == 'Next action'
    assert hints(replace(s, dining_alive=False))['stew']['status'] == 'Unavailable'
    assert hints(replace(s, alert_until_ms=20000))['stew']['status'] == 'Wait'


def test_sleep_guidance_uses_actual_meal_times():
    import feast
    import voyage
    s = state(['sleeping_pills'], ['stew_pot'])
    v = voyage.progress(s)
    v.update(stew_drugged=True, feast=feast.plan(s, 0, 10000))
    s = voyage.save(s, v)
    assert hints(s, 10000)['stew']['status'] == 'Wait'
    asleep_at = max(v['feast']['sleep'].values()) + 1
    assert hints(s, asleep_at)['stew']['status'] == 'Opportunity'
    assert hints(s, asleep_at + 200000)['stew']['status'] == 'Plan ended'


def test_order_limit_old_saves_and_no_mutation():
    s = state(['sail', 'rope', 'crowbar'], ['captains_log', 'opening_letter', 'return_crate'])
    before = asdict(s)
    result = journal_hints(s, 10000)
    reordered = replace(s, story_state=json.dumps({
        'items': ['crowbar', 'rope', 'sail'],
        'inspected': ['return_crate', 'opening_letter', 'captains_log']}))
    assert result == journal_hints(reordered, 10000)
    assert len(result) <= 3
    assert asdict(s) == before
    assert journal_hints(replace(initial_state(), story_state='{}'), 10000)


def test_captured_and_finished_games_do_not_suggest_escaping_now():
    assert journal_hints(state(capture_phase='active'), 10000)[0]['status'] == 'Wait'
    assert journal_hints(state(ending='crate'), 10000) == []


def test_shared_discoveries_do_not_share_a_personal_captain_disguise():
    import shared_ship
    before = state()
    after = state(['captain_uniform'], ['captains_log'],
                  {'captain_worn': True, 'concealed': {'officer': 'barrel_hold_a'}},
                  officer_alive=False, disguised=True)
    partner = shared_ship.apply_world(before, shared_ship.world_changes(before, after))
    assert hints(after)['command']['status'] == 'Next action'
    assert hints(partner)['command']['status'] == 'Missing requirement'
    assert not partner.disguised


def test_paused_single_player_clock_does_not_expire_an_alarm_while_reading():
    s = state(['captain_uniform'], ['captains_log'],
              {'captain_worn': True, 'concealed': {'officer': 'barrel_hold_a'}},
              officer_alive=False, disguised=True, reading='journal',
              paused_at_ms=10000, alert_until_ms=20000)
    assert hints(s, 90000)['command']['status'] == 'Wait'
    assert hints(replace(s, paused_at_ms=0), 90000)['command']['status'] == 'Next action'


@pytest.mark.skipif(shutil.which('node') is None, reason='Node executes the Canvas controls')
def test_journal_does_not_swallow_native_space_or_arrow_key_events():
    from test_canvas_rules import canvas
    from logic import MAP_CONFIG
    data = {**asdict(initial_state()), 'rules': MAP_CONFIG,
            'reading': 'journal', 'run_id': 'journal-keys'}
    result = canvas(r'''(() => {
      const handlers={};
      globalThis.Element=class {closest(){return null;}};
      globalThis.window={addEventListener:(k,f)=>handlers[k]=f,removeEventListener:()=>{}};
      globalThis.document={querySelector:()=>null};globalThis.performance={now:()=>0};
      globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
      const el=()=>({addEventListener:()=>{},removeEventListener:()=>{},querySelector:()=>el(),
        classList:{toggle:()=>{}},lastElementChild:{},focus:()=>{}});
      mount({data:input,parentElement:{querySelector:()=>el(),querySelectorAll:()=>[]},
        key:'journal-keys',setTriggerValue:()=>{},setStateValue:()=>{}});
      let prevented=0;
      for(const key of [' ', 'ArrowDown']) for(const type of ['keydown','keyup'])
        handlers[type]({key,target:new Element(),repeat:false,preventDefault:()=>prevented++});
      return prevented;
    })()''', data)
    assert result == 0
