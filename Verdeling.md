Person A handles server and netcode, Person B focuses on client rendering and physics, Person C builds UI/menus and assets. This enables parallel development with clear handoffs; use Git for shared code like Player.py.

## Person A: Server & Netcode (Hayyan)
- Server.py: Socket server, client auth (2 players), game loop (inputs -> updates -> broadcast JSON states).
- Combat resolution: Damage, knockback, win detection, vote handling.

## Person B: Client Core & Mechanics (Finn)
- Client.py basics: Input capture, local prediction, rendering loop.
- Physics/Mechanics: Movement (jump, dash), collisions, weapons (hitboxes/projectiles) in shared files.
- Arena: Tile collision, camera follow.

## Person C: UI, Menus & Assets (Thijs)
- Menus: Weapon select, arena vote screens (buttons, nav, visuals).
- HUD: Health bars, timers, effects (particles).
- Assets: Simple sprites/rects (players, weapons, arenas); sounds. Integrate into client.

## Shared & Integration
| Task | Who Leads | Notes |
|------|-----------|-------|
| Shared models (Player, Weapon, JSON protocols) | Person A | Define early; test formats. |
| Testing (local net, bots) | All | Weekly merges; localhost first.  |
| Polish (lag fix, sync) | Person A/B | Debug desync.  |
| Full integration | Person B | Run end-to-end flow. |

Sync daily on GitHub; Person B coordinates client-server links.