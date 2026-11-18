# Adaptive journal and visual polish

## What changed

The journal now separates **Possible next steps** from **Your discoveries**.
It offers at most three suggestions, based on discoveries and equipment already
recorded in the save. Each suggestion has an optional **Show a clearer hint**
disclosure. Opening that disclosure is a browser interaction, not a game action.

The ship keeps its existing Canvas style. Wood seams and staggered joints,
contact shadows, iron highlights, small clothing details, a folded-paper corner
and wax seal add definition. A restrained marker appears beneath a nearby
interactive prop. Foreground bars still cover objects naturally. Geometry,
interaction ranges, movement, camera settings and guard rules are unchanged.
Existing device-pixel-ratio rendering is retained.

The starting character now wears black-and-white prisoner stripes, with matching
sleeves and trousers, with short hair and no hat. The clothes follow standing, crouching, resting and
barrel poses; later guard/captain disguises keep their uniforms. The multiplayer
partner uses the same starting outfit. The pre-capture civilian intro keeps its
original clothes, and the cell scene uses the prisoner outfit. Existing saves
need no migration; an undisguised saved character receives the same new look.

The final visual pass adds a navy-and-brass app theme, separate title/tools and
voyage-status rows, coordinated journal/inventory controls, quieter keycaps,
small room plaques and soft cell daylight. Repeated controls outside the game
were removed; the accessible state summary remains in **Game details**.
The reusable art-direction prompt is in `specs/visual-direction.md`.

## How to explain the code

1. `journal.py` reads a validated game state and returns short dictionaries:
   an ID, title, status, suggestion and clearer explanation. It uses existing
   helpers such as `boat_ready`, `crate_ready`, `captain_ready` and `crew_asleep`.
   The same input and clock value produce the same suggestions, without writes.
2. `app.py` includes those suggestions in the component's normal state update.
   `runtime_loader.py` refreshes the new module along with existing rule modules.
3. `game_component/game.js` displays the suggestions using native HTML details.
   Entries have stable IDs so unchanged updates preserve expanded documents,
   focus and scrolling. The game leaves Space and arrow events alone while the
   journal is open, allowing normal document navigation.
4. `game.html` supplies the journal sections; `game.css` gives them the existing
   parchment, teal and brass appearance. Drawing helpers in `game.js` add the
   scenery and character detail independently of hint selection.

The discovery mapping and acceptance criteria are in `specs/adaptive-journal.md`.

## Try it yourself

Start the local game with `uv run streamlit run app.py --server.port 8536` if
the supplied preview is no longer running. Use the existing preview otherwise.

1. Start a game or continue your save. Press J or click Journal. A fresh game
   should point to the folded letter without revealing secret escape routes.
2. Expand **Show a clearer hint** with a click, Enter or Space. Press Tab to
   move between controls. Close with F, Escape or the close button.
3. Read the letter, then reopen the journal. It should remember the document
   and offer only leads supported by that discovery.
4. Obtain the cell key. Before opening the door, check that the advice now says
   to unlock it instead of stealing another key.
5. Find a sail and check the dinghy lead. Find rope or pay the boatswain, then
   check that equipment collection advice becomes an available next action.
6. Follow the crate clue: opening it removes tool advice. A dead cook makes
   that known plan unavailable. Do not sacrifice your preferred save just to
   check this case; it is also covered by automated tests.
7. Compare the bed, letter, bars, chests and character clothing. Check normal
   view, fullscreen and Brighter view. Resize the window and check journal
   scrolling and text wrapping.

For teammates after a PR exists: fetch its branch, install with `uv sync --locked`,
run `uv run pytest -q`, then start that checkout on a free local port. A separate
checkout is required to keep another branch's preview independent.

## Validation and limits

- Final local run: **201 tests passed**; `git diff --check` passed.
- A simulated installation without Node passed 166 tests and skipped the 35
  JavaScript-dependent tests. All assertions still execute when Node is present.
- A shadow-DOM keyboard regression was reproduced and fixed: the music slider
  now receives arrow/Space events without moving or crouching the character.
  Browser verification changed volume from 0.22 to 0.23 while the saved position
  stayed at cell x=230 and crouching stayed false, then restored the volume.
- The review also verified restart cancellation without resetting progress,
  inventory opening/closing, reading the initial letter, and the journal showing
  the corresponding document and updated suggestions.
- Automated acceptance tests cover discovery order, spoiler gating, equipment
  alternatives, cook death, capture, disguise, alarms, meal timing, older empty
  story saves, immutability and personal/shared multiplayer state.
- A keyboard regression test exercises the actual Canvas event handlers.
- The existing reliable-delivery DOM test double now implements `setAttribute`;
  all original retry and acknowledgement assertions remain.
- Browser checks include native hint expansion and preserving both expanded
  entries and a 495-pixel scroll position across a Streamlit rerun.
- At 390 pixels wide, journal content wrapped without horizontal overflow.
  Escape restored focus to the Journal button; F after keyboard opening restored
  focus to the game. Expanding hints left the disposable save checksum unchanged.
- Browser error logs were empty during the final preview check. Rendering was
  visually inspected; a hardware performance benchmark was not performed.
- Not every interaction is saved as a discovery. The castaway secret is therefore
  deliberately withheld, and undiscovered plans are not listed as locked quests.
- Multiplayer hints use shared discoveries/equipment and personal disguise.
  The UI explicitly warns that the ship stays live while reading. Time-sensitive
  guidance reflects the latest server update; there is no added polling.
- Live two-player testing needs a configured Ably key. Automated multiplayer
  checks do not replace that final connected playtest. No key is configured in
  this local environment; the multiplayer setup notice was verified in-browser.

No commit, push, PR, merge or deployment is part of the local review stage.
