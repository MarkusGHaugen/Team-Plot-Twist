"""Authored English game content."""

ITEMS = {'crowbar': {'name': 'Crowbar', 'icon': '🔧', 'use': 'Pry open nailed lids.'},
 'rope': {'name': 'Rope', 'icon': '🪢', 'use': 'A strong rope. It may be useful at the dinghy later.'},
 'whistle': {'name': 'Boatswain whistle',
             'icon': '\U0001fa88',
             'use': 'B: nearby crew turn towards the sound for four seconds outside an alarm.'},
 'manifest': {'name': 'Cargo manifest',
              'icon': '📜',
              'use': 'Return crate 07 is due ashore at the next port.'},
 'seal': {'name': 'Officer seal', 'icon': '⚜', 'use': 'A brass keepsake. Crate 07 no longer needs a stamp.'},
 'sail': {'name': 'Folded sail', 'icon': '⛵', 'use': 'Rig the dinghy before leaving the ship.'}}

STORY_POINTS = {'opening_letter': {'zone': 'cell', 'x': 205.0, 'reach': 48.0, 'name': 'Folded letter', 'kind': 'document'},
 'tools_chest': {'zone': 'hold',
                 'x': 510.0,
                 'reach': 32.0,
                 'name': 'Tool chest',
                 'kind': 'chest',
                 'item': 'crowbar'},
 'rope_chest': {'zone': 'sail_store',
                'x': 1715.0,
                'reach': 30.0,
                'name': 'Sailmaker chest',
                'kind': 'chest',
                'item': 'rope'},
 'whistle_chest': {'zone': 'crew_room',
                   'x': 1900.0,
                   'reach': 30.0,
                   'name': 'Boatswain chest',
                   'kind': 'chest',
                   'item': 'whistle'},
 'manifest_desk': {'zone': 'officers',
                   'x': 2380.0,
                   'reach': 30.0,
                   'name': 'Cargo manifest',
                   'kind': 'document',
                   'item': 'manifest'},
 'seal_chest': {'zone': 'captain',
                'x': 2460.0,
                'reach': 28.0,
                'name': 'Captain chest',
                'kind': 'chest',
                'item': 'seal'},
 'captains_log': {'zone': 'captain', 'x': 2350.0, 'reach': 28.0, 'name': 'Captain log', 'kind': 'document'},
 'boat_window': {'zone': 'crew_room', 'x': 2140.0, 'reach': 27.0, 'name': 'Sea window', 'kind': 'window'},
 'lifeboat': {'zone': 'aft_deck', 'x': 1660.0, 'reach': 27.0, 'name': 'Dinghy winch', 'kind': 'winch'},
 'return_crate': {'zone': 'kitchen',
                  'x': 1260.0,
                  'reach': 30.0,
                  'name': 'Return crate 07',
                  'kind': 'return_crate'},
 'helm': {'zone': 'aft_deck', 'x': 1980.0, 'reach': 30.0, 'name': 'Helm', 'kind': 'helm'},
 'sail_chest': {'zone': 'sail_store',
                'x': 1530.0,
                'reach': 30.0,
                'name': 'Sail chest',
                'kind': 'chest',
                'item': 'sail'},
 'coins_hold': {'zone': 'hold', 'x': 760.0, 'reach': 30.0, 'name': 'Coin cache', 'kind': 'coins'},
 'coins_provisions': {'zone': 'provisions',
                      'x': 2420.0,
                      'reach': 30.0,
                      'name': 'Coin cache',
                      'kind': 'coins'},
 'coins_chart': {'zone': 'chart_room', 'x': 2200.0, 'reach': 30.0, 'name': 'Coin cache', 'kind': 'coins'},
 'coins_crew': {'zone': 'crew_room', 'x': 2010.0, 'reach': 30.0, 'name': 'Coin cache', 'kind': 'coins'}}

DOCUMENTS = {'opening_letter': {'title': 'You are not the only one who wants to leave',
                    'kicker': 'LETTER IN THE CELL',
                    'body': 'They locked you up because you saw the captain falsifying the cargo manifests. '
                            'At the next port, he plans to silence the witness.\n'
                            '\n'
                            'I cannot open your door. But the guard carries a key when he passes the stairs. '
                            'Wait for your chance.\n'
                            '\n'
                            'The cook sends return crates ashore. The officer authorises the cargo. If you '
                            'choose to take the ship yourself, nobody can remain to stop you at the helm.\n'
                            '\n'
                            '— A friend among the crew',
                    'hint': 'Watch the guard. E steals the key when he is close; F opens the door.'},
 'tools_chest': {'title': 'Tool chest',
                 'kicker': 'HOLD',
                 'body': 'A sturdy crowbar.',
                 'hint': 'F opens the chest. E takes the crowbar.'},
 'rope_chest': {'title': 'A reliable rope',
                'kicker': 'SAIL STORE',
                'body': 'A long rope for the dinghy tackle.',
                'hint': 'F opens the chest. E takes the rope. Use it to lower the dinghy.'},
 'whistle_chest': {'title': 'Boatswain whistle',
                   'kicker': 'CREW QUARTERS',
                   'body': 'One short signal turns nearby crew towards the sound for four seconds. They '
                           'ignore it during an alarm.',
                   'hint': 'E takes the whistle. B blows it.'},
 'manifest_desk': {'title': 'Cargo manifest · next port',
                   'kicker': 'HARBOUR OFFICE / COPY 07',
                   'body': '07 · Empty galley crate returns to the quay warehouse tomorrow morning. The cook '
                           'accompanies the delivery.\n'
                           '\n'
                           'A passenger could hide inside. The lid is nailed shut.',
                   'hint': 'The manifest is a clue. Find a crowbar or pay the cook two coins.'},
 'seal_chest': {'title': 'Officer seal',
                'kicker': 'CAPTAIN CABIN',
                'body': 'A brass stamp matching the cargo manifest.',
                'hint': 'E takes the seal. It can be reused.'},
 'captains_log': {'title': 'The captain last entry',
                  'kicker': 'PRIVATE LOG',
                  'body': 'The prisoner knows too much. The officer has the papers. The cook only knows his '
                          'own delivery. We reach port before sunset.\n'
                          '\n'
                          'The helm on the aft deck steers the ship. Nobody outside my crew shall command it '
                          'while one of us still stands.',
                  'hint': 'Takeover: defeat all ten opponents and use the helm on the aft deck.'},
 'boat_window': {'title': 'A boat beyond the window',
                 'kicker': 'VIEW FROM THE CREW QUARTERS',
                 'body': 'A dinghy hangs outside. Its winch is on the aft deck. A folded sail lies in the '
                         'sail store.',
                 'hint': 'Find the sail. Repair the tackle or pay the boatswain.'},
 'lifeboat': {'title': 'Dinghy tackle',
              'kicker': 'A WAY TO SHORE',
              'body': 'The dinghy needs a sail. Rope will let you lower it yourself. The '
                      'boatswain will handle the tackle for three coins.',
              'hint': 'T near the boatswain offers a bribe. Bring the sail first.'},
 'return_crate': {'title': 'Return crate 07',
                  'kicker': 'THE COOK DELIVERY',
                  'body': 'Crate 07 goes ashore tomorrow morning. Pry open the lid or pay the cook to help. '
                          'He must survive to accompany the delivery.',
                  'hint': 'No manifest, stamp or sail is needed.'},
 'confirm_crate': {'title': 'Hide in the return crate?',
                   'kicker': 'FINISH THE JOURNEY',
                   'body': 'The lid is open. Hide inside and wait until morning. The cook will carry the '
                           'crate ashore.',
                   'hint': 'You can cancel and keep exploring.'},
 'confirm_takeover': {'title': 'Set a course for freedom?',
                      'kicker': 'FINISH THE JOURNEY',
                      'body': 'Nobody remains to stop you. You place your hands on the helm.\n'
                              '\n'
                              'Take over the ship to finish the journey and sail towards the horizon.',
                      'hint': 'You can cancel and keep exploring.'},
 'confirm_dinghy': {'title': 'Lower the dinghy?',
                    'kicker': 'LEAVE THE SHIP',
                    'body': 'The sail is ready. Lower the dinghy, catch the wind and leave the pirate ship '
                            'behind.',
                    'hint': 'Confirm to escape, or keep exploring.'}}

ENDINGS = {'takeover': {'title': 'A ship of your own',
              'subtitle': 'Ending 1 of 3 · The takeover',
              'body': 'The sails fill. You turn away from port and let the pirate ship disappear into the '
                      'sunset. You are free, with only the silence of the ship for company.'},
 'crate': {'title': 'Freedom in a wooden crate',
           'subtitle': 'Ending 2 of 3 · The unseen passenger',
           'body': 'The cook carries the return crate ashore. You wait for the footsteps to fade, lift the '
                   'lid and slip between the warehouses. The ship stays behind.'},
 'dinghy': {'title': 'A small sail, a wide sea',
            'subtitle': 'Ending 3 of 3 · The dinghy',
            'body': 'You lower the dinghy into the waves. The little sail fills with wind and carries you '
                    'towards the lights of the coast.'}}

ROLES = {'patrol': 'Key guard',
 'dining': 'Cook',
 'cargo': 'Cargo guard',
 'lookout': 'Lookout',
 'sailor': 'Sailmaker',
 'armorer': 'Armorer',
 'medic': 'Ship doctor',
 'boatswain': 'Boatswain',
 'officer': 'Officer'}

DOCUMENTS['restart_confirm']={'title':'Start a new game?','kicker':'RESTART','body':'Your current escape will be replaced. You will begin again in the cell.','hint':'Choose Restart game to confirm, or keep playing.'}

ITEMS['captain_uniform']={'name':"Captain's uniform",'icon':'★','use':'Gold coat and command star. Wear it to command the helm after concealing the officer.'}
ENDINGS['command']={'title':'A captain by deception','subtitle':'Ending 4 of 4 · Heading home','body':'The crew obey your command. Sails rise above the deck, the ship turns towards port, and you sail home in the captain’s uniform.'}
for ending in ENDINGS.values():ending['subtitle']=ending['subtitle'].replace('of 3','of 4')
DOCUMENTS['captains_log']['body']+='\n\nThe officer alone knows the captain’s face. If he disappears, a gold coat and command star might convince the remaining crew.'

ROLES['sleeper']='Blue-key guard'
