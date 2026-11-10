"""One shared ship for the players in a multiplayer room.

Each player keeps an ordinary save. After every accepted action, the parts of
the ship that changed (doors, keys, items, crew, alarms, the meal, endings ...)
are copied to the other players' saves. Only the fields that actually changed
are copied, so two players acting at nearly the same time never undo each
other. What belongs to one person stays theirs: where they stand, what they
hold, their hiding place, their disguise and whether a guard has caught them.

Being caught is the exception to sharing: the guards take that player back to
the cell, lock the door and search the ship for the other player for 30
seconds, starting where that player was last seen.

Multiplayer never pauses the ship while someone reads, so both players always
share one game clock, and the guards walk the same routes for both.
"""
from __future__ import annotations

import json
from dataclasses import fields, replace

import logic as L

SEARCH_MS = L.SEARCH_ALERT_MS

PERSONAL_FIELDS = frozenset({
    'position', 'facing', 'held_item', 'hidden_barrel', 'in_hammock', 'disguised', 'lamp_lit',
    'capture_phase', 'capture_guard_zone', 'capture_guard_value', 'capture_guard',
    'reading', 'paused_at_ms', 'suspect_started_ms', 'suspect_guard_zone', 'suspect_guard_value',
    'reached_kitchen',
})
WORLD_FIELDS = tuple(f.name for f in fields(L.GameState) if f.name not in PERSONAL_FIELDS and f.name != 'story_state')
PERSONAL_VOYAGE = frozenset({'duck', 'hp', 'escort', 'guide', 'captain_worn', 'capture_started', 'last_tick'})
_GONE = {'__gone__': True}  # marks a key that the action removed
HELD_NEEDS = {'cell_key': 'has_key', 'blue_key': 'has_blue_key', 'pistol': 'has_pistol', 'lamp': 'has_lamp'}

_CREATE = """
CREATE TABLE IF NOT EXISTS rooms (
  room TEXT PRIMARY KEY, epoch_ms INTEGER NOT NULL, generation INTEGER NOT NULL DEFAULT 0,
  version INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS room_members (
  room TEXT NOT NULL, save_id TEXT NOT NULL, joined_ms INTEGER NOT NULL,
  PRIMARY KEY (room, save_id));
"""


def _story(state):
    try:
        story = json.loads(state.story_state or '{}')
    except ValueError:
        story = {}
    return story if isinstance(story, dict) else {}


def world_changes(old, new) -> dict:
    """What an action changed on the shared ship, ready to copy to a partner."""
    changes = {'fields': {name: getattr(new, name) for name in WORLD_FIELDS if getattr(old, name) != getattr(new, name)},
               'story': {}, 'voyage': {}}
    before, after = _story(old), _story(new)
    for key in set(before) | set(after):
        if key == 'voyage' or before.get(key, _GONE) == after.get(key, _GONE):
            continue
        changes['story'][key] = after.get(key, _GONE)
    vb, va = before.get('voyage') or {}, after.get('voyage') or {}
    for key in set(vb) | set(va):
        if key in PERSONAL_VOYAGE or vb.get(key, _GONE) == va.get(key, _GONE):
            continue
        changes['voyage'][key] = va.get(key, _GONE)
    return changes if any(changes.values()) else {}


def apply_world(state, changes: dict):
    """Copy shared changes into a partner's save and keep their own parts valid."""
    if not changes:
        return state
    state = replace(state, **changes.get('fields', {}))
    story = _story(state)
    for key, value in changes.get('story', {}).items():
        if value == _GONE:
            story.pop(key, None)
        else:
            story[key] = value
    if changes.get('voyage'):
        voyage = dict(story.get('voyage') or {})
        for key, value in changes['voyage'].items():
            if value == _GONE:
                voyage.pop(key, None)
            else:
                voyage[key] = value
        story['voyage'] = voyage
    state = replace(state, story_state=json.dumps(story, separators=(',', ':')))
    # A partner's own choices must still make sense on the changed ship.
    need = HELD_NEEDS.get(state.held_item)
    if need and not getattr(state, need):
        state = replace(state, held_item='none')
    if state.lamp_lit and not state.has_lamp:
        state = replace(state, lamp_lit=False)
    if state.ending:
        state = replace(state, reading='', paused_at_ms=0, capture_phase='none')
    return state


def adopt_ship(fresh, partner):
    """A newcomer's save: their own fresh start in the cell, on the partner's ship."""
    changes = world_changes(fresh, partner)
    return apply_world(fresh, changes)


def unpaused(old, new):
    """Multiplayer never pauses the shared ship while a document is open."""
    return replace(new, paused_at_ms=0) if new.paused_at_ms else new


def jailed(before, guard_elapsed: float, now_ms: int, last_seen=None):
    """A caught player goes back to the locked cell; the crew search for the other."""
    start = L.initial_state()
    personal = {name: getattr(start, name) for name in PERSONAL_FIELDS}
    story = _story(before)
    if 'voyage' in story:
        # Keep the shared crew state; drop this player's own (crouching, health, guide).
        from voyage import progress
        fresh = progress(L.initial_state())
        story['voyage'] = {k: (fresh[k] if k in fresh else None) if k in PERSONAL_VOYAGE else v
                           for k, v in story['voyage'].items()
                           if k not in PERSONAL_VOYAGE or k in fresh}
    state = replace(before, **personal, door_open=False,
                    story_state=json.dumps(story, separators=(',', ':')))
    if last_seen is not None and last_seen.zone == 'cell':
        last_seen = None
    return L._start_alert(state, guard_elapsed, now_ms, first_goal=last_seen, duration_ms=SEARCH_MS)


# ---- Room bookkeeping ---------------------------------------------------------

def ensure_tables(conn):
    conn.executescript(_CREATE)


def room_info(conn, room: str) -> dict | None:
    ensure_tables(conn)
    row = conn.execute('SELECT epoch_ms, generation, version FROM rooms WHERE room=?', (room,)).fetchone()
    return None if row is None else {'epoch_ms': row[0], 'generation': row[1], 'version': row[2]}


def members(conn, room: str) -> list[str]:
    ensure_tables(conn)
    return [r[0] for r in conn.execute('SELECT save_id FROM room_members WHERE room=? ORDER BY joined_ms', (room,))]


def join(conn, room: str, save_id: str, wall_now: int) -> dict:
    """Register a player in a room. A new player starts in the cell on the shared ship."""
    from db import load_game, new_game, _write_game
    ensure_tables(conn)
    with conn:
        conn.execute('INSERT OR IGNORE INTO rooms (room, epoch_ms) VALUES (?, ?)', (room, wall_now))
        conn.execute('INSERT OR IGNORE INTO room_members (room, save_id, joined_ms) VALUES (?, ?, ?)',
                     (room, save_id, wall_now))
    if load_game(conn, save_id) is None:
        partner = next((s for s in (load_game(conn, m) for m in members(conn, room) if m != save_id) if s), None)
        if partner is None:
            new_game(conn, save_id)
        else:
            with conn:
                _write_game(conn, adopt_ship(L.initial_state(), partner), save_id)
    return room_info(conn, room)


def share(conn, room: str, save_id: str, before, after) -> bool:
    """Copy what an action changed on the ship to every other player in the room."""
    from db import load_game, _write_game
    changes = world_changes(before, after)
    if not changes:
        return False
    with conn:
        for other in members(conn, room):
            if other == save_id:
                continue
            state = load_game(conn, other)
            if state is not None:
                _write_game(conn, apply_world(state, changes), other)
        conn.execute('UPDATE rooms SET version = version + 1 WHERE room=?', (room,))
    return True


def restart(conn, room: str, wall_now: int):
    """Restart puts everyone back in the cell of a fresh ship, on a new clock."""
    from db import new_game
    for other in members(conn, room):
        new_game(conn, other)
    with conn:
        conn.execute('UPDATE rooms SET epoch_ms=?, generation = generation + 1, version = version + 1 WHERE room=?',
                     (wall_now, room))
