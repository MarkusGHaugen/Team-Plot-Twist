# Cannon finale: "one last escape"

Acceptance notes. Written before any code, as `AGENTS.md` asks. Numbers in **bold** are proposals the group can change; they are collected under "Open choices" at the end.

## The story beat

- The player confirms an ending and the usual celebration plays: happy music, sails, freedom.
- Then the music cuts and turns dark. Behind the player, the guards appear on the horizon in boats, furious, with cannons. The celebration was not the end.
- The player has to dodge **10** cannonballs. When the last one has been dealt with, the music turns hopeful and a small boat arrives with the dog from the intro. The player climbs aboard and escapes for real.

## Rules (the server decides all of these)

1. The finale starts only after one of the six existing endings has been confirmed. It cannot be started from anywhere else, and a rejected request changes nothing in the save.
2. The finale has a fixed volley of **10** cannonballs. Each ball has a lane (**high** or **low**) and an arrival time. The order is decided by the server from a stored seed, so the same save always replays the same volley.
3. A **low** ball must be jumped (W / Up). A **high** ball must be ducked (Space / Down). Doing the wrong move, or nothing, is a hit.
4. The player has **3** lives. A hit removes one life. At 0 lives the player is caught.
5. The counter shows cannonballs left, from 10 down to 0. It never goes below 0 and never changes except when a ball has been resolved (dodged or hit).
6. The finale is won only when all 10 balls are resolved and at least 1 life remains. The client may animate this, but only the server can declare it won.
7. On a win the rescue boat with the dog arrives, and a new ending panel appears: **"Free at last"** (`ending 7`). The earlier ending stays recorded.
8. On a loss the player is "caught" and may **retry the finale from the first cannonball**. A loss never deletes the earlier ending, items or coins.
9. Reloading the page during the finale resumes it: same ball count, same lives. A finished finale (won) cannot be replayed except through Restart.
10. Older saves without finale data load exactly as before (migration in `db.py`).

## What the player sees and hears

- Music: happy during the celebration, a hard cut to dark when the guards appear, hopeful again when the rescue boat arrives. This reuses the existing `explore` / `alert` music modes plus one for the rescue.
- HUD: cannonballs left (**10**) and lives (**3** hearts).
- Guard boats and cannons in the background, with a puff of smoke before each shot so the lane can be read.
- Rescue scene: the intro's boat and dog (`introSkiff`, `introDog`, `introPerson` in `game.js`) arrive from the side and the player boards.
- Reduced-motion mode: balls are shown as a clear telegraph (lane marker plus countdown) instead of fast movement, and the finale remains playable.

## Acceptance checks

- Starting the finale before an ending is rejected and the save is unchanged.
- The volley always has exactly 10 balls and the same order for the same seed.
- Jumping a low ball and ducking a high ball is a dodge; the wrong move or no move is a hit.
- 3 hits end the finale as "caught"; 2 hits followed by 8 dodges still wins.
- The counter reaches 0 only after the 10th ball is resolved, and never goes negative.
- A client that claims victory early is rejected and nothing changes.
- Retry after a loss restarts at 10 balls and 3 lives; the earlier ending and inventory are kept.
- Reloading mid-finale restores the same ball count and lives.
- An old save with no finale data still loads.
- The "Free at last" ending shows after a win and can be replayed through Restart.
- Reduced-motion mode shows the telegraph and the rescue scene.

## Tests to write first

New file `tests/test_cannon_finale.py`, in the style of `tests/test_sleeping_pills.py`: rules and save round-trips on the server, plus a parity test that the Canvas timing constants match the server's.

## Where it will live

- New module `finale.py` for the rules, next to `shiplife.py` and `voyage.py`.
- `logic.py`: validate the new finale state, and allow the new ending.
- `content.py`: the new ending text and captions. `ENDINGS` subtitles currently say "of 6"; update to "of 7".
- `db.py`: migration for saves with finale data.
- `game_component/`: Canvas drawing, controls, music.
- `CHANGELOG.md`: describe the change.
- `game_component/game.js` and `logic.py` are common conflict points: tell the group before editing, and keep the commits small.

## Out of scope for the first version

- Different volleys for different endings.
- Difficulty settings.
- A leaderboard.

## Open choices (the group decides)

- Which endings trigger it: **all six**, or only some?
- Lives: **3**.
- Volley length and speed: **10 balls over about 40 seconds**.
- Multiplayer: the ship is shared, so does the finale have **shared lives** or **one set per player**?
- On a loss: **retry** (proposed) or go back to the cell?
- Who owns what: the intro scene belongs to Hannah. The finale reuses her drawing functions and should call them, not copy them.
