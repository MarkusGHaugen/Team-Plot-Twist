# Visual finishing brief

Refine Team Plot Twist into a cohesive maritime adventure interface. Preserve
the illustrated Canvas world, warm timber, dark ocean teal and restrained brass.
Make the game feel deliberately art-directed: clear hierarchy, consistent
spacing and controls, crisp materials, readable lighting and calm overlays.

## Implementation prompt

Repository: https://github.com/MarkusGHaugen/Team-Plot-Twist

Local checkout: `/Users/skole/Documents/nova/Team-Plot-Twist`.
Continue the existing `feature/adaptive-journal-polish` work without discarding
uncommitted changes. Read AGENTS.md, START_HERE.md and CONTRIBUTING.md first.

Act as a senior game UI developer and visual designer. Inspect the live game
before editing. Work on the existing feature branch and preserve unfinished
work and player saves. Keep all visible text and documentation in English.

1. Remove every hat from the prisoner outfit, including crouching, resting,
   barrel and ending poses. Use a simple, recognizable short-haired silhouette.
   Keep the striped clothes and the guards' and captain's distinct uniforms.
2. Give the interface a clear hierarchy: adventure title and tools, compact
   voyage status, immersive scene, then a quiet keyboard legend. Reserve brass
   emphasis for meaningful actions. Avoid repeated instructions and debug-like
   status text around the game; retain accessible details on demand.
3. Replace flat material fills with restrained shading, deliberate highlights
   and well-placed hardware detail. Improve signs and paper without making
   every prop compete for attention. Keep foreground occlusion believable.
4. Refine the journal as a readable parchment document, with clear section
   hierarchy, discreet status labels and obvious keyboard focus. Make inventory
   and feedback panels feel like part of the same product.
5. Keep desktop and narrow layouts usable. Respect reduced motion. Avoid web
   fonts, external image dependencies, heavy blur and random per-frame texture.
6. Preserve map geometry, game rules, camera behavior, save formats, multiplayer
   timing and the existing hint logic. Do not merge, deploy or push.

Validate the actual browser result at desktop and narrow widths. Inspect both
prisoner and uniform states, journal and inventory, and representative poses.
Run appropriate regression checks. Provide screenshots and a running local
preview, explain any limitations, and wait for player feedback before commits.

## Acceptance

- Prisoner headwear is absent; guard/captain uniforms remain recognizable.
- Title, tools and status are distinct without crowding the scene.
- Controls remain reachable at 390px; journal has no horizontal text overflow.
- Native journal keyboard controls and reduced-motion preferences still work.
- Existing tests pass, and no local saves or credentials enter source control.

## Final local verification

All 201 regression tests passed, as did `git diff --check`. Browser review
covered the standing and crouching prisoner, inventory, journal, keyboard hint
expansion and focus restoration. At 390px, every toolbar button fit on one row,
and journal content wrapped without horizontal overflow. Final browser error
logs were empty. The preview remains local for player review.
