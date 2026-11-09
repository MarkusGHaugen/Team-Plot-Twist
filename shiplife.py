"""Things to do aboard that are not escapes by themselves. All times are game milliseconds."""
import logic as L
from voyage import progress, save

CANNON = L.Position('upper_deck', L.STORY_POINTS['cannon']['x'])
FUSE_MS = 800


def fire_cannon(s, guard_elapsed, now):
    """Light the loaded deck cannon with a lamp. The blast brings every pirate running."""
    v = progress(s)
    point = L.STORY_POINTS['cannon']
    if s.ending or s.reading or s.capture_phase != 'none' or v.get('escort'):
        return L.ActionResult(s, False, 'You cannot do this now.')
    if s.position.zone != point['zone'] or abs(s.position.value - point['x']) > point['reach']:
        return L.ActionResult(s, False, 'Move closer to the cannon.')
    if s.hidden_barrel or s.in_hammock:
        return L.ActionResult(s, False, 'Leave your hiding place first.')
    if 'cannon_fired' in v:
        return L.ActionResult(s, False, 'The cannon is empty. Powder and shot are locked away in the armory.')
    if not (s.has_lamp and s.lamp_lit and s.held_item == 'lamp'):
        return L.ActionResult(s, False, 'The cannon is loaded, but you need a flame for the fuse. Hold a lit lamp.')
    boom = now + FUSE_MS
    v['cannon_fired'] = boom
    s = L._start_alert(save(s, v), guard_elapsed + FUSE_MS / 1000, boom, first_goal=CANNON)
    return L.ActionResult(s, True, 'The fuse hisses… BOOM! Every pirate on board will come running. Hide!')
