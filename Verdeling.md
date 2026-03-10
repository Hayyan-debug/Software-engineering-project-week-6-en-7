Person A and Person B can split tasks efficiently: Person A focuses on server-side logic and core mechanics, while Person B handles client-side rendering and UI. Merge via shared files (e.g., Player.py) and test together early.

## Person A: Server & Mechanics
- Implement server.py: Socket setup, client handling (accept 2 players), game loop (60 FPS), input processing, state updates/broadcast.
- Core physics: Movement, collisions, gravity, knockback in shared Player.py and Physics.py.
- Weapons logic: Weapon classes with attack effects, projectiles, damage calc.
- Menus backend: Collect weapon choices/votes, decide arena, handle win conditions.

## Person B: Client & UI
- Implement client.py: Socket connection, input handling (keys), local prediction, state rendering.
- Menus frontend: Weapon selection screen, voting UI with buttons/images/live bars.
- Arena rendering: Tilemaps, camera, particles, animations (use sprite sheets).
- Polish: HUD (health, % damage), sounds, effects.

## Shared & Integration Tasks
| Task | Who Leads | Notes |
|------|-----------|-------|
| Shared classes (Player, Weapon, Arena) | Both | Git repo; define JSON formats for net data early. |
| Testing | Both | Localhost first; add bots for solo test. |
| Assets | Person B | Free from Kenney.nl; commit to repo. |
| Net sync debugging | Person A | Fix lag/desync; use logs. |

This split allows parallel work; sync daily on GitHub. Meet after menus for fight integration.