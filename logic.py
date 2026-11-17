"""Fixed ship layout and rules. Player progress lives in db.py."""
from __future__ import annotations

from dataclasses import dataclass, replace
from heapq import heappop, heappush
import json
from math import hypot, isfinite
from content import ITEMS, STORY_POINTS, DOCUMENTS, ENDINGS

PLAYER_SPEED = 180.0
STAIR_SPEED = .7
GUARD_SPEED = 76.0
KEY_REACH = 140.0
KEY_HEIGHT = 52.0
MAST_X = 760.0
MAST_TOP_Y = 60.0
MAST_SPEED = .62
LAMP_VISION_MULTIPLIER = 1.55
DOOR_X = 390.0
CELL_KEY_PLAYER_MIN = 350.0
DOOR_HOLD_NEAR_MAX = 440.0
DOOR_BLOCK_MIN = 385.0
DOOR_BLOCK_MAX = 410.0
SLEEPER_RANGE = 55.0
CHEST_RANGE = 60.0
SLEEPER_X = 300.0
CHEST_X = 1120.0
WARDROBE_X = 460.0
WARDROBE_RANGE = 80.0
BARREL_RANGE = 38.0
CRATE_RANGE = 45.0
VISION_RANGE = 180.0
VISION_HEIGHT = 28.0
ALERT_DURATION_MS = 20_000
# After a capture in multiplayer the crew search 30 s for the other player.
SEARCH_ALERT_MS = 30_000
ALERT_DURATIONS = (ALERT_DURATION_MS, SEARCH_ALERT_MS)
ALERT_SPEED = 2.4
WARDROBE_SIGHT = 125.0
INSPECTION_RANGE = 95.0
INSPECTION_MS = 2000
# These locations are also used by the renderer; there are no invisible props.
BARRELS = (('barrel_hold_a', 'hold', 710.),
           ('barrel_chest_a', 'chest_room', 945.),
           ('barrel_deck_a', 'upper_deck', 410.),
           ('barrel_deck_b', 'upper_deck', 885.),
           ('barrel_mid_a','mid',660.), ('barrel_mid_b','mid',810.),
           ('barrel_dining','dining',1260.), ('barrel_kitchen','kitchen',1330.),
           ('barrel_sail_a','sail_store',1590.), ('barrel_sail_b','sail_store',1780.),
           ('barrel_armory_a','armory',1850.), ('barrel_armory_b','armory',2090.),
           ('barrel_armory_c','armory',2200.), ('barrel_provisions_a','provisions',2260.),
           ('barrel_provisions_b','provisions',2370.),
           ('barrel_infirmary_a','infirmary',1420.), ('barrel_infirmary_b','infirmary',1680.),
           ('barrel_crew_a','crew_room',1835.), ('barrel_crew_b','crew_room',2180.),
           ('barrel_officers_a','officers',2270.), ('barrel_officers_b','officers',2550.),
           ('barrel_aft_a','aft_deck',1430.), ('barrel_aft_b','aft_deck',1700.),
           ('barrel_aft_c','aft_deck',1910.), ('barrel_chart_a','chart_room',2050.),
           ('barrel_chart_b','chart_room',2290.), ('barrel_captain_a','captain',2380.),
           ('barrel_captain_b','captain',2550.))
CRATES = (('crate_hold_a', 'hold', 613.),
          ('crate_hold_b', 'hold', 834.),
          ('crate_chest_a', 'chest_room', 1297.),
          ('crate_sail','sail_store',1480.), ('crate_armory','armory',1950.),
          ('crate_provisions','provisions',2490.), ('crate_crew','crew_room',2080.),
          ('crate_officers','officers',2460.), ('crate_aft','aft_deck',1570.),
          ('crate_chart','chart_room',2160.))
FLOORS = {
    'cell': (160., 390., 500.), 'hold': (390., 900., 500.),
    'chest_room': (900., 1370., 500.), 'cabin': (160., 520., 365.),
    'mid': (520., 900., 365.), 'dining': (900., 1370., 365.),
    'upper_deck': (160., 1040., 245.), 'kitchen': (1040., 1370., 245.),
    'sail_store': (1370.,1810.,500.), 'armory': (1810.,2220.,500.),
    'provisions': (2220.,2580.,500.), 'infirmary': (1370.,1810.,365.),
    'crew_room': (1810.,2220.,365.), 'officers': (2220.,2580.,365.),
    'aft_deck': (1370.,2040.,245.), 'chart_room': (2040.,2310.,245.),
    'captain': (2310.,2580.,245.),
}
STAIRS = {'lower_stair': (440., 500., 540., 365.),
          'upper_stair': (920., 365., 1040., 245.),
          'sail_stair': (1640.,500.,1740.,365.),
          'aft_stair': (1920.,365.,2040.,245.),
          'provisions_stair': (2320.,500.,2420.,365.),
          'captain_stair': (2420.,365.,2540.,245.)}
ROOM_INFO = {
    'sail_store': ('SAIL STORE','#6b6250'), 'armory': ('ARMORY','#655d53'),
    'provisions': ('PROVISIONS','#827052'), 'infirmary': ('INFIRMARY','#798377'),
    'crew_room': ('CREW QUARTERS','#96744f'), 'officers': ('OFFICERS PASSAGE','#82694f'),
    'aft_deck': ('AFT DECK','#a68b61'), 'chart_room': ('CHART ROOM','#747c6c'),
    'captain': ('CAPTAIN CABIN','#865c51'),
}
GUARD_STYLES = {
    'patrol': {'color':'#9c3d33','vision':180.,'badge':'•'},
    'dining': {'color':'#d4c4a5','vision':170.,'badge':'K'},
    'cargo': {'color':'#617947','vision':155.,'badge':'I'},
    'lookout': {'color':'#5168a0','vision':175.,'badge':'II'},
    'sailor': {'color':'#387c86','vision':135.,'badge':'S'},
    'armorer': {'color':'#686780','vision':150.,'badge':'A'},
    'medic': {'color':'#c3c8ac','vision':125.,'badge':'+'},
    'boatswain': {'color':'#985b82','vision':145.,'badge':'B'},
    'officer': {'color':'#b79545','vision':165.,'badge':'★'},
}
MAP_CONFIG = {
    'floors': FLOORS, 'stairs': STAIRS, 'player_speed': PLAYER_SPEED,
    'stair_speed': STAIR_SPEED, 'door_x': DOOR_X,
    'closed_cell_max': 380., 'closed_hold_min': 410.,
    'cell_key_player_min': CELL_KEY_PLAYER_MIN,
    'door_hold_near_max': DOOR_HOLD_NEAR_MAX,
    'door_block_min': DOOR_BLOCK_MIN, 'door_block_max': DOOR_BLOCK_MAX,
    'sleeper_x': SLEEPER_X, 'chest_x': CHEST_X,
    'sleeper_range': SLEEPER_RANGE, 'chest_range': CHEST_RANGE,
    'wardrobe_x': WARDROBE_X, 'wardrobe_range': WARDROBE_RANGE,
    'barrel_range': BARREL_RANGE, 'crate_range': CRATE_RANGE,
    'barrels': BARRELS, 'crates': CRATES,
    'vision_range': VISION_RANGE, 'vision_height': VISION_HEIGHT,
    'alert_duration_ms': ALERT_DURATION_MS, 'search_alert_ms': SEARCH_ALERT_MS, 'alert_speed': ALERT_SPEED,
    'key_reach': KEY_REACH, 'key_height': KEY_HEIGHT,
    'mast_x': MAST_X, 'mast_top_y': MAST_TOP_Y, 'mast_speed': MAST_SPEED,
    'lamp_vision_multiplier': LAMP_VISION_MULTIPLIER,
    'guard_speed':GUARD_SPEED, 'guard_styles':GUARD_STYLES,
    'rooms':ROOM_INFO, 'world_min':160., 'world_max':2580.,
    'wardrobe_sight':WARDROBE_SIGHT, 'inspection_range':INSPECTION_RANGE,
    'inspection_ms':INSPECTION_MS,
    'story_points': STORY_POINTS, 'story_items': ITEMS,
}

@dataclass(frozen=True)
class Position:
    zone: str
    value: float

@dataclass(frozen=True)
class GameState:
    position: Position
    has_key: bool = False
    door_open: bool = False
    reached_kitchen: bool = False
    has_blue_key: bool = False
    chest_open: bool = False
    has_pistol: bool = False
    in_hammock: bool = False
    patrol_alive: bool = True
    sleeper_alive: bool = True
    patrol_corpse_x: float | None = None
    patrol_corpse_y: float | None = None
    facing: str = 'right'
    held_item: str = 'none'
    hidden_barrel: str = ''
    wardrobe_open: bool = False
    disguised: bool = False
    door_alerted: bool = False
    alert_started_ms: int = 0
    alert_until_ms: int = 0
    capture_phase: str = 'none'
    capture_guard_zone: str = ''
    capture_guard_value: float = 0.
    dining_alive: bool = True
    cargo_alive: bool = True
    lookout_alive: bool = True
    dining_corpse_x: float | None = None
    dining_corpse_y: float | None = None
    cargo_corpse_x: float | None = None
    cargo_corpse_y: float | None = None
    lookout_corpse_x: float | None = None
    lookout_corpse_y: float | None = None
    has_lamp: bool = False
    lamp_lit: bool = False
    wardrobe_contents: str = 'uniform'
    suspect_started_ms: int = 0
    patrol_pause_ms: int = 0
    capture_guard: str = 'patrol'
    alert_paths: str = '{}'
    alert_resume: str = '{}'
    lamp_revealed: bool = False
    wardrobe_suspected: bool = False
    suspect_guard_zone: str = ''
    suspect_guard_value: float = 0.
    patrol_resume_ms: int = 0
    patrol_resume_elapsed: float = 0.
    sailor_alive: bool = True
    sailor_corpse_x: float | None = None
    sailor_corpse_y: float | None = None
    armorer_alive: bool = True
    armorer_corpse_x: float | None = None
    armorer_corpse_y: float | None = None
    medic_alive: bool = True
    medic_corpse_x: float | None = None
    medic_corpse_y: float | None = None
    boatswain_alive: bool = True
    boatswain_corpse_x: float | None = None
    boatswain_corpse_y: float | None = None
    officer_alive: bool = True
    officer_corpse_x: float | None = None
    officer_corpse_y: float | None = None
    story_state: str = '{}'
    ending: str = ''
    reading: str = ''
    paused_at_ms: int = 0
    paused_total_ms: int = 0

@dataclass(frozen=True)
class ActionResult:
    state: GameState
    accepted: bool
    message: str

@dataclass(frozen=True)
class GuardSegment:
    name: str
    x1: float
    y1: float
    x2: float
    y2: float
    duration: float

@dataclass(frozen=True)
class GuardPose:
    x: float
    y: float
    segment: str
    progress: float
    facing: int = 0

def initial_state() -> GameState:
    return GameState(Position('cell', 230.))

_GUARD_POINTS = (
    ('dining_out',920.,365.,540.,365.),
    ('lower_down',540.,365.,440.,500.),
    ('cell_pass',440.,500.,410.,500.),
    ('cell_return',410.,500.,440.,500.),
    ('hold_out',440.,500.,1320.,500.),
    ('hold_return',1320.,500.,440.,500.),
    ('lower_up',440.,500.,540.,365.),
    ('dining_return',540.,365.,920.,365.),
    ('dining_second',920.,365.,540.,365.),
    ('cabin_visit',540.,365.,300.,365.),
    ('cabin_return',300.,365.,540.,365.),
    ('lower_down_again',540.,365.,440.,500.),
    ('cell_pass_again',440.,500.,410.,500.),
    ('cell_return_again',410.,500.,440.,500.),
    ('hold_out_again',440.,500.,1320.,500.),
    ('hold_return_again',1320.,500.,440.,500.),
    ('lower_up_again',440.,500.,540.,365.),
    ('dining_return_again',540.,365.,920.,365.),
)
GUARD_SEGMENTS = tuple(GuardSegment(name,x1,y1,x2,y2,hypot(x2-x1,y2-y1)/GUARD_SPEED)
                       for name,x1,y1,x2,y2 in _GUARD_POINTS)
GUARD_CYCLE_SECONDS = sum(s.duration for s in GUARD_SEGMENTS)

def _route(points: tuple[tuple[str,float,float,float,float,float], ...], speed: float = GUARD_SPEED) -> tuple[GuardSegment,...]:
    return tuple(GuardSegment(name,x1,y1,x2,y2,wait*.7 if wait else hypot(x2-x1,y2-y1)/speed)
                 for name,x1,y1,x2,y2,wait in points)

DINING_SEGMENTS = _route((
    ('eating',1100,365,1100,365,40),
    ('dining_to_stair',1100,365,920,365,0),
    ('dining_upper_up',920,365,1040,245,0),
    ('bowl_to_pot',1040,245,1200,245,0),
    ('put_bowl',1200,245,1200,245,2),
    ('kitchen_to_deck',1200,245,800,245,0),
    ('lookout_pause',800,245,800,245,15),
    ('deck_to_pot',800,245,1200,245,0),
    ('fill_bowl',1200,245,1200,245,2),
    ('pot_to_stair',1200,245,1040,245,0),
    ('dining_upper_down',1040,245,920,365,0),
    ('stair_to_table',920,365,1100,365,0),
))
CARGO_SEGMENTS = _route((
    ('cargo_left_pause',760,500,760,500,4),
    ('cargo_out',760,500,1320,500,0),
    ('cargo_right_pause',1320,500,1320,500,5),
    ('cargo_back',1320,500,760,500,0),
),speed=48.)
LOOKOUT_SEGMENTS = _route((
    ('lookout_left_pause',250,245,250,245,4),
    ('lookout_to_mast',250,245,MAST_X,245,0),
    ('lookout_mast_pause',MAST_X,245,MAST_X,245,5),
    ('lookout_to_right',MAST_X,245,970,245,0),
    ('lookout_right_pause',970,245,970,245,4),
    ('lookout_return',970,245,250,245,0),
))
# Preserve the 45-second watch and its walking speed while shortening actual
# stationary waits by 30%. Spend the freed time walking a short turn near the post.
def _cargo_watch_route():
    old_cycle=sum(p.duration if (p.x1,p.y1)!=(p.x2,p.y2) else p.duration/.7 for p in CARGO_SEGMENTS)
    scale=45/old_cycle
    route=[replace(CARGO_SEGMENTS[i],duration=CARGO_SEGMENTS[i].duration*scale) for i in (2,3,0,1)]
    spare=45-sum(p.duration for p in route);turn=1320-48/scale*spare/2
    route.extend((GuardSegment('cargo_watch_turn_out',1320,500,turn,500,spare/2),GuardSegment('cargo_watch_turn_back',turn,500,1320,500,spare/2)))
    return tuple(route)
CARGO_WATCH_ROUTE=_cargo_watch_route()
MAP_CONFIG['cargo_watch_route']=[{'name':s.name,'x1':s.x1,'y1':s.y1,'x2':s.x2,'y2':s.y2,'duration':s.duration} for s in CARGO_WATCH_ROUTE]
MAP_CONFIG['cargo_route']=[{'name':s.name,'x1':s.x1,'y1':s.y1,'x2':s.x2,'y2':s.y2,'duration':s.duration} for s in CARGO_SEGMENTS]
GUARD_ROUTES = {'patrol':GUARD_SEGMENTS,'dining':DINING_SEGMENTS,
                'cargo':CARGO_SEGMENTS,'lookout':LOOKOUT_SEGMENTS}


def _round_trip(kind: str, points: tuple, speed: float, wait: float) -> tuple[GuardSegment,...]:
    result=[GuardSegment(f'{kind}_start_pause',*points[0],*points[0],wait*.7)]
    journey=(*points,*reversed(points[:-1]))
    for i,(a,b) in enumerate(zip(journey,journey[1:])):
        result.append(GuardSegment(f'{kind}_walk_{i}',*a,*b,hypot(b[0]-a[0],b[1]-a[1])/speed))
        if i==len(points)-2:
            result.append(GuardSegment(f'{kind}_end_pause',*b,*b,(wait+2)*.7))
    return tuple(result)

GUARD_ROUTES.update({
    'sailor':_round_trip('sailor',((1410.,500.),(1740.,500.)),50.,6.),
    'armorer':_round_trip('armorer',((1850.,500.),(2320.,500.),(2420.,365.),(2500.,365.)),55.,7.),
    'medic':_round_trip('medic',((1280.,365.),(1740.,365.)),44.,8.),
    'boatswain':_round_trip('boatswain',((1450.,245.),(2040.,245.),(1920.,365.),(1810.,365.)),58.,6.),
    'officer':_round_trip('officer',((1980.,245.),(2530.,245.)),48.,8.),
})

def guard_time(segment_name: str, progress: float) -> float:
    if segment_name == 'cycle_end': return GUARD_CYCLE_SECONDS
    elapsed = 0.
    for s in GUARD_SEGMENTS:
        if s.name == segment_name: return elapsed + s.duration * progress
        elapsed += s.duration
    raise ValueError(f'Unknown guard segment: {segment_name}')

def guard_pose(elapsed_seconds: float) -> GuardPose:
    return guard_pose_for('patrol',elapsed_seconds)

def guard_pose_for(kind: str, elapsed_seconds: float) -> GuardPose:
    segments = GUARD_ROUTES[kind]
    cycle = sum(s.duration for s in segments)
    if not isfinite(elapsed_seconds): elapsed_seconds = 0.
    remaining = max(0., elapsed_seconds) % cycle
    for s in segments:
        if remaining < s.duration:
            f = remaining/s.duration
            return GuardPose(s.x1+(s.x2-s.x1)*f,s.y1+(s.y2-s.y1)*f,s.name,f,
                             _guard_facing(kind,s.name))
        remaining -= s.duration
    s = segments[0]
    return GuardPose(s.x1,s.y1,s.name,0.,_guard_facing(kind,s.name))


def alert_waypoints(kind: str) -> tuple[Position,...]:
    locations={
        'patrol':(('hold',410),('chest_room',1320),('cabin',300),('dining',920)),
        'dining':(('hold',800),('kitchen',1360),('upper_deck',500),('dining',1100)),
        'cargo':(('hold',760),('sail_store',1730),('chest_room',1300)),
        'lookout':(('upper_deck',250),('aft_deck',1950),('upper_deck',760)),
        'sailor':(('chest_room',980),('armory',2030),('sail_store',1470)),
        'armorer':(('sail_store',1590),('provisions',2540),('officers',2370)),
        'medic':(('dining',1050),('crew_room',2150),('infirmary',1450)),
        'boatswain':(('upper_deck',900),('chart_room',2300),('crew_room',1835)),
        'officer':(('aft_deck',1800),('captain',2550),('chart_room',2150)),
        'sleeper':(('cabin',300),('hold',760),('chest_room',1300)),
    }
    return tuple(Position(zone,float(x)) for zone,x in locations[kind])


def alert_duration(state) -> int:
    """How long this alarm's search walk takes: 20 s, or 30 s after a multiplayer capture."""
    span=state.alert_until_ms-state.alert_started_ms
    return span if span in ALERT_DURATIONS else ALERT_DURATION_MS


def search_path_pose(path,kind,elapsed_ms,duration_ms=ALERT_DURATION_MS):
    """Traverse the entire search route once per alarm; reverse without stopping in combat."""
    length=sum(hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:]))
    phase=max(0,elapsed_ms)/duration_ms % 2
    reverse=phase>1
    points=list(reversed(path)) if reverse else path
    return _path_pose(points,length*(phase-1 if reverse else phase),kind)


def search_pose_at(state,kind,now_ms):
    armed=story_progress(state).get('voyage',{}).get('armed',False)
    if not (state.alert_started_ms<=now_ms<state.alert_until_ms or armed):return None
    path=json.loads(state.alert_paths).get(kind)
    if path:return search_path_pose(path,kind,now_ms-state.alert_started_ms,alert_duration(state))
    # Earlier saves have no search route for the original sleeping guard.
    if armed and kind=='sleeper':
        return search_path_pose([list(p) for p in route_points(Position('cabin',300),Position('chest_room',1320))],kind,now_ms-state.alert_started_ms,alert_duration(state))
    return None


def _path_pose(path: list[list[float]], distance: float, kind: str) -> GuardPose:
    left=max(0.,distance)
    for i in range(1,len(path)):
        a,b=path[i-1],path[i]
        length=hypot(b[0]-a[0],b[1]-a[1])
        if left<=length or i==len(path)-1:
            f=min(1.,left/length) if length else 1.
            facing=1 if b[0]>=a[0] else -1
            return GuardPose(a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,
                             f'search_{kind}',f,facing)
        left-=length
    return GuardPose(path[0][0],path[0][1],f'search_{kind}',0.,1)


def _nearest_route_time(kind: str, x: float, y: float) -> float:
    best=(float('inf'),0.)
    elapsed=0.
    for segment in GUARD_ROUTES[kind]:
        dx,dy=segment.x2-segment.x1,segment.y2-segment.y1
        f=max(0.,min(1.,((x-segment.x1)*dx+(y-segment.y1)*dy)/(dx*dx+dy*dy))) if dx or dy else 0.
        px,py=segment.x1+dx*f,segment.y1+dy*f
        candidate=((x-px)**2+(y-py)**2,elapsed+segment.duration*f)
        if candidate<best: best=candidate
        elapsed+=segment.duration
    return best[1]


def _base_guard_pose_at(state: GameState, kind: str, guard_elapsed: float, now_ms: int) -> GuardPose:
    search=search_pose_at(state,kind,now_ms)
    if search is not None:return search
    if kind=='patrol' and state.suspect_started_ms and state.suspect_guard_zone:
        x,y=position_xy(Position(state.suspect_guard_zone,state.suspect_guard_value))
        return GuardPose(x,y,'inspection_pause',0.,1 if position_xy(state.position)[0]>=x else -1)
    if kind=='patrol' and state.patrol_resume_ms and state.patrol_resume_ms>=state.alert_started_ms:
        return guard_pose_for(kind,state.patrol_resume_elapsed+max(0,now_ms-state.patrol_resume_ms)/1000)
    paths=json.loads(state.alert_paths)
    resume=json.loads(state.alert_resume)
    if state.alert_started_ms<=now_ms<state.alert_until_ms and kind in paths:
        return search_path_pose(paths[kind],kind,now_ms-state.alert_started_ms)
    if state.alert_until_ms and now_ms>=state.alert_until_ms and kind in resume:
        return guard_pose_for(kind,resume[kind]+(now_ms-state.alert_until_ms)/1000)
    return guard_pose_for(kind,guard_elapsed)


def guard_pose_at(state: GameState, kind: str, guard_elapsed: float, now_ms: int) -> GuardPose:
    from feast import pose as feast_pose, resumed
    meal = feast_pose(state,kind,now_ms) or resumed(state,kind,now_ms)
    if meal is not None: return meal
    from escort import guard_override
    guided=guard_override(state,kind,now_ms)
    if guided is not None:return guided
    if kind in ('cargo','sleeper'):
        from voyage import watch_pose
        pose,_=watch_pose(state,kind,now_ms)
        if pose is not None:return pose
    pose = _base_guard_pose_at(state, kind, guard_elapsed, now_ms)
    signal = story_progress(state).get('signal')
    if (signal and signal['started'] <= now_ms < signal['until'] and now_ms >= state.alert_until_ms
            and not (kind == 'patrol' and state.suspect_started_ms)
            and abs(pose.y-signal['y']) <= VISION_HEIGHT and abs(pose.x-signal['x']) <= 400):
        return replace(pose, facing=1 if signal['x'] >= pose.x else -1)
    return pose


def _start_alert(state: GameState, guard_elapsed: float, now_ms: int, cell_first: bool=False,
                 first_goal: Position | None=None, duration_ms: int=ALERT_DURATION_MS) -> GameState:
    paths={};resume={}
    for kind in (*GUARD_ROUTES,'sleeper'):
        if not getattr(state,f'{kind}_alive'): continue
        start=_guard_position(guard_elapsed,kind,state,now_ms)
        current=start
        points=[list(position_xy(start))]
        goals=alert_waypoints(kind)
        if cell_first and kind=='patrol':goals=(Position('cell',180.),Position('hold',410.),*goals)
        if first_goal is not None:goals=(first_goal,*goals)
        for goal in goals:
            leg=route_points(current,goal)
            points.extend([list(point) for point in leg[1:]])
            current=goal
        # End on the normal route so a quiet alarm can expire without a jump.
        home=start
        meal=story_progress(state).get('voyage',{}).get('feast')
        if meal and kind in meal['returns'] and now_ms>=meal['gather']:
            from feast import back
            if now_ms<back(meal,kind):home=_position_at_xy(*meal['returns'][kind][-1])
        if kind in ('cargo','sleeper'):
            from voyage import normal_watch_pose
            future,_=normal_watch_pose(state,kind,now_ms+duration_ms)
            if future is not None:home=_position_at_xy(future.x,future.y)
        points.extend([list(p) for p in route_points(current,home)[1:]])
        points=[p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
        paths[kind]=points
        resume[kind]=_nearest_route_time('cargo' if kind=='sleeper' else kind,*points[-1])
    from voyage import progress as voyage_progress, save as voyage_save
    v=voyage_progress(state)
    if 'feast' in v:
        from feast import interrupt
        state=voyage_save(state,interrupt(state,v,now_ms))
    return replace(state,alert_started_ms=now_ms,alert_until_ms=now_ms+duration_ms,
                   suspect_started_ms=0,suspect_guard_zone='',suspect_guard_value=0.,
                   alert_paths=json.dumps(paths,separators=(',',':')),
                   alert_resume=json.dumps(resume,separators=(',',':')))

def valid_position(position: Position, door_open: bool) -> bool:
    if not isinstance(position, Position) or not isinstance(position.value,(int,float)) or not isfinite(position.value): return False
    if position.zone == 'hammock': return position.value == SLEEPER_X
    if position.zone == 'mast': return 0. <= position.value <= 1.
    if position.zone == 'mast_top': return MAST_X-40 <= position.value <= MAST_X+40
    if position.zone in STAIRS: return 0. <= position.value <= 1.
    if position.zone not in FLOORS: return False
    low, high, _ = FLOORS[position.zone]
    if position.zone == 'cell' and not door_open: high = 380.
    if position.zone == 'hold' and not door_open: low = 410.
    return low <= position.value <= high

def position_xy(position: Position) -> tuple[float,float]:
    if position.zone == 'hammock': return SLEEPER_X, 365.
    if position.zone == 'mast': return MAST_X,245.-(245.-MAST_TOP_Y)*position.value
    if position.zone == 'mast_top': return position.value,MAST_TOP_Y
    if position.zone in FLOORS: return position.value, FLOORS[position.zone][2]
    if position.zone in STAIRS:
        x1,y1,x2,y2 = STAIRS[position.zone]
        return x1+(x2-x1)*position.value, y1+(y2-y1)*position.value
    raise ValueError(f'Unknown zone: {position.zone}')

def _floor_zone(y: float, x: float) -> str:
    matches=[(zone,floor) for zone,floor in FLOORS.items() if floor[2]==y and floor[0]<=x<=floor[1]]
    if not matches: raise ValueError(f'Outside walkable floor: {x}, {y}')
    return matches[-1][0]  # at a shared boundary, enter the room to the right


def advance_player(position: Position, door_open: bool, horizontal: int, vertical: int, dt: float) -> Position:
    dt=max(0.,min(float(dt),3.))
    horizontal=max(-1,min(1,int(horizontal)));vertical=max(-1,min(1,int(vertical)))
    z,v=position.zone,position.value
    if z=='hammock': return position
    if z=='mast':
        progress=v+vertical*MAST_SPEED*dt
        if progress>=1: return Position('mast_top',MAST_X)
        if progress<=0: return Position('upper_deck',MAST_X)
        return Position(z,progress)
    if z=='mast_top':
        if vertical<0 and abs(v-MAST_X)<=30:
            progress=1+vertical*MAST_SPEED*dt
            return Position('upper_deck',MAST_X) if progress<=0 else Position('mast',progress)
        return Position(z,max(MAST_X-40,min(MAST_X+40,v+horizontal*PLAYER_SPEED*dt)))
    def on_stair(name: str, progress: float) -> Position:
        x1,y1,x2,y2=STAIRS[name]
        if progress<=0: return Position(_floor_zone(y1,x1),x1)
        if progress>=1: return Position(_floor_zone(y2,x2),x2)
        return Position(name,progress)
    if z in STAIRS:
        if horizontal and not vertical and (v <= .18 or v >= .82):
            x1,y1,x2,y2=STAIRS[z]
            x,y=(x1,y1) if v<=.18 else (x2,y2)
            x=max(MAP_CONFIG['world_min'],min(MAP_CONFIG['world_max'],x+horizontal*PLAYER_SPEED*dt))
            return Position(_floor_zone(y,x),x)
        return on_stair(z,v+vertical*STAIR_SPEED*dt)
    if z not in FLOORS: return position
    y=FLOORS[z][2]
    for name,(x1,y1,x2,y2) in STAIRS.items():
        if vertical>0 and y==y1 and z!='cell' and x1-45<=v<=x2+20: return on_stair(name,dt*STAIR_SPEED)
        if vertical<0 and y==y2 and x1-20<=v<=x2+45: return on_stair(name,1-dt*STAIR_SPEED)
    if z=='upper_deck' and vertical>0 and abs(v-MAST_X)<=18:
        return Position('mast',min(1.,dt*MAST_SPEED))
    x=max(MAP_CONFIG['world_min'],min(MAP_CONFIG['world_max'],v+horizontal*PLAYER_SPEED*dt))
    if y==500 and not door_open: x=min(x,380.) if z=='cell' else max(x,410.)
    return Position(_floor_zone(y,x),x)

def with_position(state: GameState, position: Position) -> GameState | None:
    if state.ending or state.reading: return None
    if not valid_position(position,state.door_open): return None
    if state.capture_phase != 'none': return None
    if state.hidden_barrel and position != state.position: return None
    if not state.has_key and position.zone != 'cell': return None
    if state.in_hammock and position.zone != 'hammock': return None
    if not state.in_hammock and position.zone == 'hammock': return None
    x1,y1 = position_xy(state.position)
    x2,y2 = position_xy(position)
    # Browser reports snapshots. Reject jumps across decks and far teleports;
    # actions may report a valid position after moving while saves were throttled.
    if abs(y2-y1)>145 and position.zone not in STAIRS and state.position.zone not in STAIRS and position.zone not in ('mast','mast_top') and state.position.zone not in ('mast','mast_top'):
        return None
    facing = state.facing
    if x2 > x1 + .001: facing = 'right'
    elif x2 < x1 - .001: facing = 'left'
    return replace(state,position=position,facing=facing,
                   reached_kitchen=state.reached_kitchen or position.zone=='kitchen')

def state_from_backup(payload: object) -> GameState | None:
    if not isinstance(payload,dict) or not isinstance(payload.get('position'),dict): return None
    pos = payload['position']
    if not isinstance(pos.get('zone'),str) or type(pos.get('value')) not in (float,int): return None
    base_flags = ('has_key','door_open','reached_kitchen')
    if any(type(payload.get(k)) is not bool for k in base_flags): return None
    optional = {'has_blue_key':False,'chest_open':False,'has_pistol':False,'in_hammock':False,
                'patrol_alive':True,'sleeper_alive':True,'wardrobe_open':False,
                'disguised':False,'door_alerted':False,'dining_alive':True,
                'cargo_alive':True,'lookout_alive':True,'has_lamp':False,'lamp_lit':False,
                'lamp_revealed':payload.get('has_lamp',False),'wardrobe_suspected':False,
                **{f'{k}_alive':True for k in GUARD_ROUTES}}
    if any(type(payload.get(k,default)) is not bool for k,default in optional.items()): return None
    for k in (f'{kind}_corpse_{axis}' for kind in GUARD_ROUTES for axis in ('x','y')):
        v = payload.get(k)
        if v is not None and (type(v) not in (int,float) or not isfinite(v)): return None
    facing = payload.get('facing','right')
    if facing not in ('left','right'): return None
    held_default = ('lamp' if payload.get('has_lamp',False) else
                    'pistol' if payload.get('has_pistol',False) else
                    'blue_key' if payload.get('has_blue_key',False) else
                    'cell_key' if payload['has_key'] else 'none')
    held = payload.get('held_item',held_default)
    hidden = payload.get('hidden_barrel','')
    phase = payload.get('capture_phase','none')
    guard_zone = payload.get('capture_guard_zone','')
    guard_value = payload.get('capture_guard_value',0.)
    if held not in ('none','cell_key','blue_key','pistol','lamp'): return None
    if type(hidden) is not str or type(phase) is not str or type(guard_zone) is not str: return None
    if phase not in ('none','active'): return None
    if type(guard_value) not in (int,float) or not isfinite(guard_value): return None
    start = payload.get('alert_started_ms',0)
    until = payload.get('alert_until_ms',0)
    if any(type(v) is not int or v < 0 for v in (start,until)): return None
    suspect = payload.get('suspect_started_ms',0)
    pause = payload.get('patrol_pause_ms',0)
    if any(type(v) is not int or v < 0 for v in (suspect,pause)): return None
    wardrobe_contents = payload.get('wardrobe_contents','player_clothes' if payload.get('disguised',False) else 'uniform')
    if wardrobe_contents not in ('uniform','player_clothes'): return None
    capture_guard=payload.get('capture_guard','patrol')
    if capture_guard not in (*GUARD_ROUTES,'sleeper'): return None
    alert_paths=payload.get('alert_paths','{}')
    alert_resume=payload.get('alert_resume','{}')
    try:
        if not isinstance(alert_paths,str) or not isinstance(alert_resume,str): return None
        paths=json.loads(alert_paths);resume=json.loads(alert_resume)
        if not isinstance(paths,dict) or not isinstance(resume,dict): return None
        if any(k not in (*GUARD_ROUTES,'sleeper') or not isinstance(v,list) for k,v in paths.items()): return None
        if any(k not in (*GUARD_ROUTES,'sleeper') or type(v) not in (int,float) or not isfinite(v) for k,v in resume.items()): return None
    except (ValueError,TypeError): return None
    suspect_zone=payload.get('suspect_guard_zone','')
    suspect_value=payload.get('suspect_guard_value',0.)
    resume_ms=payload.get('patrol_resume_ms',0)
    resume_elapsed=payload.get('patrol_resume_elapsed',0.)
    if type(resume_ms) is not int or resume_ms<0: return None
    if type(resume_elapsed) not in (float,int) or not isfinite(resume_elapsed) or resume_elapsed<0: return None
    if type(suspect_zone) is not str or type(suspect_value) not in (float,int) or not isfinite(suspect_value): return None
    if suspect_zone and not valid_position(Position(suspect_zone,suspect_value),True): return None
    story = payload.get('story_state', '{}')
    ending = payload.get('ending', '')
    reading = payload.get('reading', '')
    paused_at = payload.get('paused_at_ms', 0)
    paused_total = payload.get('paused_total_ms', 0)
    if not valid_story_state(story): return None
    if not isinstance(ending, str) or ending not in ('', *ENDINGS): return None
    if not isinstance(reading, str) or reading not in ('', 'journal', *DOCUMENTS): return None
    if any(type(v) is not int or v < 0 for v in (paused_at, paused_total)): return None
    if bool(reading) != bool(paused_at) or (ending and reading): return None
    state = GameState(
        story_state=story, ending=ending, reading=reading,
        paused_at_ms=paused_at, paused_total_ms=paused_total,
        position=Position(pos['zone'],float(pos['value'])),
        has_key=payload['has_key'],door_open=payload['door_open'],
        reached_kitchen=payload['reached_kitchen'],
        has_blue_key=payload.get('has_blue_key',False),
        chest_open=payload.get('chest_open',False),
        has_pistol=payload.get('has_pistol',False),
        in_hammock=payload.get('in_hammock',False),
        patrol_alive=payload.get('patrol_alive',True),
        sleeper_alive=payload.get('sleeper_alive',True),
        patrol_corpse_x=payload.get('patrol_corpse_x'),
        patrol_corpse_y=payload.get('patrol_corpse_y'),
        facing=facing,held_item=held,hidden_barrel=hidden,
        wardrobe_open=payload.get('wardrobe_open',False),
        disguised=payload.get('disguised',False),
        door_alerted=payload.get('door_alerted',False),
        alert_started_ms=start,alert_until_ms=until,
        capture_phase=phase,capture_guard_zone=guard_zone,
        capture_guard_value=float(guard_value),
        dining_alive=payload.get('dining_alive',True),cargo_alive=payload.get('cargo_alive',True),
        lookout_alive=payload.get('lookout_alive',True),
        dining_corpse_x=payload.get('dining_corpse_x'),dining_corpse_y=payload.get('dining_corpse_y'),
        cargo_corpse_x=payload.get('cargo_corpse_x'),cargo_corpse_y=payload.get('cargo_corpse_y'),
        lookout_corpse_x=payload.get('lookout_corpse_x'),lookout_corpse_y=payload.get('lookout_corpse_y'),
        has_lamp=payload.get('has_lamp',False),lamp_lit=payload.get('lamp_lit',False),
        wardrobe_contents=wardrobe_contents,suspect_started_ms=suspect,patrol_pause_ms=pause,
        capture_guard=capture_guard,alert_paths=alert_paths,alert_resume=alert_resume,
        lamp_revealed=payload.get('lamp_revealed',payload.get('has_lamp',False)),
        wardrobe_suspected=payload.get('wardrobe_suspected',False),
        suspect_guard_zone=suspect_zone,suspect_guard_value=suspect_value,
        patrol_resume_ms=resume_ms,patrol_resume_elapsed=resume_elapsed,
        **{f'{k}_{field}':payload.get(f'{k}_{field}',True if field=='alive' else None)
           for k in ('sailor','armorer','medic','boatswain','officer')
           for field in ('alive','corpse_x','corpse_y')})
    if state.door_open and not state.has_key: return None
    if not state.has_key and state.position.zone != 'cell': return None
    if state.position.zone == 'kitchen' and not state.reached_kitchen: return None
    if state.chest_open and not state.has_blue_key: return None
    if state.has_pistol and not state.chest_open: return None
    if state.in_hammock != (state.position.zone == 'hammock'): return None
    if not state.patrol_alive and (state.patrol_corpse_x is None or state.patrol_corpse_y is None): return None
    for kind in GUARD_ROUTES:
        if not getattr(state,f'{kind}_alive') and (getattr(state,f'{kind}_corpse_x') is None or
                                                   getattr(state,f'{kind}_corpse_y') is None): return None
    if state.held_item == 'cell_key' and not state.has_key: return None
    if state.held_item == 'blue_key' and not state.has_blue_key: return None
    if state.held_item == 'pistol' and not state.has_pistol: return None
    if state.held_item == 'lamp' and not state.has_lamp: return None
    if state.lamp_lit and not state.has_lamp: return None
    if state.has_lamp and not state.lamp_revealed: return None
    if state.wardrobe_contents != ('player_clothes' if state.disguised else 'uniform'): return None
    if state.hidden_barrel:
        barrel = next((b for b in (*BARRELS,*CRATES) if b[0] == state.hidden_barrel),None)
        if barrel is None or state.position != Position(barrel[1],barrel[2]): return None
    if state.capture_phase == 'active':
        if not valid_position(Position(state.capture_guard_zone,state.capture_guard_value),True): return None
    elif state.capture_guard_zone: return None
    if state.alert_until_ms and state.alert_until_ms-state.alert_started_ms not in ALERT_DURATIONS: return None
    from voyage import progress as voyage_progress,captain_ready
    v=voyage_progress(state)
    for kind,barrel_id in v.get('concealed',{}).items():
        if getattr(state,kind+'_alive'):return None
        barrel=next(b for b in BARRELS if b[0]==barrel_id)
        if kind!='sleeper' and (getattr(state,kind+'_corpse_x'),getattr(state,kind+'_corpse_y'))!=position_xy(Position(barrel[1],barrel[2])):return None
    if v.get('captain_worn') and not state.disguised:return None
    cannon_finale=v.get('finale')
    if cannon_finale is not None:
        # The finale belongs to an ending: a win turns it into "free", anything else keeps it.
        if cannon_finale['status']=='won':
            if ending!='free':return None
        elif ending!=cannon_finale['origin']:return None
    elif ending=='free':return None
    reached=cannon_finale['origin'] if ending=='free' else ending
    if reached=='command' and not captain_ready(state):return None
    if reached == 'takeover' and opponents_remaining(state): return None
    if reached == 'crate' and not crate_ready(state): return None
    if reached == 'dinghy':
        from voyage import boat_ready
        if not boat_ready(state):return None
    if reached == 'lullaby' and not v.get('stew_drugged'): return None
    if reached == 'castaway' and 'sleeping_pills' not in story_progress(state)['items']: return None
    if ending and (state.capture_phase != 'none' or state.hidden_barrel or state.in_hammock): return None
    return state if valid_position(state.position,state.door_open) else None

def _at_door(state: GameState) -> bool:
    return (state.position.zone=='cell' and state.position.value>=CELL_KEY_PLAYER_MIN or
            state.position.zone=='hold' and DOOR_BLOCK_MAX<=state.position.value<=DOOR_HOLD_NEAR_MAX)

def key_prompt(state: GameState, guard_elapsed: float, now_ms: int | None = None) -> bool:
    if state.has_key or not state.patrol_alive or state.position.zone!='cell' or state.position.value<CELL_KEY_PLAYER_MIN: return False
    p = guard_pose_at(state,'patrol',guard_elapsed,now_ms) if now_ms is not None else guard_pose(guard_elapsed)
    return abs(p.y-500.) <= KEY_HEIGHT and hypot(p.x-state.position.value,p.y-500.) <= KEY_REACH

def steal_key(state: GameState, guard_elapsed: float, now_ms: int | None = None) -> ActionResult:
    if state.has_key: return ActionResult(state,False,'You already have the cell key.')
    if state.position.zone!='cell' or state.position.value<CELL_KEY_PLAYER_MIN: return ActionResult(state,False,'Stand by the cell bars to reach the key.')
    if not key_prompt(state,guard_elapsed,now_ms): return ActionResult(state,False,'The key is out of reach. Wait for the guard to pass the stairs.')
    return ActionResult(replace(state,has_key=True,held_item='cell_key'),True,'You stole the cell key!')

def open_door(state: GameState) -> ActionResult:
    if not _at_door(state): return ActionResult(state,False,'Move closer to the cell door.')
    if not state.has_key: return ActionResult(state,False,'The cell door is locked. You need the key.')
    if state.door_open and DOOR_BLOCK_MIN <= state.position.value <= DOOR_BLOCK_MAX:
        return ActionResult(state,False,'Step out of the doorway before closing it.')
    next_open = not state.door_open
    return ActionResult(replace(state,door_open=next_open,
                                door_alerted=state.door_alerted if next_open else False),True,
                        'The cell door is open!' if next_open else 'The cell door is closed!')

def steal_blue_key(state: GameState, guard_elapsed: float=0, now_ms: int | None=None) -> ActionResult:
    if state.has_blue_key: return ActionResult(state,False,'You already have the blue key.')
    if not state.sleeper_alive: return ActionResult(state,False,'The guard no longer has the key.')
    x,y = position_xy(state.position)
    from voyage import watch_pose
    pose,_=watch_pose(state,'sleeper',now_ms or 0)
    if abs(x-pose.x)>SLEEPER_RANGE or abs(position_xy(state.position)[1]-pose.y)>25:
        return ActionResult(state,False,'Move closer to the original blue-key guard.')
    return ActionResult(replace(state,has_blue_key=True,held_item='blue_key'),True,'You stole the blue key!')

def toggle_hammock(state: GameState) -> ActionResult:
    if state.in_hammock:
        return ActionResult(replace(state,in_hammock=False,position=Position('cabin',SLEEPER_X)),True,'You got out of the hammock.')
    if state.position.zone!='cabin' or abs(state.position.value-SLEEPER_X)>SLEEPER_RANGE:
        return ActionResult(state,False,'Move to the upper hammock first.')
    return ActionResult(replace(state,in_hammock=True,position=Position('hammock',SLEEPER_X)),True,'You lie in the upper hammock. Guards leave sleeping crew alone.')

def unlock_chest(state: GameState) -> ActionResult:
    if state.chest_open: return ActionResult(state,False,'The chest is already open.')
    if state.position.zone!='chest_room' or abs(state.position.value-CHEST_X)>CHEST_RANGE:
        return ActionResult(state,False,'Move closer to the chest.')
    if not state.has_blue_key: return ActionResult(state,False,'The chest needs the blue key.')
    return ActionResult(replace(state,chest_open=True),True,'The blue key unlocked the chest!')

def take_pistol(state: GameState) -> ActionResult:
    if state.has_pistol: return ActionResult(state,False,'You already have the pistol.')
    if state.position.zone!='chest_room' or abs(state.position.value-CHEST_X)>CHEST_RANGE:
        return ActionResult(state,False,'Move closer to the chest.')
    if not state.chest_open: return ActionResult(state,False,'The chest is locked.')
    return ActionResult(replace(state,has_pistol=True,held_item='pistol'),True,'You took the pistol!')

def shoot_guard(state: GameState, guard_elapsed: float, now_ms: int = 0) -> ActionResult:
    if not state.has_pistol: return ActionResult(state,False,'You need the pistol before you can shoot.')
    if state.held_item != 'pistol': return ActionResult(state,False,'Select the pistol in your inventory with I before shooting.')
    if state.in_hammock: return ActionResult(state,False,'Stand up before shooting.')
    if state.hidden_barrel: return ActionResult(state,False,'Leave the barrel before shooting.')
    x,y = position_xy(state.position)
    direction = 1 if state.facing=='right' else -1
    candidates = []
    for kind in GUARD_ROUTES:
        if getattr(state,f'{kind}_alive'):
            p=guard_pose_at(state,kind,guard_elapsed,now_ms) if now_ms else guard_pose_for(kind,guard_elapsed)
            if abs(p.y-y)<=20: candidates.append((abs(p.x-x),p.x,kind,p.y))
    if state.sleeper_alive:
        from voyage import watch_pose
        sp,_=watch_pose(state,'sleeper',now_ms)
        if abs(y-sp.y)<=20:candidates.append((abs(sp.x-x),sp.x,'sleeper',sp.y))
    for distance,target,kind,guard_y in sorted(candidates):
        if (target-x)*direction<=0: continue
        if not state.door_open and y==500 and min(x,target)<DOOR_X<max(x,target): continue
        if kind!='sleeper':
            floor_y = min((fy for fy in (245.,365.,500.) if fy>=guard_y),default=500.)
            updated=replace(state,**{f'{kind}_alive':False,f'{kind}_corpse_x':target,
                                     f'{kind}_corpse_y':floor_y})
            return ActionResult(_shot_alert(updated,guard_elapsed,now_ms),True,'The guard fell. The shot alerted the others!')
        return ActionResult(_shot_alert(replace(state,sleeper_alive=False),guard_elapsed,now_ms),True,'The sleeping guard fell. The shot alerted the others!')
    return ActionResult(_shot_alert(state,guard_elapsed,now_ms),True,'The shot missed, but the guards heard it.')


def _shot_alert(state: GameState, guard_elapsed: float, now_ms: int) -> GameState:
    if now_ms < 0: now_ms=0
    from voyage import progress,save
    v=progress(state)
    v['armed']=True
    return _start_alert(save(state,v),guard_elapsed,now_ms)


def _near_prop(position: Position, zone: str, x: float, reach: float) -> bool:
    return position.zone == zone and abs(position.value-x) <= reach


def toggle_barrel(state: GameState) -> ActionResult:
    if state.hidden_barrel:
        return ActionResult(replace(state,hidden_barrel=''),True,'You climbed out of the barrel.')
    if state.in_hammock or state.capture_phase != 'none':
        return ActionResult(state,False,'You cannot hide right now.')
    barrel = next((b for b in (*BARRELS,*CRATES) if _near_prop(state.position,b[1],b[2],BARREL_RANGE)),None)
    if barrel is None: return ActionResult(state,False,'Move closer to a barrel.')
    return ActionResult(replace(state,hidden_barrel=barrel[0],position=Position(barrel[1],barrel[2])),
                        True,'You hid in the barrel. Press F to climb out.')


def search_crate(state: GameState) -> ActionResult:
    if state.hidden_barrel or state.in_hammock or state.capture_phase != 'none':
        return ActionResult(state,False,'You cannot search right now.')
    crate = next((b for b in CRATES if _near_prop(state.position,b[1],b[2],CRATE_RANGE)),None)
    if crate is None:
        return ActionResult(state,False,'Move closer to a crate.')
    if crate[0]=='crate_hold_b':
        if state.has_lamp: return ActionResult(state,False,'The crate is empty now.')
        if state.lamp_revealed: return ActionResult(state,False,'The lamp is in the crate. Press E to take it.')
        return ActionResult(replace(state,lamp_revealed=True),True,
                            'You found an old lamp! Press E to take it.')
    return ActionResult(state,True,'The crate is empty.')


def take_lamp(state: GameState) -> ActionResult:
    if state.has_lamp: return ActionResult(state,False,'You already have the lamp.')
    if state.hidden_barrel or state.in_hammock or state.capture_phase!='none':
        return ActionResult(state,False,'You cannot take the lamp right now.')
    if not _near_prop(state.position,'hold',834.,CRATE_RANGE):
        return ActionResult(state,False,'Move closer to the lamp crate.')
    if not state.lamp_revealed: return ActionResult(state,False,'Open the crate with F first.')
    return ActionResult(replace(state,has_lamp=True,held_item='lamp'),True,
                        'You took the lamp. Press L to light it.')


def toggle_lamp(state: GameState) -> ActionResult:
    if not state.has_lamp: return ActionResult(state,False,'You do not have a lamp.')
    if state.held_item!='lamp': return ActionResult(state,False,'Select the lamp in your inventory first.')
    if state.hidden_barrel or state.capture_phase!='none': return ActionResult(state,False,'You cannot use the lamp right now.')
    lit=not state.lamp_lit
    return ActionResult(replace(state,lamp_lit=lit),True,'The lamp is lit.' if lit else 'The lamp is off.')


def toggle_wardrobe(state: GameState) -> ActionResult:
    if abs(position_xy(state.position)[1]-365)>20 or abs(position_xy(state.position)[0]-WARDROBE_X)>WARDROBE_RANGE:
        return ActionResult(state,False,'Move closer to the wardrobe.')
    if state.in_hammock or state.hidden_barrel: return ActionResult(state,False,'Stand up first.')
    opened = not state.wardrobe_open
    return ActionResult(replace(state,wardrobe_open=opened),True,
                        'You opened the wardrobe.' if opened else 'You closed the wardrobe.')


def change_outfit(state: GameState) -> ActionResult:
    if abs(position_xy(state.position)[1]-365)>20 or abs(position_xy(state.position)[0]-WARDROBE_X)>WARDROBE_RANGE:
        return ActionResult(state,False,'Move closer to the wardrobe.')
    if not state.wardrobe_open:return ActionResult(state,False,'Open the wardrobe with F first.')
    if state.in_hammock or state.hidden_barrel:return ActionResult(state,False,'Stand up first.')
    from voyage import progress as vp,save as vs
    v=vp(state)
    if v.get('captain_worn'):v['captain_worn']=False;state=vs(state,v)
    dressed=not state.disguised
    return ActionResult(replace(state,disguised=dressed,wardrobe_contents='player_clothes' if dressed else 'uniform'),True,
                        'You put on the guard uniform.' if dressed else 'You took off the uniform.')


def select_item(state: GameState, item: str) -> ActionResult:
    owned = {'cell_key':state.has_key,'blue_key':state.has_blue_key,'pistol':state.has_pistol,
             'lamp':state.has_lamp}
    if item not in owned or not owned[item]: return ActionResult(state,False,'You do not own that item.')
    if state.hidden_barrel or state.capture_phase != 'none': return ActionResult(state,False,'You cannot switch items right now.')
    if state.held_item == item: return ActionResult(state,False,'You are already holding it.')
    return ActionResult(replace(state,held_item=item),True,'You are holding '+{
        'cell_key':'the cell key.','blue_key':'the blue key.',
        'pistol':'the pistol.','lamp':'the lamp.'}[item])


def _guard_facing(kind: str, segment_name: str) -> int:
    segments=GUARD_ROUTES[kind]
    i=next(i for i,s in enumerate(segments) if s.name==segment_name)
    segment=segments[i]
    if segment.x2 != segment.x1: return 1 if segment.x2 > segment.x1 else -1
    # During a pause, face the direction travelled before stopping.
    previous=segments[i-1]
    return 1 if previous.x2 >= previous.x1 else -1


def can_guard_see(state: GameState, guard_elapsed: float, kind: str='patrol', now_ms: int | None=None) -> bool:
    if kind not in GUARD_ROUTES or not getattr(state,f'{kind}_alive') or (state.disguised and not story_progress(state).get('voyage',{}).get('armed')) or state.hidden_barrel or state.in_hammock or state.capture_phase!='none': return False
    from voyage import progress,watch_pose
    e=progress(state).get('escort')
    if e and (e.get('hidden') or kind==('dining' if e['kind']=='cook' else 'boatswain')):return False
    if kind=='cargo' and watch_pose(state,kind,now_ms or 0)[1]:return False
    pose = guard_pose_at(state,kind,guard_elapsed,now_ms) if now_ms is not None else guard_pose_for(kind,guard_elapsed)
    if pose.segment=='feast_sleep': return False
    px,py = position_xy(state.position)
    if state.position.zone=='cell':
        return kind=='patrol' and state.alert_started_ms<=int(now_ms or 0)<state.alert_until_ms and pose.y==500 and pose.x<=390
    dx = (px-pose.x)*(pose.facing or _guard_facing(kind,pose.segment))
    vision=GUARD_STYLES[kind]['vision']*(LAMP_VISION_MULTIPLIER if state.has_lamp and state.lamp_lit and state.held_item=='lamp' else 1.)
    return 12. <= dx <= vision*(1.3 if progress(state)['armed'] else 1.) and abs(py-pose.y) <= VISION_HEIGHT


def guard_notices_door(state: GameState, guard_elapsed: float, now_ms: int | None=None) -> bool:
    if not state.patrol_alive or not state.door_open or state.door_alerted or state.capture_phase!='none': return False
    pose = guard_pose_at(state,'patrol',guard_elapsed,now_ms) if now_ms is not None else guard_pose(guard_elapsed)
    return 410 <= pose.x <= 455 and abs(pose.y-500)<1


def raise_alert(state: GameState, guard_elapsed: float, now_ms: int) -> ActionResult:
    if not guard_notices_door(state,guard_elapsed,now_ms): return ActionResult(state,False,'No new alarm.')
    if type(now_ms) is not int or now_ms < 0: return ActionResult(state,False,'Invalid time.')
    return ActionResult(_start_alert(replace(state,door_alerted=True,suspect_started_ms=0,suspect_guard_zone="",suspect_guard_value=0.),guard_elapsed,now_ms,cell_first=True),True,'The guard noticed the open door!')


def _position_at_xy(x: float,y: float) -> Position:
    for name,(x1,y1,x2,y2) in STAIRS.items():
        progress=(y-y1)/(y2-y1)
        if 0<progress<1 and abs(x-(x1+(x2-x1)*progress))<.01:
            return Position(name,progress)
    return Position(_floor_zone(y,x),x)


def _guard_position(elapsed: float,kind: str='patrol',state: GameState | None=None,now_ms: int | None=None) -> Position:
    pose=guard_pose_at(state,kind,elapsed,now_ms) if state is not None and now_ms is not None else guard_pose_for(kind,elapsed)
    return _position_at_xy(pose.x,pose.y)

def start_capture(state: GameState, guard_elapsed: float, kind: str='patrol',now_ms: int | None=None) -> ActionResult:
    from voyage import progress
    if progress(state)['armed']:return ActionResult(state,False,'Incoming fire — duck or find cover!')
    if not can_guard_see(state,guard_elapsed,kind,now_ms): return ActionResult(state,False,'The guard cannot see you.')
    guard = _guard_position(guard_elapsed,kind,state,now_ms)
    return ActionResult(replace(state,capture_phase='active',capture_guard_zone=guard.zone,
                                capture_guard_value=guard.value,capture_guard=kind,hidden_barrel=''),
                        True,'The guard spotted you and is taking you back to the cell!')


def notice_wardrobe(state: GameState, elapsed: float, now_ms: int) -> ActionResult:
    if (state.wardrobe_suspected or not state.patrol_alive or not state.wardrobe_open
        or state.wardrobe_contents!='player_clothes' or state.capture_phase!='none'):
        return ActionResult(state,False,'No new clues at the wardrobe.')
    pose=guard_pose_at(state,'patrol',elapsed,now_ms)
    ahead=(WARDROBE_X-pose.x)*pose.facing
    if abs(pose.y-365)>1 or not 160<=pose.x<=520 or not -16<=ahead<=WARDROBE_SIGHT:
        return ActionResult(state,False,'The guard cannot see the wardrobe from here.')
    return ActionResult(replace(state,wardrobe_suspected=True),True,
                        'The key guard found your prison clothes! Keep your distance while disguised.')


def suspicion_step(state: GameState, near_disguised_player: bool, now_ms: int,
                   guard_position: Position | None = None) -> GameState:
    if state.capture_phase!='none': return state
    eligible=not story_progress(state).get('voyage',{}).get('captain_worn') and state.wardrobe_suspected and state.disguised and state.patrol_alive and not state.hidden_barrel and not state.in_hammock
    if not eligible or not near_disguised_player:
        if not state.suspect_started_ms: return state
        guard=Position(state.suspect_guard_zone,state.suspect_guard_value) if state.suspect_guard_zone else guard_position or Position('cabin',WARDROBE_X)
        x,y=position_xy(guard)
        return replace(state,suspect_started_ms=0,suspect_guard_zone='',suspect_guard_value=0.,
                       patrol_resume_ms=now_ms,patrol_resume_elapsed=_nearest_route_time('patrol',x,y))
    if not state.suspect_started_ms:
        guard=guard_position or Position('cabin',WARDROBE_X)
        return replace(state,suspect_started_ms=now_ms,suspect_guard_zone=guard.zone,suspect_guard_value=guard.value)
    if now_ms-state.suspect_started_ms>INSPECTION_MS:
        return replace(state,capture_phase='active',capture_guard_zone=state.suspect_guard_zone,
                       capture_guard_value=state.suspect_guard_value,capture_guard='patrol')
    return state


def inspect_disguise(state: GameState, elapsed: float, now_ms: int) -> ActionResult:
    guard=_guard_position(elapsed,'patrol',state,now_ms)
    gx,gy=position_xy(guard);px,py=position_xy(state.position)
    near=abs(px-gx)<=INSPECTION_RANGE and abs(py-gy)<=VISION_HEIGHT and state.position.zone!='cell'
    updated=suspicion_step(state,near,now_ms,guard)
    if updated==state: return ActionResult(state,False,'No change in the inspection.')
    message=('Your disguise has been exposed!' if updated.capture_phase=='active' else
             'The guard is inspecting you. Move away!' if updated.suspect_started_ms else 'You escaped the inspection.')
    return ActionResult(updated,True,message)

def finish_capture(state: GameState) -> ActionResult:
    if state.capture_phase!='active': return ActionResult(state,False,'No capture is in progress.')
    return ActionResult(initial_state(),True,'You are back in the locked cell.')


def route_points(start: Position, goal: Position) -> list[tuple[float,float]]:
    """Shortest continuous walking path on the decks, stairs and mast."""
    coords={'M':(MAST_X,245.),'MT':(MAST_X,MAST_TOP_Y),
            'S':position_xy(start),'T':position_xy(goal)}
    for name,values in STAIRS.items():
        coords[name+'_bottom']=values[:2];coords[name+'_top']=values[2:]
    edges: dict[str,list[tuple[str,float]]]={key:[] for key in coords}
    def link(a: str,b: str) -> None:
        distance=hypot(coords[a][0]-coords[b][0],coords[a][1]-coords[b][1])
        edges[a].append((b,distance));edges[b].append((a,distance))
    for name in STAIRS: link(name+'_bottom',name+'_top')
    link('M','MT')
    fixed=[key for key in coords if key not in ('S','T')]
    for i,a in enumerate(fixed):
        for b in fixed[i+1:]:
            if coords[a][1]==coords[b][1]: link(a,b)
    def attach(name: str,pos: Position) -> None:
        if pos.zone in STAIRS: link(name,pos.zone+'_bottom');link(name,pos.zone+'_top')
        elif pos.zone=='mast': link(name,'M');link(name,'MT')
        else:
            for node in fixed:
                if coords[node][1]==coords[name][1]: link(name,node)
    attach('S',start);attach('T',goal)
    if coords['S'][1]==coords['T'][1] and start.zone not in STAIRS and goal.zone not in STAIRS: link('S','T')
    if start.zone==goal.zone and start.zone in (*STAIRS,'mast'): link('S','T')
    queue=[(0.,'S')];best={'S':0.};prev={}
    while queue:
        distance,node=heappop(queue)
        if node=='T': break
        if distance>best[node]: continue
        for other,weight in edges[node]:
            new=distance+weight
            if new < best.get(other,float('inf'))-1e-8:
                best[other]=new;prev[other]=node;heappush(queue,(new,other))
    names=['T']
    while names[-1]!='S': names.append(prev[names[-1]])
    names.reverse()
    points=[coords[name] for name in names]
    return [point for i,point in enumerate(points) if i==0 or point != points[i-1]]


def capture_paths(state: GameState) -> tuple[list[tuple[float,float]],list[tuple[float,float]]]:
    if state.capture_phase!='active': raise ValueError('No capture is active')
    guard = Position(state.capture_guard_zone,state.capture_guard_value)
    return (route_points(guard,state.position),route_points(state.position,Position('cell',230.)))


# Story rules extend the continuous ship without changing its saved coordinates.
def valid_story_state(raw: object) -> bool:
    if not isinstance(raw, str) or len(raw) > 12_000:
        return False
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return False
    if not isinstance(value, dict) or set(value) - {'items','inspected','crate_open','crate_marked','whistle_used','signal','voyage'}:
        return False
    for key, allowed in (('items', ITEMS), ('inspected', STORY_POINTS)):
        entries = value.get(key, [])
        if not isinstance(entries, list) or any(not isinstance(x,str) or x not in allowed for x in entries):
            return False
        if len(entries) != len(set(entries)):
            return False
    if any(type(value.get(k,False)) is not bool for k in ('crate_open','crate_marked','whistle_used')):
        return False
    if 'voyage' in value:
        from voyage import valid
        try:
            if not valid(value['voyage']): return False
        except (TypeError,ValueError,KeyError):return False
    items = value.get('items', [])
    v=value.get('voyage',{})
    if ('captain_uniform' in items or v.get('captain_worn')) and 'officer' not in v.get('concealed',{}):return False
    if v.get('captain_worn') and 'captain_uniform' not in items:return False
    if value.get('crate_open') and 'crowbar' not in items and 'cook' not in value.get('voyage',{}).get('paid',[]):
        return False
    if value.get('crate_marked') and (not value.get('crate_open') or not {'manifest','seal'} <= set(items)):
        return False
    signal = value.get('signal')
    if signal is not None:
        if not isinstance(signal,dict) or set(signal) != {'x','y','started','until'}:
            return False
        if any(type(signal[k]) not in (int,float) or not isfinite(signal[k]) for k in ('x','y')):
            return False
        if any(type(signal[k]) is not int or signal[k] < 0 for k in ('started','until')):
            return False
        if signal['until']-signal['started'] != 4000 or 'whistle' not in items:
            return False
    return True


def story_progress(state: GameState) -> dict:
    return {'items': [], 'inspected': [], 'crate_open': False, 'crate_marked': False,
            'whistle_used': False, **json.loads(state.story_state)}


def reading_time(state: GameState, wall_now: int) -> int:
    """Time spent with a document open. Zero when nothing paused the game
    (multiplayer never pauses the shared ship), so closing adds nothing."""
    return max(0,wall_now-state.paused_at_ms) if state.paused_at_ms else 0


def game_now_ms(state: GameState, wall_now: int) -> int:
    """Alarm and patrol time excludes reading time, including across reloads."""
    return (state.paused_at_ms or wall_now) - state.paused_total_ms


def opponents_remaining(state: GameState) -> int:
    return int(state.sleeper_alive) + sum(getattr(state, f'{kind}_alive') for kind in GUARD_ROUTES)


def crate_ready(state: GameState) -> bool:
    progress = story_progress(state)
    return state.dining_alive and progress['crate_open']


def story_action(state: GameState, kind: str, point_id: str, wall_now: int) -> ActionResult:
    """Authoritative local interactions. Opening a confirmation never wins a game."""
    if state.ending:
        return ActionResult(state,False,'The journey has already ended.')
    if point_id in ('helm','lifeboat') or point_id.startswith('coins_'):
        from voyage import voyage_action
        return voyage_action(state,kind,point_id,wall_now)
    progress = story_progress(state)

    def updated(**changes):
        return replace(state, story_state=json.dumps(progress, separators=(',',':'), sort_keys=True), **changes)

    def document(doc_id, message):
        return ActionResult(updated(reading=doc_id, paused_at_ms=max(1,wall_now)),True,message)

    if kind == 'close_reading':
        if not state.reading:
            return ActionResult(state,False,'No document is open.')
        return ActionResult(replace(state,reading='',paused_at_ms=0,
            paused_total_ms=state.paused_total_ms + reading_time(state,wall_now)),True,'Back to the ship.')
    if state.reading and kind != 'finish':
        return ActionResult(state,False,'Close the document first.')
    if state.capture_phase != 'none':
        return ActionResult(state,False,'You cannot do this while being captured.')
    if kind == 'journal':
        return document('journal','The journal is open. The game is paused.')
    if state.hidden_barrel or state.in_hammock:
        return ActionResult(state,False,'Leave your hiding place before interacting.')
    if kind == 'whistle':
        if 'whistle' not in progress['items']:
            return ActionResult(state,False,'You do not have a whistle.')
        now = game_now_ms(state,wall_now)
        if progress.get('signal') and now < progress['signal']['until']:
            return ActionResult(state,False,'Wait for the whistle signal to fade.')
        progress['whistle_used'] = True
        x,y = position_xy(state.position)
        progress['signal'] = {'x':x,'y':y,'started':now,'until':now+4000}
        return ActionResult(updated(),True,'A short signal! Nearby crew turn towards the sound for four seconds. Move away before they see you.')
    point = STORY_POINTS.get(point_id)
    if point is None or state.position.zone != point['zone'] or abs(state.position.value-point['x']) > point['reach']:
        return ActionResult(state,False,'Move closer to the object.')
    if kind == 'finish' and point_id == 'cell_floor':
        if state.reading != 'confirm_castaway':
            return ActionResult(state,False,'Inspect the exit and confirm your choice first.')
        if 'sleeping_pills' not in progress['items'] or not opponents_remaining(state):
            return ActionResult(state,False,'The requirements for this escape are not met.')
        return ActionResult(replace(state,ending='castaway',reading='',paused_at_ms=0,
            paused_total_ms=state.paused_total_ms + reading_time(state,wall_now),
            alert_started_ms=0,alert_until_ms=0,suspect_started_ms=0),True,ENDINGS['castaway']['title'])
    if kind == 'finish':
        required = 'confirm_takeover' if point_id == 'helm' else 'confirm_crate' if point_id == 'return_crate' else None
        if state.reading != required or required is None:
            return ActionResult(state,False,'Inspect the exit and confirm your choice first.')
        ending = 'takeover' if point_id == 'helm' else 'crate'
        if (ending == 'takeover' and opponents_remaining(state)) or (ending == 'crate' and not crate_ready(state)):
            return ActionResult(state,False,'The requirements for this escape are not met.')
        return ActionResult(replace(state,ending=ending,reading='',paused_at_ms=0,
            paused_total_ms=state.paused_total_ms + reading_time(state,wall_now),
            alert_started_ms=0,alert_until_ms=0,suspect_started_ms=0),True,ENDINGS[ending]['title'])
    if state.reading:
        return ActionResult(state,False,'Close the document first.')
    if kind == 'take':
        item = 'captain_uniform' if point_id=='seal_chest' and 'officer' in progress.get('voyage',{}).get('concealed',{}) else point.get('item')
        if not item or point_id not in progress['inspected']:
            return ActionResult(state,False,'Open or inspect it with F before taking anything.')
        if item=='captain_uniform':
            from voyage import wear_captain
            return wear_captain(state)
        if item in progress['items']:
            return ActionResult(state,False,'You already have this item.')
        progress['items'].append(item)
        return ActionResult(updated(),True,f"You took {ITEMS[item]['name'].lower()}. Open your inventory with I.")
    if kind != 'inspect':
        return ActionResult(state,False,'Unknown story action.')
    if point_id == 'helm':
        remaining = opponents_remaining(state)
        if remaining:
            return ActionResult(state,False,f'{remaining} of the ten opponents are still alive. They will stop you at the helm.')
        return document('confirm_takeover','Take over the ship?')
    if point_id == 'return_crate':
        if not state.dining_alive:
            return ActionResult(state,False,'The cook is dead. Nobody will carry the return crate ashore. The helm remains a possible escape.')
        if crate_ready(state):
            return document('confirm_crate','Hide in the crate and leave the ship?')
        if point_id not in progress['inspected']:
            progress['inspected'].append(point_id)
        if not progress['crate_open'] and 'crowbar' in progress['items']:
            progress['crate_open'] = True
            return ActionResult(updated(),True,'You opened crate 07. Press F to hide inside.')
        return ActionResult(updated(),False,'Find a crowbar, or bribe the cook with two coins.')
    if point_id == 'cell_floor':
        if 'sleeping_pills' not in progress['items']:
            return ActionResult(state,False,'The cold, damp floor of your cell.')
        if not opponents_remaining(state):
            return ActionResult(state,False,'Nobody is left on board to find you here.')
        return document('confirm_castaway','Swallow the sleeping pills?')
    if point_id not in progress['inspected']:
        progress['inspected'].append(point_id)
    if point['kind'] == 'chest':
        return ActionResult(updated(),True,'Chest opened. Press E to take the item.' if point.get('item') not in progress['items'] else 'The chest is empty.')
    return document(point_id,'You found a clue. It is recorded in the journal.')
