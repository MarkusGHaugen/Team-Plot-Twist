"""Cannon finale: after any ending the guards return and the player dodges 10 cannonballs.

The server owns the rules. It picks the volley from a stored seed, the page plays it and
reports the player's moves, and the server judges them. A win turns the ending into
"free" (the seventh). A loss keeps the earlier ending and allows a retry.
"""
import json
import random
from dataclasses import replace

import logic as L
from content import ENDINGS

LIVES = 3
BALLS = 10
FIRST_AT_MS = 4000          # first ball arrives after the guards have appeared
GAP_MS = 3600               # time between balls (before a little jitter)
JITTER_MS = 300
END_MS = FIRST_AT_MS + (BALLS - 1) * GAP_MS + 1500
WINDOW_BEFORE_MS = 500      # a move this long before the ball arrives still dodges it
WINDOW_AFTER_MS = 250       # and this long after
EARLY_SLACK_MS = 3000       # the report may come this much before the volley ends (latency)
MAX_MOVES = 120
MAX_ITEM_CHARS = 4000
KINDS = ('finale_start', 'finale_report', 'finale_retry')
STATUSES = ('active', 'won', 'lost')
MOVES = ('jump', 'duck')
_BASE = {'status', 'origin', 'seed', 'started', 'attempt'}
_SEED_LIMIT = 2 ** 31


def volley(seed):
    """The ten cannonballs of one attempt: a lane ('low' is jumped, 'high' is ducked) and an arrival time."""
    rng = random.Random(seed)
    return [{'lane': rng.choice(('low', 'high')),
             'at': FIRST_AT_MS + i * GAP_MS + rng.randint(-JITTER_MS, JITTER_MS)} for i in range(BALLS)]


def judge(seed, moves):
    """(dodged, hits). A low ball needs a jump and a high ball needs a duck, near its arrival time."""
    dodged = 0
    for ball in volley(seed):
        counter = 'jump' if ball['lane'] == 'low' else 'duck'
        lo, hi = ball['at'] - WINDOW_BEFORE_MS, ball['at'] + WINDOW_AFTER_MS
        if any(kind == counter and lo <= t <= hi for t, kind in moves):
            dodged += 1
    return dodged, BALLS - dodged


def _int(x):
    return type(x) is int


def valid(f):
    """Is a stored finale record well formed? (Whether it fits the ending is checked in logic.)"""
    if not isinstance(f, dict):
        return False
    status = f.get('status')
    if status not in STATUSES:
        return False
    keys = _BASE | ({'dodged', 'hits'} if status != 'active' else set())
    if set(f) != keys:
        return False
    if f['origin'] not in ENDINGS or f['origin'] == 'free':
        return False
    if not _int(f['seed']) or not 0 <= f['seed'] < _SEED_LIMIT:
        return False
    if not _int(f['started']) or f['started'] < 0:
        return False
    if not _int(f['attempt']) or not 1 <= f['attempt'] <= 1000:
        return False
    if status == 'active':
        return True
    dodged, hits = f['dodged'], f['hits']
    if not _int(dodged) or not _int(hits) or dodged < 0 or hits < 0 or dodged + hits != BALLS:
        return False
    return hits < LIVES if status == 'won' else hits >= LIVES


def _record(state):
    from logic import story_progress
    return story_progress(state).get('voyage', {}).get('finale')


def _with_record(state, record, **changes):
    from voyage import progress, save
    v = progress(state)
    v['finale'] = record
    return replace(save(state, v), **changes)


def _no(state, message):
    return L.ActionResult(state, False, message)


def start(state, now):
    if not state.ending or state.ending == 'free':
        return _no(state, 'Reach one of the endings first.')
    if _record(state) is not None:
        return _no(state, 'The guards are already after you.')
    record = {'status': 'active', 'origin': state.ending, 'seed': int(now) % _SEED_LIMIT,
              'started': int(now), 'attempt': 1}
    return L.ActionResult(_with_record(state, record), True, 'The music stops. The guards are back, with cannons!')


def _clean_moves(moves):
    if not isinstance(moves, list) or len(moves) > MAX_MOVES:
        return None
    clean = []
    for m in moves:
        if not isinstance(m, (list, tuple)) or len(m) != 2:
            return None
        t, kind = m
        if not _int(t) or not 0 <= t <= END_MS + 5000 or kind not in MOVES:
            return None
        clean.append((t, kind))
    return clean


def report(state, moves, now):
    f = _record(state)
    if f is None or f['status'] != 'active':
        return _no(state, 'There is no cannon volley to finish.')
    if int(now) - f['started'] < END_MS - EARLY_SLACK_MS:
        return _no(state, 'The volley is not over yet.')
    clean = _clean_moves(moves)
    if clean is None:
        return _no(state, 'That report of your moves is not valid.')
    dodged, hits = judge(f['seed'], clean)
    if hits < LIVES:
        record = {**f, 'status': 'won', 'dodged': dodged, 'hits': hits}
        return L.ActionResult(_with_record(state, record, ending='free'), True, ENDINGS['free']['title'])
    record = {**f, 'status': 'lost', 'dodged': dodged, 'hits': hits}
    return L.ActionResult(_with_record(state, record), True, 'The guards caught you.')


def retry(state, now):
    f = _record(state)
    if f is None or f['status'] != 'lost':
        return _no(state, 'You can only try again after being caught.')
    attempt = f['attempt'] + 1
    record = {'status': 'active', 'origin': f['origin'], 'seed': (int(now) + attempt * 7919) % _SEED_LIMIT,
              'started': int(now), 'attempt': attempt}
    return L.ActionResult(_with_record(state, record), True, 'One more try. Run!')


def dispatch(state, kind, item, now):
    """Entry point from the action pipeline (the moves arrive as a JSON string in `item`)."""
    if kind == 'finale_start':
        return start(state, now)
    if kind == 'finale_retry':
        return retry(state, now)
    if not isinstance(item, str) or len(item) > MAX_ITEM_CHARS:
        return _no(state, 'That report of your moves is not valid.')
    try:
        moves = json.loads(item)
    except ValueError:
        return _no(state, 'That report of your moves is not valid.')
    return report(state, moves, now)


def public(state):
    """What the page needs to play and draw the finale, or None when there is none."""
    f = _record(state)
    if f is None:
        return None
    done = f['status'] != 'active'
    hits = f.get('hits', 0)
    return {'status': f['status'], 'origin': f['origin'], 'attempt': f['attempt'], 'seed': f['seed'],
            'balls': volley(f['seed']), 'total': BALLS, 'lives': LIVES, 'end_ms': END_MS,
            'window_before': WINDOW_BEFORE_MS, 'window_after': WINDOW_AFTER_MS,
            'dodged': f.get('dodged', 0), 'hits': hits,
            'left': 0 if done else BALLS, 'lives_left': max(0, LIVES - hits)}
