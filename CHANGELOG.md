# Changelog

## Unreleased

- Mandatory cannon finale: after any of the six escape routes' original ending scenes, the beach celebration leads automatically into the cannon volley. Winning shows the rescue boat, dog and "Free at last" epilogue while preserving the reached ending. Three hits show "Caught by the cannons!" with a Try again button for a fresh volley; no loss resets the game automatically. New Game continues to require confirmation.
- Cheerful music plays in each of the six escape scenes. The beach celebration is shortened by one second and the plot twist sequence is extended by two seconds.
- The plot twist is extended by one more second, and a distinct upbeat victory fanfare now plays alone during the final dog rescue.
- Validation: tests cover finale rules, save/restore, route preservation, multiplayer sharing, beach music and scene timing, retry behavior, and server/Canvas parity (`tests/test_cannon_finale.py`).
- Multiplayer: one shared ship. What one player does happens for both (key, doors, items, coins, crew, alarms, the meal, the ending). A caught player is taken back to the locked cell and the crew search 30 seconds for the other, starting where they were last seen. Reading no longer pauses the game in multiplayer; Restart restarts the ship for both.
- Multiplayer (beta): choose Single player or Multiplayer. Create a room and share its six-letter code; both players start in the cell and see each other move live through Ably. Each room has its own save. For now each player still has their own ship (doors, items and guards are not shared yet).
- Sleeping pills in the cabin sea chest, with two new endings (6 in total): drug the crew stew so the whole crew eats and sleeps for two minutes (escape by dinghy or the helm, ending "A lullaby for pirates"), or swallow them in your cell and drift four days in a barrel to a deserted island (ending "Castaway").
- Deck cannon: light it with a lamp; the blast draws every pirate to the cannon and wakes a sleeping crew.
- Telescope in the crow's nest with a panning view of the horizon.
- Rats in the hold that flee from people.
- Return crate 07 now waits on the middle deck between the two barrels; the cook's escort leads there.
- A real galley: planked deckhouse, iron range with a live fire, a big stew pot with bubbles and steam (crushed pills show as pale specks), hanging pans, a shelf and a prep table.
- Faster online play: key presses no longer wait behind a once-a-second crew check, each action runs the page once instead of twice, and the game script is downloaded once instead of with every action.
- Validation: 149+ tests, including server/Canvas parity for every crew pose during the meal; scenes checked in a rendered preview.

## 1.0.0 — 2026-11-04

- Initial Team Plot Twist release with independent project identity and save storage.
- Complete pirate-ship exploration game, four endings, barrel ambushes, captain disguise, crew patrols, guides and supplied soundtrack.
- Fresh team-only Git history, collaboration guide, portable launchers and source packaging.
