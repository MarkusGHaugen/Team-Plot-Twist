"""SQLite persistence for browser-specific player progress."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, fields
from dataclasses import replace
from pathlib import Path
from content import ENDINGS
from logic import (ActionResult, GameState, Position, change_outfit, finish_capture,
    initial_state, open_door, raise_alert, search_crate, select_item, shoot_guard,
    start_capture, state_from_backup, steal_blue_key, steal_key, take_pistol,
    toggle_barrel, toggle_hammock, toggle_wardrobe, toggle_lamp, unlock_chest,
    notice_wardrobe, inspect_disguise, take_lamp, GUARD_ROUTES, with_position,
    story_action, game_now_ms)

_COLUMNS = {
    'has_blue_key': 'INTEGER NOT NULL DEFAULT 0 CHECK (has_blue_key IN (0,1))',
    'chest_open': 'INTEGER NOT NULL DEFAULT 0 CHECK (chest_open IN (0,1))',
    'has_pistol': 'INTEGER NOT NULL DEFAULT 0 CHECK (has_pistol IN (0,1))',
    'in_hammock': 'INTEGER NOT NULL DEFAULT 0 CHECK (in_hammock IN (0,1))',
    'patrol_alive': 'INTEGER NOT NULL DEFAULT 1 CHECK (patrol_alive IN (0,1))',
    'sleeper_alive': 'INTEGER NOT NULL DEFAULT 1 CHECK (sleeper_alive IN (0,1))',
    'patrol_corpse_x': 'REAL', 'patrol_corpse_y': 'REAL',
    'facing': "TEXT NOT NULL DEFAULT 'right' CHECK (facing IN ('left','right'))",
    'held_item': "TEXT NOT NULL DEFAULT 'none' CHECK (held_item IN ('none','cell_key','blue_key','pistol','lamp'))",
    'hidden_barrel': "TEXT NOT NULL DEFAULT ''",
    'wardrobe_open': 'INTEGER NOT NULL DEFAULT 0 CHECK (wardrobe_open IN (0,1))',
    'disguised': 'INTEGER NOT NULL DEFAULT 0 CHECK (disguised IN (0,1))',
    'door_alerted': 'INTEGER NOT NULL DEFAULT 0 CHECK (door_alerted IN (0,1))',
    'alert_started_ms': 'INTEGER NOT NULL DEFAULT 0',
    'alert_until_ms': 'INTEGER NOT NULL DEFAULT 0',
    'capture_phase': "TEXT NOT NULL DEFAULT 'none' CHECK (capture_phase IN ('none','active'))",
    'capture_guard_zone': "TEXT NOT NULL DEFAULT ''",
    'capture_guard_value': 'REAL NOT NULL DEFAULT 0',
    'dining_alive': 'INTEGER NOT NULL DEFAULT 1 CHECK (dining_alive IN (0,1))',
    'cargo_alive': 'INTEGER NOT NULL DEFAULT 1 CHECK (cargo_alive IN (0,1))',
    'lookout_alive': 'INTEGER NOT NULL DEFAULT 1 CHECK (lookout_alive IN (0,1))',
    'dining_corpse_x':'REAL','dining_corpse_y':'REAL',
    'cargo_corpse_x':'REAL','cargo_corpse_y':'REAL',
    'lookout_corpse_x':'REAL','lookout_corpse_y':'REAL',
    'has_lamp':'INTEGER NOT NULL DEFAULT 0 CHECK (has_lamp IN (0,1))',
    'lamp_lit':'INTEGER NOT NULL DEFAULT 0 CHECK (lamp_lit IN (0,1))',
    'wardrobe_contents':"TEXT NOT NULL DEFAULT 'uniform' CHECK (wardrobe_contents IN ('uniform','player_clothes'))",
    'suspect_started_ms':'INTEGER NOT NULL DEFAULT 0',
    'patrol_pause_ms':'INTEGER NOT NULL DEFAULT 0',
    'capture_guard':"TEXT NOT NULL DEFAULT 'patrol'",
    'alert_paths':"TEXT NOT NULL DEFAULT '{}'",
    'alert_resume':"TEXT NOT NULL DEFAULT '{}'",
}
_COLUMNS.update({
    'lamp_revealed':'INTEGER NOT NULL DEFAULT 0 CHECK (lamp_revealed IN (0,1))',
    'wardrobe_suspected':'INTEGER NOT NULL DEFAULT 0 CHECK (wardrobe_suspected IN (0,1))',
    'suspect_guard_zone':"TEXT NOT NULL DEFAULT ''",
    'suspect_guard_value':'REAL NOT NULL DEFAULT 0',
    'patrol_resume_ms':'INTEGER NOT NULL DEFAULT 0',
    'patrol_resume_elapsed':'REAL NOT NULL DEFAULT 0',
})
for _kind in GUARD_ROUTES:
    _COLUMNS.setdefault(f'{_kind}_alive',f'INTEGER NOT NULL DEFAULT 1 CHECK ({_kind}_alive IN (0,1))')
    _COLUMNS.setdefault(f'{_kind}_corpse_x','REAL')
    _COLUMNS.setdefault(f'{_kind}_corpse_y','REAL')
# Ending IDs come from the same source as game and browser-save validation.
_ENDING_VALUES = ','.join("'" + ending.replace("'", "''") + "'" for ending in ('', *ENDINGS))
_ENDING_CHECK = f'CHECK (ending IN ({_ENDING_VALUES}))'
_COLUMNS.update({
    'story_state': "TEXT NOT NULL DEFAULT '{}'",
    'ending': f"TEXT NOT NULL DEFAULT '' {_ENDING_CHECK}",
    'reading': "TEXT NOT NULL DEFAULT ''",
    'paused_at_ms': 'INTEGER NOT NULL DEFAULT 0',
    'paused_total_ms': 'INTEGER NOT NULL DEFAULT 0',
})
_KEYS = ('zone','position_value','has_key','door_open','reached_kitchen',*_COLUMNS)
_CREATE = """CREATE TABLE IF NOT EXISTS progress (
player_id TEXT PRIMARY KEY, zone TEXT NOT NULL, position_value REAL NOT NULL,
has_key INTEGER NOT NULL, door_open INTEGER NOT NULL, reached_kitchen INTEGER NOT NULL,
""" + ',\n'.join(f'{key} {sql}' for key,sql in _COLUMNS.items()) + ')'

def _progress_schema(conn: sqlite3.Connection) -> tuple[set[str], bool]:
    definition = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='progress'"
    ).fetchone()
    if definition is None:
        return set(), False
    columns = {row['name'] for row in conn.execute('PRAGMA table_info(progress)')}
    sql = definition['sql']
    rebuild = (
        'player_id' not in columns
        or ('held_item' in columns and "'lamp'" not in sql)
        or ('ending' in columns and _ENDING_CHECK not in sql)
    )
    return columns, rebuild


def connect_db(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        columns, rebuild = _progress_schema(conn)
        if not rebuild and _COLUMNS.keys() <= columns:
            return conn

        # Serialize schema changes and recheck after another session may have migrated.
        # An explicit transaction also rolls back SQLite DDL if copying a save fails.
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            columns, rebuild = _progress_schema(conn)
            if rebuild:
                conn.execute('ALTER TABLE progress RENAME TO progress_legacy')
                if {'ending','story_state','player_id'} <= columns:
                    for old in conn.execute("SELECT player_id,story_state FROM progress_legacy WHERE ending='free'").fetchall():
                        try:
                            story=json.loads(old['story_state'])
                            finale_record=story.get('voyage',{}).get('finale',{})
                            route=finale_record.get('origin')
                            if finale_record.get('status')=='won' and route in ENDINGS:
                                finale_record.pop('origin',None)
                                conn.execute("UPDATE progress_legacy SET ending=?,story_state=? WHERE player_id=?",
                                    (route,json.dumps(story,separators=(',',':')),old['player_id']))
                        except (ValueError,TypeError,AttributeError):
                            continue
                conn.execute(_CREATE)
                shared = ','.join(key for key in _KEYS if key in columns)
                if 'player_id' in columns:
                    conn.execute(f"INSERT INTO progress (player_id,{shared}) "
                                 f"SELECT player_id,{shared} FROM progress_legacy")
                else:
                    conn.execute(f"INSERT INTO progress (player_id,{shared}) "
                                 f"SELECT 'local',{shared} FROM progress_legacy WHERE id=1")
                conn.execute('DROP TABLE progress_legacy')
            elif not columns:
                conn.execute(_CREATE)
            else:
                for key, sql in _COLUMNS.items():
                    if key not in columns:
                        conn.execute(f'ALTER TABLE progress ADD COLUMN {key} {sql}')

            if columns and 'held_item' not in columns:
                conn.execute("""UPDATE progress SET held_item = CASE
                    WHEN has_pistol=1 THEN 'pistol'
                    WHEN has_blue_key=1 THEN 'blue_key'
                    WHEN has_key=1 THEN 'cell_key' ELSE 'none' END""")
            if columns and 'wardrobe_contents' not in columns:
                conn.execute("UPDATE progress SET wardrobe_contents=CASE WHEN disguised=1 THEN 'player_clothes' ELSE 'uniform' END")
            if columns and 'lamp_revealed' not in columns:
                conn.execute("UPDATE progress SET lamp_revealed=1 WHERE has_lamp=1")
    except Exception:
        conn.close()
        raise
    return conn


def load_game(conn: sqlite3.Connection, player_id: str='local') -> GameState | None:
    row = conn.execute('SELECT * FROM progress WHERE player_id=?',(player_id,)).fetchone()
    if row is None: return None
    booleans={'has_key','door_open','reached_kitchen','has_blue_key','chest_open',
              'has_pistol','in_hammock','patrol_alive','sleeper_alive','wardrobe_open',
              'disguised','door_alerted','dining_alive','cargo_alive','lookout_alive',
              'has_lamp','lamp_lit','lamp_revealed','wardrobe_suspected',
              *(f'{kind}_alive' for kind in GUARD_ROUTES)}
    values={field.name:(bool(row[field.name]) if field.name in booleans else row[field.name])
            for field in fields(GameState) if field.name!='position'}
    return GameState(position=Position(row['zone'],float(row['position_value'])),**values)

def _values(state: GameState) -> tuple:
    raw=asdict(state)
    return tuple([state.position.zone,state.position.value,*
                  [int(raw[key]) if isinstance(raw[key],bool) else raw[key] for key in _KEYS[2:]]])

def _write_game(conn: sqlite3.Connection,state: GameState,player_id: str) -> None:
    columns = ('player_id',*_KEYS)
    placeholders = ','.join('?' for _ in columns)
    update = ','.join(f'{k}=excluded.{k}' for k in _KEYS)
    conn.execute(f"INSERT INTO progress ({','.join(columns)}) VALUES ({placeholders}) "
                 f'ON CONFLICT(player_id) DO UPDATE SET {update}',(player_id,*_values(state)))

def new_game(conn: sqlite3.Connection,player_id: str='local') -> GameState:
    state = initial_state()
    with conn:
        conn.execute('DELETE FROM progress WHERE player_id=?',(player_id,))
        _write_game(conn,state,player_id)
    return state

def restore_game(conn: sqlite3.Connection,state: GameState,player_id: str='local') -> bool:
    if not isinstance(state,GameState) or state_from_backup(asdict(state)) is None: return False
    with conn:
        cursor = conn.execute(f"INSERT OR IGNORE INTO progress ({','.join(('player_id',*_KEYS))}) "
            f"VALUES ({','.join('?' for _ in ('player_id',*_KEYS))})",(player_id,*_values(state)))
    return cursor.rowcount==1

def claim_legacy(conn: sqlite3.Connection,player_id: str) -> bool:
    if player_id=='local' or load_game(conn,player_id) is not None: return False
    with conn:
        cursor=conn.execute("UPDATE progress SET player_id=? WHERE player_id='local'",(player_id,))
    return cursor.rowcount==1

def save_position(conn: sqlite3.Connection,position: Position,player_id: str='local') -> bool:
    state=load_game(conn,player_id)
    if state is None: return False
    updated=with_position(state,position)
    if updated is None or updated==state: return False
    with conn: _write_game(conn,updated,player_id)
    return True

def apply_action(conn: sqlite3.Connection,kind: str,position: Position,guard_elapsed: float,
                 player_id: str='local', facing: str | None=None,
                 item: str | None=None, now_ms: int | None=None) -> ActionResult:
    state=load_game(conn,player_id)
    if state is None: return ActionResult(initial_state(),False,'Start a new game first.')
    wall_now = now_ms if now_ms is not None else 0
    if kind=='restart_prompt':
        if state.ending:return ActionResult(state,False,'The completed game can only be replaced through New Game confirmation.')
        candidate=with_position(state,position) if not state.reading and state.capture_phase=='none' else None
        result=replace(candidate or state,reading='restart_confirm',paused_at_ms=state.paused_at_ms or max(1,wall_now))
        with conn:_write_game(conn,result,player_id)
        return ActionResult(result,True,'')
    if kind=='restart_game':
        if state.ending or item!='confirmed' or state.reading!='restart_confirm':
            return ActionResult(state,False,'Confirm restart first.')
        return ActionResult(new_game(conn,player_id),True,'A new escape begins.')
    import finale
    if kind in finale.KINDS:
        result=finale.dispatch(state,kind,item,wall_now)
        if result.accepted:
            with conn:_write_game(conn,result.state,player_id)
        return result
    if state.ending: return ActionResult(state,False,'The journey is complete. Start a new game to try another route.')
    if state.reading:
        if kind not in ('close_reading', 'story_finish'):
            return ActionResult(state,False,'Close the document before continuing.')
        if position != state.position:
            return ActionResult(state,False,'You cannot move while a document is open.')
        result = story_action(state, 'finish' if kind == 'story_finish' else kind, item or '', wall_now)
        if result.accepted:
            with conn: _write_game(conn,result.state,player_id)
        return result
    if state.capture_phase == 'active':
        if kind=='capture_tick':
            from voyage import capture_heartbeat
            result=capture_heartbeat(state,game_now_ms(state,wall_now))
            if result.state!=state:
                with conn:_write_game(conn,result.state,player_id)
            return result
        if kind != 'capture_complete': return ActionResult(state,False,'The guard is taking you to the cell.')
        result=finish_capture(state)
        with conn: _write_game(conn,result.state,player_id)
        return result
    from voyage import progress as voyage_progress
    if voyage_progress(state).get('escort') and kind not in ('voyage_tick','journal','close_reading','capture'):
        return ActionResult(state,False,'Stay with your guide.')
    candidate=with_position(state,position)
    if candidate is None: return ActionResult(state,False,'You cannot do that from here.')
    if facing in ('left','right'): candidate=replace(candidate,facing=facing)
    now_ms = game_now_ms(state, wall_now)
    from voyage import voyage_action,ambush
    from shiplife import fire_cannon
    from feast import drug_stew
    actions = {
        'ambush':lambda:ambush(candidate,item or '',now_ms,guard_elapsed),
        'fire_cannon':lambda:fire_cannon(candidate,guard_elapsed,now_ms or 0),
        'drug_stew':lambda:drug_stew(candidate,guard_elapsed,now_ms or 0),
        'voyage_tick':lambda:voyage_action(candidate,'tick','',wall_now,guard_elapsed),
        'bribe':lambda:voyage_action(candidate,'bribe',item or '',wall_now,guard_elapsed),
        'toggle_duck':lambda:voyage_action(candidate,'toggle_duck','',wall_now),
        'duck':lambda:voyage_action(candidate,'duck','',wall_now),
        'stand':lambda:voyage_action(candidate,'stand','',wall_now),
        'story_inspect':lambda:story_action(candidate,'inspect',item or '',wall_now),
        'story_take':lambda:story_action(candidate,'take',item or '',wall_now),
        'story_finish':lambda:story_action(candidate,'finish',item or '',wall_now),
        'journal':lambda:story_action(candidate,'journal','',wall_now),
        'close_reading':lambda:story_action(candidate,'close_reading','',wall_now),
        'whistle':lambda:story_action(candidate,'whistle','',wall_now),
        'steal':lambda:steal_key(candidate,guard_elapsed,now_ms),
        'open':lambda:open_door(candidate), 'steal_blue':lambda:steal_blue_key(candidate,guard_elapsed,now_ms),
        'hammock':lambda:toggle_hammock(candidate), 'unlock_chest':lambda:unlock_chest(candidate),
        'take_pistol':lambda:take_pistol(candidate),
        'shoot':lambda:shoot_guard(candidate,guard_elapsed,now_ms or 0),
        'barrel':lambda:toggle_barrel(candidate),
        'wardrobe':lambda:toggle_wardrobe(candidate),
        'outfit':lambda:change_outfit(candidate),
        'search_crate':lambda:search_crate(candidate),
        'take_lamp':lambda:take_lamp(candidate),
        'empty_pickup':lambda:ActionResult(candidate,False,'Search the crate with F. There is no item to take here.'),
        'resting':lambda:ActionResult(candidate,False,'Press F to leave the hammock first.'),
        'notice_wardrobe':lambda:notice_wardrobe(candidate,guard_elapsed,now_ms or 0),
        'toggle_lamp':lambda:toggle_lamp(candidate),
        'select_item':lambda:select_item(candidate,item or ''),
        'alert':lambda:raise_alert(candidate,guard_elapsed,now_ms if now_ms is not None else 0),
        'capture':lambda:start_capture(candidate,guard_elapsed,item if item in GUARD_ROUTES else 'patrol',now_ms),
        'suspicion':lambda:inspect_disguise(candidate,guard_elapsed,now_ms or 0),}
    if kind not in actions: return ActionResult(state,False,'Unknown action.')
    result=actions[kind]()
    if not result.accepted: return ActionResult(state,False,result.message)
    if result.state != state:
        with conn: _write_game(conn,result.state,player_id)
    return result
