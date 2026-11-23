# Supplied soundtrack assets

Audio files were supplied by the project owner for use in this game. The original uploads remain unchanged outside the repository. These browser assets are conversions of those uploads, not downloads from YouTube.

- `exploration-v1.ogg`: **The Young Buccaneer** and **Pirate Town**, composed by **Derek & Brandon Fiechter**. Source reference: https://www.youtube.com/watch?v=f7Cpkup4g3I. Only 0:00–6:52 is included. Converted to stereo Opus at a target 48 kbit/s; decoded programme length 412 seconds.
- `alert-v1.ogg`: **Deadly Combat / The Unstoppable**, by **RPG Soundtracks**. Source reference: https://www.youtube.com/watch?v=m-1S1V1PZHA. Complete supplied recording, approximately 66 minutes 44 seconds. The uploaded file had an MP3 extension but contained WebM/Opus audio. Converted to stereo Opus at a target 32 kbit/s.

The recordings remain the work of their respective creators. This repository does not grant a separate licence to reuse them outside this project. Music must be enabled through the game's Music button. Both recordings loop; exploration resets for each new run, and alert music resets when alert mode is entered. A same-run Streamlit rerender does not restart either recording.

The final dog rescue uses a short, locally synthesized C-major victory fanfare generated with the browser's Web Audio API. It plays by itself and does not add or redistribute a third recording.
