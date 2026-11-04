"""Acknowledge discrete browser requests and safely replay lost acknowledgements."""
import math
from db import apply_action, load_game
from logic import ActionResult, Position, initial_state

def handle_action(conn, payload, player_id, run_id, cache, now_ms):
    request_id = payload.get('request_id', '')
    if not isinstance(request_id,str) or len(request_id)>256: request_id=''
    state=load_game(conn,player_id) or initial_state()
    if payload.get('run_id',run_id)!=run_id:
        return ActionResult(state,False,'This request belongs to an earlier game.'),request_id,False
    if request_id and request_id in cache:
        accepted,message=cache[request_id]
        return ActionResult(state,accepted,message),request_id,True
    try:
        raw=payload['position']
        position=Position(str(raw['zone']),float(raw['value']))
        elapsed=float(payload.get('guard_elapsed',0))
        if not math.isfinite(elapsed):elapsed=0.
    except (KeyError,TypeError,ValueError):
        return ActionResult(state,False,'Invalid action position.'),request_id,False
    outcome=apply_action(conn,str(payload.get('kind','')),position,elapsed,player_id,
                         payload.get('facing'),payload.get('item'),now_ms)
    if request_id:
        cache[request_id]=(outcome.accepted,outcome.message)
        while len(cache)>128:cache.pop(next(iter(cache)))
    return outcome,request_id,False
