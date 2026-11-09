"""Drugged stew: the cook serves, the crew eat together, fall asleep and wake later.

All times are game milliseconds. The plan is fixed when the pills go into the pot,
so the server and the Canvas compute identical crew poses from the saved plan.
"""
import math
import logic as L

SERVE_DELAY_MS = 5_000      # the cook serves five seconds after the pills go in
WALK_SPEED = 95.            # hungry crew hurry to the table
RETURN_SPEED = 60.          # and stagger back, groggy
EAT_MS = 6_000              # everyone eats together once the last one sits down
DOZE_STEP_MS = 350          # they nod off one after another around the table
SLEEP_MS = 120_000          # two minutes of deep sleep
POT = L.Position('kitchen', 1200.)
ORDER = ('dining', 'patrol', 'cargo', 'lookout', 'sleeper', 'sailor', 'armorer', 'medic', 'boatswain', 'officer')
SEATS = {'patrol': 945., 'cargo': 985., 'lookout': 1025., 'sleeper': 1065., 'dining': 1105.,
         'sailor': 1165., 'armorer': 1205., 'medic': 1245., 'boatswain': 1285., 'officer': 1325.}
WATCH = ('cargo', 'sleeper')


def length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def _route(*stops):
    points = [list(L.position_xy(stops[0]))]
    for a, b in zip(stops, stops[1:]):
        points.extend([round(p[0], 2), round(p[1], 2)] for p in L.route_points(a, b)[1:])
    points = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
    return points if len(points) > 1 else points + [list(points[0])]


def _walkable(x, y):
    """The walkable position for a pose; snaps to the nearest deck or stair if it is off by a hair."""
    try:
        return L._position_at_xy(x, y)
    except ValueError:
        options = []
        for zone, (left, right, fy) in L.FLOORS.items():
            if zone == 'cell':
                continue
            fx = min(max(x, left), right)
            options.append((math.dist((x, y), (fx, fy)), L.Position(zone, fx)))
        for zone, (x1, y1, x2, y2) in L.STAIRS.items():
            dx, dy = x2 - x1, y2 - y1
            f = min(.99, max(.01, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
            options.append((math.dist((x, y), (x1 + dx * f, y1 + dy * f)), L.Position(zone, f)))
        return min(options, key=lambda o: o[0])[1]


def _watch_pair(s, v):
    return 'watch_start' in v and s.cargo_alive and s.sleeper_alive


def plan(s, guard_elapsed, now):
    """Fix every living crew member's walk, meal, sleep and return when the stew is drugged."""
    from voyage import progress
    v = progress(s)
    gather = now + SERVE_DELAY_MS
    crew = [k for k in ORDER if getattr(s, k + '_alive')]
    paths, returns, origins = {}, {}, {}
    for k in crew:
        pose = L.guard_pose_at(s, k, guard_elapsed + SERVE_DELAY_MS / 1000, gather)
        start = _walkable(pose.x, pose.y)
        origins[k] = start
        seat = L.Position('dining', SEATS[k])
        paths[k] = _route(start, POT, seat) if k == 'dining' else _route(start, seat)
        returns[k] = _route(seat, start)
    last = max(gather + length(paths[k]) / WALK_SPEED * 1000 for k in crew)
    sleep = {k: int(last + EAT_MS + i * DOZE_STEP_MS) for i, k in enumerate(crew)}
    pair = _watch_pair(s, v)
    resume = {k: L._nearest_route_time(k, *L.position_xy(origins[k]))
              for k in crew if k in L.GUARD_ROUTES and not (pair and k in WATCH)}
    return {'drugged': now, 'gather': gather, 'paths': paths, 'returns': returns,
            'sleep': sleep, 'resume': resume, 'watch': pair}


def back(f, kind):
    """When this crew member is back at their post and their routine resumes."""
    own = f['sleep'][kind] + SLEEP_MS + length(f['returns'][kind]) / RETURN_SPEED * 1000
    if f['watch'] and kind in WATCH:
        return max(f['sleep'][k] + SLEEP_MS + length(f['returns'][k]) / RETURN_SPEED * 1000
                   for k in WATCH if k in f['sleep'])
    return own


def watch_shift(f):
    """The cargo/sleeper rotation pauses for the meal and continues where it stopped."""
    return int(back(f, 'cargo') - f['gather']) if f['watch'] else 0


def _along(path, distance):
    from voyage import along
    total = length(path)
    x, y = along(path, distance / total if total else 1)
    ahead = along(path, min(total, distance + 6) / total if total else 1)
    behind = along(path, max(0, distance - 6) / total if total else 0)
    facing = 1 if ahead[0] > behind[0] else -1 if ahead[0] < behind[0] else 0
    return x, y, facing


def pose(s, kind, now):
    """The crew member's pose during the meal, or None outside it."""
    from voyage import progress
    f = progress(s).get('feast')
    if not f or kind not in f['paths'] or not getattr(s, kind + '_alive') or now < f['gather']:
        return None
    path = f['paths'][kind]
    walked = (now - f['gather']) / 1000 * WALK_SPEED
    if walked < length(path):
        x, y, facing = _along(path, walked)
        return L.GuardPose(x, y, 'feast_serve' if kind == 'dining' else 'feast_walk', 0., facing or 1)
    seat_x, seat_y = path[-1]
    table = 1 if seat_x < 1105 else -1   # face the middle of the mess hall
    if now < f['sleep'][kind]:
        return L.GuardPose(seat_x, seat_y, 'feast_eat', 0., table)
    if now < f['sleep'][kind] + SLEEP_MS:
        return L.GuardPose(seat_x, seat_y, 'feast_sleep', 0., table)
    ret = f['returns'][kind]
    walked = (now - f['sleep'][kind] - SLEEP_MS) / 1000 * RETURN_SPEED
    if walked < length(ret):
        x, y, facing = _along(ret, walked)
        return L.GuardPose(x, y, 'feast_return', 0., facing or 1)
    if now < back(f, kind):
        x, y = ret[-1]
        return L.GuardPose(x, y, 'feast_post', 0., 1)
    return None


def resumed(s, kind, now):
    """After the meal, routine crew continue their round from where they left it."""
    from voyage import progress
    v = progress(s)
    f = v.get('feast')
    if not f or kind not in f['resume'] or not getattr(s, kind + '_alive'):
        return None
    done = back(f, kind)
    if now < done:
        return None
    if kind == 'patrol' and (s.suspect_started_ms or s.patrol_resume_ms >= done):
        return None
    g = v.get('guide')
    if g and kind == ('dining' if g['kind'] == 'cook' else 'boatswain') and g['started'] > f['drugged']:
        return None
    return L.guard_pose_for(kind, f['resume'][kind] + (now - done) / 1000)


def asleep(s, kind, now):
    p = pose(s, kind, now)
    return p is not None and p.segment == 'feast_sleep'


def crew_asleep(s, now):
    """True while every living crew member sleeps at the table."""
    crew = [k for k in ORDER if getattr(s, k + '_alive')]
    return bool(crew) and all(asleep(s, k, now) for k in crew)


def active(s, now):
    from voyage import progress
    f = progress(s).get('feast')
    return bool(f) and any(now < back(f, k) for k in f['sleep'] if getattr(s, k + '_alive'))


def drug_stew(s, guard_elapsed, now):
    from voyage import progress, save
    v = progress(s)
    p = L.story_progress(s)
    point = L.STORY_POINTS['stew_pot']
    if s.ending or s.reading or s.capture_phase != 'none' or v.get('escort'):
        return L.ActionResult(s, False, 'You cannot do this now.')
    if s.position.zone != point['zone'] or abs(s.position.value - point['x']) > point['reach']:
        return L.ActionResult(s, False, 'Move closer to the pot.')
    if s.hidden_barrel or s.in_hammock:
        return L.ActionResult(s, False, 'Leave your hiding place first.')
    if 'sleeping_pills' not in p['items']:
        return L.ActionResult(s, False, 'You have nothing to put in the stew.')
    if v.get('stew_drugged'):
        return L.ActionResult(s, False, 'The stew is already drugged.')
    if not s.dining_alive:
        return L.ActionResult(s, False, 'The cook is dead. Nobody will serve the stew.')
    if v['armed'] or s.alert_started_ms <= now < s.alert_until_ms:
        return L.ActionResult(s, False, 'Nobody eats during an alarm.')
    v['stew_drugged'] = True
    v['feast'] = plan(s, guard_elapsed, now)
    return L.ActionResult(save(s, v), True, 'You crush the sleeping pills into the stew. The cook will serve it any moment. Hide!')


def interrupt(s, v, now):
    """An alarm wakes everyone and ends the meal. The watch rotation keeps its pause."""
    f = v.pop('feast', None)
    if f and now >= f['gather'] and f['watch'] and 'watch_start' in v:
        v['watch_start'] += watch_shift(f)
    return v


def valid(f, items_ok=True):
    def path_ok(path):
        from voyage import path_valid
        return path_valid(path)
    if not isinstance(f, dict) or set(f) != {'drugged', 'gather', 'paths', 'returns', 'sleep', 'resume', 'watch'}:
        return False
    if any(type(f[k]) is not int or f[k] < 0 for k in ('drugged', 'gather')) or f['gather'] - f['drugged'] != SERVE_DELAY_MS:
        return False
    if type(f['watch']) is not bool:
        return False
    crew = set(f['paths'])
    if not crew or not crew <= set(ORDER) or set(f['returns']) != crew or set(f['sleep']) != crew:
        return False
    if not set(f['resume']) <= crew or any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 for t in f['resume'].values()):
        return False
    for k in crew:
        if not path_ok(f['paths'][k]) or not path_ok(f['returns'][k]):
            return False
        if f['paths'][k][-1] != [SEATS[k], 365.] or f['returns'][k][0] != [SEATS[k], 365.]:
            return False
        if type(f['sleep'][k]) is not int or f['sleep'][k] < f['gather']:
            return False
    return True
