# Adaptive journal and visual polish

The journal offers at most three stable suggestions, derived without changing
the save. A short suggestion leads to optional, more direct help. Existing
documents remain available. English text, keyboard navigation and the current
single-player/multiplayer clock behavior are preserved.

## Discovery evidence

| Evidence already saved | Guidance permitted |
| --- | --- |
| No clues, locked cell | Notice the visible folded letter |
| Opening letter inspected | Key theft and the letter's crate/takeover clues |
| Cell key owned | Unlock the door, including after capture |
| Sail or rope owned; boat window inspected | Dinghy equipment and alternatives |
| Manifest or crate inspected; opening letter read | Crate plan and cook dependency |
| Captain's log read, uniform owned or officer concealed | Disguise plan |
| Pills owned and stew inspected, or stew already drugged | Stew plan |

Some failed interactions (helm, lifeboat and cell floor) are not stored as
discoveries. They do not unlock hints. In particular, the castaway outcome is
not advertised from merely owning pills. No save migration is needed.

## Acceptance

- New games do not expose secret routes. Key possession replaces theft advice.
- Sail/rope/payment combinations use the existing boat readiness helper.
- Open crates stop requesting tools. A dead cook blocks a known crate plan.
- Disguise readiness uses the authoritative helper; alarms remain temporary.
- The stew distinguishes preparation, gathering, sleep and an ended meal.
- Different discovery orders produce identical suggestions; calculations do
  not mutate state. Existing saves and personal multiplayer disguise work.
- Clearer hints run locally. Focus, scrolling and expanded documents survive
  unchanged component updates. Multiplayer clearly says the ship is live.
- Graphics retain geometry and rules: stable wood detail, metal highlights,
  contact shadows, character details and a subtle nearby-object treatment.
- Compare cell and cabin/hold views, fullscreen and a narrow viewport.

## Baseline

At 076a8a9: 183 passed, one existing failure in the reliable-delivery test.
Its DOM test double lacks `setAttribute` on the intro music button. Any repair
must improve that test double without removing delivery assertions.
