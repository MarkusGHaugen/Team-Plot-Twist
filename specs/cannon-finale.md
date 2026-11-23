# Cannon finale: "one last escape"

Acceptance notes. Written before any code, as `AGENTS.md` asks. Numbers in **bold** are proposals the group can change; they are collected under "Open choices" at the end.

## The story beat

- Any of the six escape endings plays its existing scene, then cuts to a shared beach scene: the player stands on the sand and celebrates being free.
- Each of the six original escape scenes now has cheerful exploration music. On the beach, the brief **Free at last!** celebration lasts about **5.7 seconds**, followed by a **4.8-second** plot twist scene so players can read the reveal.
- Cheerful exploration music plays while the player celebrates being free on the beach. It cuts to the dark, dramatic guard theme exactly when the **"PLOT TWIST: THE GUARDS ARE BACK!"** text appears.
- After the final cannonball is dodged, a bright, locally synthesized victory fanfare starts automatically, even if music was off during play, as the dog arrives to rescue the player. It replaces the other tracks for the rescue scene.
- After the beach reveal, the player has to dodge **10** cannonballs. On a win, a small boat arrives with the dog from the intro. This is the rescue epilogue of the reached route, not another ending.
- On a loss, show **"Caught by the cannons!"** and a **Try again** button. Retrying starts a fresh volley; it does not reset the game.

## Rules (the server decides all of these)

1. After one of the six existing escape routes and its original ending scene, the page starts the shared beach celebration and then the cannon finale automatically. A finale request cannot be started from anywhere else, and a rejected request changes nothing in the save.
2. The finale has a fixed volley of **10** cannonballs, fired about **1 second apart** (with a little timing jitter). Each ball has a lane (**high** or **low**) and an arrival time. The order is decided by the server from a stored seed, so the same save always replays the same volley.
3. A **low** ball must be jumped (W / Up). A **high** ball must be ducked (Space / Down). Doing the wrong move, or nothing, is a hit.
4. The player has **3** lives. A hit removes one life. At 0 lives the finale is lost and the player can start a new volley with Try again.
5. The counter shows cannonballs left, from 10 down to 0. It never goes below 0 and never changes except when a ball has been resolved (dodged or hit).
6. The finale is won only when all 10 balls are resolved and at least 1 life remains. The client may animate this, but only the server can declare it won.
7. On a win the rescue boat with the dog arrives. The final screen shows the original route ending (`Ending x of 6`) and the **"Free at last"** rescue epilogue. The route ending is unchanged in the save.
8. On a loss, show a caught screen with Try again. Retry keeps the original route and all game progress, increments the attempt and starts a new seeded volley. A loss never resets the game.
9. Once an ending is reached, ordinary story actions are rejected and leave the save unchanged. While the finale is active, only `finale_start`, `finale_report`, `finale_retry`, and New Game after its existing confirmation can change the save.
10. Reloading or continuing mid-finale resumes the saved finale record and route. Starting New Game requires confirmation and resets both the route and finale record.
11. The server accepts a report when the volley is over, or earlier once the third hit has landed. A report that arrives before that is rejected and changes nothing.
12. Older saves without finale data load exactly as before. Legacy saves from the earlier seventh-ending implementation migrate their stored route and finale result.

## What the player sees and hears

- Music: happy for the start of the beach celebration, then switches to the existing `alert` music as the guards appear. The rescue boat reuses the intro's visual assets.
- HUD: cannonballs left (**10**) and lives (**3** hearts).
- Guard boats and cannons in the background, with a puff of smoke before each shot so the lane can be read.
- Rescue scene: the intro's boat and dog (`introSkiff`, `introDog`, `introPerson` in `game.js`) arrive from the side and the player boards.
- Caught screen: after the third hit, show **"Caught by the cannons!"** and **Try again**.
- Won screen: show the original route ending (`Ending x of 6`) followed by the rescue epilogue text.
- Reduced-motion mode: the lane marker with the word JUMP or DUCK is shown for the whole flight of every ball (it normally appears after a third of the flight). The timing is the same, so the finale stays playable; the rescue is shown as one still frame.

## Acceptance checks

- Starting the finale before an ending is rejected and the save is unchanged.
- The volley always has exactly 10 balls and the same order for the same seed.
- Jumping a low ball and ducking a high ball is a dodge; the wrong move or no move is a hit.
- 3 hits end the attempt as "caught"; Try again starts a new volley without resetting or changing the route. 2 hits followed by 8 dodges still wins.
- Winning leaves the route, position, inventory and decisions unchanged; save/restore retains the route and `finale.status == "won"`.
- The counter reaches 0 only after the 10th ball is resolved, and never goes negative.
- A client that claims victory early is rejected and nothing changes.
- A retry after a loss keeps the route and game state and starts a new volley; the save is never reset automatically.
- Ordinary story actions after an ending are rejected without changing the save.
- Reloading mid-finale resumes from the saved finale record.
- New Game requires confirmation and clears both ending and finale state.
- An old save with no finale data still loads.
- The final screen shows the original ending as "Ending x of 6" plus the "Free at last" rescue epilogue.
- Reduced-motion mode shows the telegraph and the rescue scene.

## Tests

`tests/test_cannon_finale.py` covers server rules, route immutability, save/restore, retry, multiplayer sharing, and Canvas parity. The ending-count expectation in `tests/test_sleeping_pills.py` remains six.

## Where it will live

- New module `finale.py` for the rules, next to `shiplife.py` and `voyage.py`.
- `logic.py`: validate the finale result while preserving the reached route.
- `content.py`: the rescue epilogue text is separate from the six route endings; `ENDINGS` subtitles remain "of 6".
- `db.py`: migration for saves with finale data.
- `game_component/`: Canvas drawing, controls, music.
- `CHANGELOG.md`: describe the change.
- `game_component/game.js` and `logic.py` are common conflict points: tell the group before editing, and keep the commits small.

## Out of scope for the first version

- Different volleys for different endings.
- Difficulty settings.
- A leaderboard.

## Decisions taken (change them if the group disagrees)

- Endings that trigger it: **all six**. The finale starts a few seconds after the ending's own scene ends.
- Lives: **3**. Volley: **10 balls over about 22.5 seconds**, with a small random jitter in the timing that the server fixes with the seed.
- On a loss: show the caught screen and let the player retry the cannon volley without resetting the game.
- Multiplayer: the ship is shared, so the finale is shared. Both players see the same volley and play it on their own screens; whoever's report reaches the server first decides the result for both.
- Known limit: the server judges the moves the page reports and checks the timing window and that enough time has passed, but it cannot see the keyboard. A player who edits the page could send perfect moves. That is acceptable for a class game; the rules and saves are still validated on the server.
- Ownership: the intro scene belongs to Hannah. The rescue scene calls her drawing functions (`introSkiff`, `introDog`, `introPerson`, `introPirate`) and does not copy them.
