"""Read-only suggestions from saved discoveries, never from undiscovered secrets."""
from logic import crate_ready, game_now_ms, opponents_remaining, story_progress
from voyage import boat_ready, captain_ready, progress
from feast import SLEEP_MS, active as meal_active, crew_asleep


def journal_hints(state, wall_now_ms: int) -> list[dict[str, str]]:
    """Return up to three stable suggestions. No save writes or clock changes."""
    if state.ending:
        return []
    story, voyage = story_progress(state), progress(state)
    items, known = set(story['items']), set(story['inspected'])
    now = game_now_ms(state, wall_now_ms)
    alarm = now < state.alert_until_ms
    suggestions = []

    def add(key, title, status, text, clearer):
        suggestions.append(dict(id=key, title=title, status=status, text=text, clearer=clearer))

    if state.capture_phase != 'none':
        add('capture', 'Back to the cell', 'Wait',
            'Let the capture sequence finish before planning your next move.',
            'Once you are back in the cell, check your inventory and the door again.')
        return suggestions

    if not state.door_open:
        if state.has_key:
            add('cell', 'The cell door', 'Next action',
                'You still have the key. The locked door need not stop you.',
                'Move beside the cell door and press F to unlock it.')
        elif 'opening_letter' in known:
            add('cell', 'A passing opportunity', 'Next action',
                'The letter mentions a key carried past your cell.',
                'Stand near the cell door. Press E when the key guard passes close enough, then F to open the door.')
        else:
            add('cell', 'A message nearby', 'Explore',
                'Someone left a folded letter beside your bed.',
                'Approach the folded letter and press F to read it. It may explain your first way forward.')

    # A meal already in motion is more urgent than equipment collecting.
    stew_known = voyage.get('stew_drugged') or ('sleeping_pills' in items and 'stew_pot' in known)
    if stew_known:
        if voyage.get('stew_drugged'):
            if crew_asleep(state, now):
                add('stew', 'A quiet ship', 'Opportunity',
                    'The living crew are asleep. This opportunity will not last.',
                    'Head towards the helm while they sleep. A gunshot or the cannon can wake them; check your surroundings before acting.')
            elif meal_active(state, now) and now < min(voyage['feast']['sleep'].values()) + SLEEP_MS:
                add('stew', 'The crew meal', 'Wait',
                    'The meal is still unfolding. Stay out of sight and watch the crew.',
                    'Wait until all living crew have fallen asleep before trying the helm. Keep quiet; loud alarms can interrupt the plan.')
            else:
                add('stew', 'The crew meal', 'Plan ended',
                    'The sleeping opportunity has ended.',
                    'The stew cannot be drugged a second time. Revisit another possibility you have discovered.')
        elif not state.dining_alive:
            add('stew', 'The crew meal', 'Unavailable',
                'The cook can no longer serve the stew.',
                'This plan needs a living cook. Keep exploring other possibilities in your discoveries.')
        elif alarm or voyage['armed']:
            add('stew', 'The crew meal', 'Wait',
                'The crew will not eat while the ship is in turmoil.',
                'You cannot add the pills during a search or gunfight. Do not approach the pot expecting the plan to work yet.')
        else:
            add('stew', 'Something in the stew', 'Next action',
                'The pills and the shared meal suggest a quiet distraction.',
                'Approach the galley stew with the sleeping pills and press F. Hide while the cook serves it.')

    if items & {'sail', 'rope'} or known & {'boat_window', 'lifeboat'} or 'boatswain' in voyage['paid']:
        if boat_ready(state):
            add('dinghy', 'A small boat', 'Next action',
                'Your dinghy equipment is ready. Find a safe moment to reach the winch.',
                'At the dinghy winch on the aft deck, press F to inspect your escape, then confirm if you are ready to leave.')
        elif 'sail' not in items:
            add('dinghy', 'A small boat', 'Missing equipment',
                'A boat needs a sail to carry you away.',
                'Explore the sail store and inspect its chests. Take the sail with E after opening its chest with F.')
        else:
            alternative = state.boatswain_alive and 'boatswain' not in voyage['paid']
            add('dinghy', 'A small boat', 'Missing equipment',
                'The sail is useful, but the dinghy still needs a way down.',
                'Find rope in the sail store.' +
                (' Alternatively, with the sail and three coins, approach the boatswain and press T when the crew are calm.' if alternative else '') +
                ' Having the equipment does not protect you from nearby crew.')

    crate_known = bool(known & {'opening_letter', 'manifest_desk', 'return_crate'} or 'manifest' in items or story['crate_open'])
    if crate_known:
        if not state.dining_alive:
            add('crate', 'Return crate 07', 'Unavailable',
                'Without the cook, nobody will take the return crate ashore.',
                'The crate plan is no longer possible. Other discoveries may offer another escape.')
        elif crate_ready(state):
            add('crate', 'Return crate 07', 'Next action',
                'The crate is open, and the cook is still aboard.',
                'Reach return crate 07 on the middle deck. Press F and confirm only when you want to leave.')
        elif 'crowbar' in items:
            add('crate', 'Return crate 07', 'Next action',
                'Your crowbar could deal with the nailed lid.',
                'Find return crate 07 on the middle deck and press F to open it. You can inspect it again before deciding to escape.')
        else:
            add('crate', 'Return crate 07', 'Missing equipment',
                'The cook sends crates ashore, but this lid needs opening.',
                'Look for a tool that can pry the lid open, or approach the cook with two coins and press T when the crew are calm.')

    if 'captains_log' in known or 'captain_uniform' in items or 'officer' in voyage.get('concealed', {}):
        if captain_ready(state):
            add('command', 'A convincing captain', 'Wait' if alarm else 'Next action',
                'The disguise is ready, but the search must settle.' if alarm else 'Your captain disguise is ready for the helm.',
                'Wait until the search ends, then reach the helm and press F.' if alarm else
                'Reach the helm and press F to command the ship. This action can end your journey.')
        else:
            add('command', 'A convincing captain', 'Missing requirement',
                'The officer and a convincing uniform stand between you and command.',
                'Conceal the officer with a barrel ambush, then take and wear the captain uniform from the captain cabin chest. A gunfight prevents this plan.'
                if 'officer' not in voyage.get('concealed', {}) else
                'Take and wear the captain uniform from the captain cabin chest. You must be disguised and out of a gunfight before commanding the helm.')

    if 'opening_letter' in known:
        remaining = opponents_remaining(state)
        add('takeover', 'Taking the helm', 'Missing requirement' if remaining else 'Next action',
            'The crew can still stop a direct takeover.' if remaining else 'No living opponent remains to stop you at the helm.',
            'A direct takeover requires defeating every remaining opponent. You can still pursue another discovered plan.' if remaining else
            'Reach the helm and press F when you are ready to take the ship.')

    if not suggestions:
        add('explore', 'Read the ship', 'Explore',
            'Look for documents and useful objects as you explore.',
            'Press F near a document or chest to inspect it. Press E to take an exposed item. Your discoveries will help connect the clues here.')
    # Immediate personal obstacles stay first; opportunities precede shopping
    # lists, and permanently blocked plans do not crowd out viable choices.
    rank = {'Opportunity': 0, 'Next action': 1, 'Wait': 2,
            'Missing equipment': 3, 'Missing requirement': 3, 'Explore': 4,
            'Unavailable': 5, 'Plan ended': 5}
    return sorted(suggestions, key=lambda h: -1 if h['id'] == 'cell' else rank[h['status']])[:3]
