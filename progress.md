Original prompt: Innovate advance improve add features refine

## Current findings

- The project is a single-file Python/Tkinter desktop game.
- The app contains duplicate method definitions; later copies silently override earlier ones.
- Several history/favorites methods are unrelated to the game and reference widgets/imports that do not exist.
- Exporting currently raises `NameError` because `json` is not imported.
- Best-of-three uses the all-time counters as match state, which makes mode changes and completed matches awkward.

## Planned work

- Separate game rules/state from the Tkinter UI so behavior can be tested.
- Add real match modes, AI difficulty, match progress, streaks, stats, and round history.
- Improve styling, layout, shortcuts, asset-path handling, reset behavior, and JSON export.
- Add automated tests and visually inspect the running desktop app.
